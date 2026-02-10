"""
Data Ingestion Script for RAG Pipeline

WHEN TO RUN: 
- Initially to load your knowledge base
- Whenever you add new documents/FAQs
- Run: python ingest_data.py

HOW IT WORKS:
1. Reads your documents/FAQs
2. Generates embeddings for each
3. Stores both text and embeddings in PostgreSQL
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Document
from api.ollama_service import generate_embedding

# YOUR KNOWLEDGE BASE - Replace with your actual data
KNOWLEDGE_BASE = [
    {
        "content": "P Square is an intelligent chatbot system that uses RAG to answer questions based on stored knowledge.",
        "metadata": {"category": "general", "source": "documentation"}
    },
    {
        "content": "The system uses PostgreSQL with pgvector extension for storing and searching vector embeddings.",
        "metadata": {"category": "technical", "source": "documentation"}
    },
    {
        "content": "Ollama runs locally and provides both embedding generation and LLM capabilities without external API calls.",
        "metadata": {"category": "technical", "source": "documentation"}
    },
    # Add more documents here
]

def ingest_documents():
    """Load documents into vector database"""
    print("Starting data ingestion...")
    
    for idx, doc_data in enumerate(KNOWLEDGE_BASE):
        print(f"Processing document {idx + 1}/{len(KNOWLEDGE_BASE)}...")
        
        # Generate embedding
        embedding = generate_embedding(doc_data["content"])
        
        # Store in database
        Document.objects.create(
            content=doc_data["content"],
            embedding=embedding,
            metadata=doc_data.get("metadata", {})
        )
        
        print(f"✓ Stored: {doc_data['content'][:50]}...")
    
    print(f"\n✓ Successfully ingested {len(KNOWLEDGE_BASE)} documents!")

if __name__ == "__main__":
    # Clear existing documents (optional)
    Document.objects.all().delete()
    print("Cleared existing documents\n")
    
    ingest_documents()
