"""
PDF Ingestion Script for RAG Pipeline

Extracts text from company_policy.pdf, chunks it, generates embeddings,
and stores in PostgreSQL documents table.

RUN: python ingest_pdf.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Document
from api.ollama_service import generate_embedding
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    print(f"Reading PDF: {pdf_path}")
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        
        for page_num, page in enumerate(pdf_reader.pages):
            text += page.extract_text()
            print(f"  Extracted page {page_num + 1}/{len(pdf_reader.pages)}")
    
    return text

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Clean chunk
        chunk = chunk.strip()
        if chunk:
            chunks.append(chunk)
        
        start += chunk_size - overlap
    
    print(f"Created {len(chunks)} chunks")
    return chunks

def ingest_pdf(pdf_path, source_name="company_policy"):
    """Main ingestion function"""
    print("\n=== PDF Ingestion Started ===\n")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    print(f"Total text length: {len(text)} characters\n")
    
    # Chunk text
    chunks = chunk_text(text)
    
    # Generate embeddings and store
    print("\nGenerating embeddings and storing in database...")
    
    for idx, chunk in enumerate(chunks):
        print(f"Processing chunk {idx + 1}/{len(chunks)}...")
        
        try:
            # Generate embedding
            embedding = generate_embedding(chunk)
            
            # Store in database
            Document.objects.create(
                content=chunk,
                embedding=embedding,
                metadata={
                    "source": source_name,
                    "chunk_id": idx,
                    "type": "pdf"
                }
            )
            
            print(f"  ✓ Stored chunk {idx + 1}")
        
        except Exception as e:
            print(f"  ✗ Error on chunk {idx + 1}: {str(e)}")
    
    print(f"\n=== ✓ Successfully ingested {len(chunks)} chunks from {source_name}.pdf ===\n")

if __name__ == "__main__":
    # Clear existing documents (optional - comment out to keep old data)
    print("Clearing existing documents...")
    Document.objects.all().delete()
    print("✓ Cleared\n")
    
    # Ingest company_policy.pdf
    pdf_path = "company_policy.pdf"
    
    if os.path.exists(pdf_path):
        ingest_pdf(pdf_path)
    else:
        print(f"ERROR: {pdf_path} not found in backend folder!")
        print("Please ensure company_policy.pdf is in the backend directory.")
