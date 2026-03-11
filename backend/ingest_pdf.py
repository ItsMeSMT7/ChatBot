# d:\Sumit\Project\P Square\backend\ingest_pdf.py

"""
Ingest company_policy.pdf using the new intelligent pipeline.

BEFORE: Read PDF → split every 500 chars → embed → save
NOW:    Parse PDF (headings, pages) → sentence-aware chunks →
        extract keywords → embed → save with rich metadata
"""

import os
import sys
import time
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from api.models import Document, DocumentChunk
from api.document_parser import parse_document
from api.chunking import create_chunks
from api.ollama_service import generate_embedding


def ingest_document(file_path):
    """Process and ingest a single document."""
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return

    file_name = os.path.basename(file_path)
    print(f"\n{'='*60}")
    print(f"  Ingesting: {file_name}")
    print(f"{'='*60}\n")

    start = time.time()

    # ── Step 1: Create or get Document record ──────────────
    doc, created = Document.objects.get_or_create(
        name=file_name,
        defaults={'processing_status': 'pending'}
    )

    if not created:
        print(f"  Document '{file_name}' already exists (ID: {doc.id})")
        print(f"  Deleting old chunks...")
        old_count = DocumentChunk.objects.filter(document=doc).count()
        DocumentChunk.objects.filter(document=doc).delete()
        print(f"  Deleted {old_count} old chunks")

    doc.processing_status = 'processing'
    doc.save()

    # ── Step 2: Parse document ─────────────────────────────
    print(f"\n  [1/4] Parsing document...")
    parsed_doc = parse_document(file_path)

    heading_count = sum(1 for s in parsed_doc.sections if s.section_type == "heading")
    print(f"    ├── Pages: {parsed_doc.total_pages}")
    print(f"    ├── Sections found: {len(parsed_doc.sections)}")
    print(f"    ├── Headings detected: {heading_count}")
    print(f"    └── Total characters: {len(parsed_doc.full_text):,}")

    if not parsed_doc.full_text.strip():
        print(f"\n  ✗ No text extracted!")
        doc.processing_status = 'failed'
        doc.save()
        return

    # ── Step 3: Intelligent chunking ───────────────────────
    print(f"\n  [2/4] Creating intelligent chunks...")
    chunks = create_chunks(parsed_doc)

    print(f"    ├── Chunks created: {len(chunks)}")
    avg_chars = sum(len(c.content) for c in chunks) // max(len(chunks), 1)
    print(f"    ├── Avg chunk size: {avg_chars} chars")

    # Show sample chunk info
    if chunks:
        first = chunks[0]
        print(f"    ├── First chunk section: '{first.section_title or 'None'}'")
        print(f"    ├── First chunk keywords: {first.keywords[:5]}")
        print(f"    └── First chunk preview: '{first.content[:80]}...'")

    # ── Step 4: Generate embeddings and save ───────────────
    print(f"\n  [3/4] Generating embeddings and saving...")
    saved = 0
    failed = 0

    for i, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk.content)

        if embedding is None:
            failed += 1
            print(f"    ✗ Chunk {i}: embedding failed")
            continue

        DocumentChunk.objects.create(
            document=doc,
            content=chunk.content,
            embedding=embedding,
            metadata={"source": file_name, **(chunk.metadata or {})},
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            keywords=chunk.keywords,
            chunk_index=chunk.chunk_index,
            char_count=len(chunk.content),
        )
        saved += 1

        # Progress indicator
        if (i + 1) % 10 == 0 or i == len(chunks) - 1:
            print(f"    ✓ {i + 1}/{len(chunks)} chunks embedded")

    # ── Step 5: Update document record ─────────────────────
    doc.total_chunks = saved
    doc.processing_status = 'completed'
    doc.save()

    elapsed = time.time() - start

    # ── Summary ────────────────────────────────────────────
    print(f"\n  [4/4] Summary")
    print(f"    ├── Chunks saved: {saved}")
    if failed:
        print(f"    ├── Chunks failed: {failed}")
    print(f"    ├── Time: {elapsed:.1f}s")
    print(f"    └── Status: {'✓ COMPLETED' if saved > 0 else '✗ FAILED'}")

    # Show all detected sections
    if heading_count > 0:
        print(f"\n  Detected sections:")
        seen = set()
        for chunk in chunks:
            if chunk.section_title and chunk.section_title not in seen:
                seen.add(chunk.section_title)
                kw_count = len(chunk.keywords)
                print(f"    • {chunk.section_title} ({kw_count} keywords)")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # Default: process company_policy.pdf
    pdf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "company_policy.pdf"
    )

    # Or pass a file path as argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

    ingest_document(pdf_path)





# """
# PDF Ingestion Script for RAG Pipeline

# Extracts text from company_policy.pdf, chunks it, generates embeddings,
# and stores in PostgreSQL documents table.

# RUN: python ingest_pdf.py
# """

# import os
# import django

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
# django.setup()

# from api.models import Document
# from api.ollama_service import generate_embedding
# import PyPDF2

# def extract_text_from_pdf(pdf_path):
#     """Extract text from PDF file"""
#     print(f"Reading PDF: {pdf_path}")
    
#     with open(pdf_path, 'rb') as file:
#         pdf_reader = PyPDF2.PdfReader(file)
#         text = ""
        
#         for page_num, page in enumerate(pdf_reader.pages):
#             text += page.extract_text()
#             print(f"  Extracted page {page_num + 1}/{len(pdf_reader.pages)}")
    
#     return text

# def chunk_text(text, chunk_size=500, overlap=50):
#     """Split text into overlapping chunks"""
#     chunks = []
#     start = 0
    
#     while start < len(text):
#         end = start + chunk_size
#         chunk = text[start:end]
        
#         # Clean chunk
#         chunk = chunk.strip()
#         if chunk:
#             chunks.append(chunk)
        
#         start += chunk_size - overlap
    
#     print(f"Created {len(chunks)} chunks")
#     return chunks

# def ingest_pdf(pdf_path, source_name="company_policy"):
#     """Main ingestion function"""
#     print("\n=== PDF Ingestion Started ===\n")
    
#     # Extract text
#     text = extract_text_from_pdf(pdf_path)
#     print(f"Total text length: {len(text)} characters\n")
    
#     # Chunk text
#     chunks = chunk_text(text)
    
#     # Generate embeddings and store
#     print("\nGenerating embeddings and storing in database...")
    
#     for idx, chunk in enumerate(chunks):
#         print(f"Processing chunk {idx + 1}/{len(chunks)}...")
        
#         try:
#             # Generate embedding
#             embedding = generate_embedding(chunk)
            
#             # Store in database
#             Document.objects.create(
#                 content=chunk,
#                 embedding=embedding,
#                 metadata={
#                     "source": source_name,
#                     "chunk_id": idx,
#                     "type": "pdf"
#                 }
#             )
            
#             print(f"  ✓ Stored chunk {idx + 1}")
        
#         except Exception as e:
#             print(f"  ✗ Error on chunk {idx + 1}: {str(e)}")
    
#     print(f"\n=== ✓ Successfully ingested {len(chunks)} chunks from {source_name}.pdf ===\n")

# if __name__ == "__main__":
#     # Clear existing documents (optional - comment out to keep old data)
#     print("Clearing existing documents...")
#     Document.objects.all().delete()
#     print("✓ Cleared\n")
    
#     # Ingest company_policy.pdf
#     pdf_path = "company_policy.pdf"
    
#     if os.path.exists(pdf_path):
#         ingest_pdf(pdf_path)
#     else:
#         print(f"ERROR: {pdf_path} not found in backend folder!")
#         print("Please ensure company_policy.pdf is in the backend directory.")
