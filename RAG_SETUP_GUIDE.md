# RAG + LLM System Setup Guide

## 🎯 System Overview

Your chatbot now uses **RAG (Retrieval Augmented Generation)** to answer questions from PDF documents.

### How It Works:
```
User Question 
    ↓
Generate Embedding (Ollama)
    ↓
Search Similar Documents (pgvector)
    ↓
Retrieve Top 3 Relevant Chunks
    ↓
Build Context + Question Prompt
    ↓
Generate Answer (Ollama LLM)
    ↓
Return Natural Language Response
```

---

## 📋 Prerequisites

1. ✅ PostgreSQL running with pgvector extension
2. ✅ Ollama installed and running (`ollama serve`)
3. ✅ Gemma model pulled (`ollama pull gemma:1b`)
4. ✅ company_policy.pdf in backend folder

---

## 🚀 Step-by-Step Setup

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

This installs:
- PyPDF2 (for PDF text extraction)
- All other required packages

### Step 2: Start Ollama Server
```bash
ollama serve
```

Keep this terminal open. Ollama must be running on `http://localhost:11434`

### Step 3: Ingest PDF into Vector Database
```bash
# Option A: Use batch file (Windows)
Double-click: ingest_company_policy.bat

# Option B: Manual
cd backend
python ingest_pdf.py
```

**What happens:**
- Reads `company_policy.pdf`
- Extracts text from all pages
- Splits into 500-character chunks with 50-char overlap
- Generates 768-dim embeddings for each chunk (using Ollama)
- Stores in PostgreSQL `documents` table with pgvector

**Expected output:**
```
=== PDF Ingestion Started ===

Reading PDF: company_policy.pdf
  Extracted page 1/10
  Extracted page 2/10
  ...
Total text length: 15000 characters

Created 35 chunks

Generating embeddings and storing in database...
Processing chunk 1/35...
  ✓ Stored chunk 1
Processing chunk 2/35...
  ✓ Stored chunk 2
...

=== ✓ Successfully ingested 35 chunks from company_policy.pdf ===
```

### Step 4: Start Backend
```bash
cd backend
python manage.py runserver
```

### Step 5: Start Frontend
```bash
cd frontend
npm start
```

### Step 6: Test RAG System

Open browser: `http://localhost:3000`

**Try these questions:**
- "What is the vacation policy?"
- "Tell me about sick leave"
- "What are the working hours?"
- "Explain the remote work policy"

---

## 🔧 System Configuration

### Current Setup (views.py):
```python
class ChatBotAPI(APIView):
    def post(self, request):
        question = request.data.get("question")
        result = rag_query(question)  # Uses RAG system
        return Response({"answer": result})
```

### RAG Pipeline (rag.py):
1. **similarity_search()** - Finds top 3 similar document chunks
2. **rag_query()** - Builds prompt and generates answer

### Embedding Generation (ollama_service.py):
- Model: `gemma:1b`
- Dimensions: 768
- Endpoint: `http://localhost:11434/api/embeddings`

### LLM Response (ollama_service.py):
- Model: `gemma:1b`
- Endpoint: `http://localhost:11434/api/generate`

---

## 📊 Database Schema

### documents table:
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,                    -- Original text chunk
    embedding VECTOR(768),           -- 768-dim embedding
    metadata JSONB,                  -- {source, chunk_id, type}
    created_at TIMESTAMP
);
```

### Example document row:
```json
{
    "content": "Employees are entitled to 15 days of paid vacation per year...",
    "embedding": [0.123, -0.456, 0.789, ...],  // 768 numbers
    "metadata": {
        "source": "company_policy",
        "chunk_id": 5,
        "type": "pdf"
    }
}
```

---

## 🧪 Testing

### Test 1: Check Ollama
```bash
curl http://localhost:11434/api/tags
```
Should show `gemma:1b` model

### Test 2: Check Documents
```bash
cd backend
python manage.py shell
```
```python
from api.models import Document
print(f"Total documents: {Document.objects.count()}")
print(Document.objects.first().content[:100])
```

### Test 3: Test RAG Query
```bash
python
```
```python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.rag import rag_query
answer = rag_query("What is the vacation policy?")
print(answer)
```

---

## 🔄 Adding More PDFs

To add more documents:

1. Place PDF in `backend/` folder
2. Edit `ingest_pdf.py`:
   ```python
   # At the bottom
   ingest_pdf("company_policy.pdf", "company_policy")
   ingest_pdf("employee_handbook.pdf", "employee_handbook")
   ingest_pdf("safety_manual.pdf", "safety_manual")
   ```
3. Run: `python ingest_pdf.py`

---

## 🐛 Troubleshooting

### "Ollama connection failed"
- Check: `ollama serve` is running
- Test: `curl http://localhost:11434`

### "No relevant information found"
- Check: Documents are ingested
- Run: `python ingest_pdf.py` again

### "PyPDF2 not found"
- Install: `pip install PyPDF2==3.0.1`

### "pgvector error"
- Ensure pgvector extension is enabled in PostgreSQL
- Run: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## 📈 Performance Tips

1. **Chunk Size**: 500 chars (adjustable in `ingest_pdf.py`)
2. **Overlap**: 50 chars (prevents context loss)
3. **Top K**: 3 documents (adjustable in `rag.py`)
4. **Model**: gemma:1b (fast, good quality)

---

## 🎯 What Questions Work Best?

✅ **Good Questions:**
- "What is the vacation policy?"
- "How many sick days do I get?"
- "What are the remote work rules?"
- "Tell me about benefits"

❌ **Won't Work:**
- "How many passengers survived?" (database query, not in PDF)
- "What is 2+2?" (general knowledge, not in PDF)
- Questions about data NOT in company_policy.pdf

---

## 🔐 Security Notes

- PDFs are processed locally (no external API)
- Embeddings stored in your PostgreSQL
- Ollama runs locally (no data sent to cloud)
- All data stays on your machine

---

## 📝 Summary

**You now have:**
1. ✅ PDF text extraction
2. ✅ Vector embeddings (768-dim)
3. ✅ Semantic search (pgvector)
4. ✅ Local LLM (Ollama)
5. ✅ RAG pipeline (retrieval + generation)

**Your chatbot can:**
- Answer questions from company_policy.pdf
- Find relevant information semantically
- Generate natural language responses
- Work completely offline (no external APIs)

---

**Next Steps:**
1. Run `ingest_company_policy.bat`
2. Start Ollama, Backend, Frontend
3. Ask questions about your company policy!
