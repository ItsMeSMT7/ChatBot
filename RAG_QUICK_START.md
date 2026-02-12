# RAG System - Quick Reference

## 🚀 Quick Start (First Time)

```bash
1. setup_rag_complete.bat          # Install & verify
2. ingest_company_policy.bat       # Load PDF into database
3. start_all.bat                   # Start everything
```

## 📋 Daily Usage

```bash
start_all.bat                      # Starts Ollama + Backend + Frontend
```

## 🔧 System Components

| Component | Purpose | Port/Location |
|-----------|---------|---------------|
| **Ollama** | Embeddings + LLM | localhost:11434 |
| **Django Backend** | API Server | localhost:8000 |
| **React Frontend** | User Interface | localhost:3000 |
| **PostgreSQL** | Vector Database | localhost:5432 |

## 📊 Data Flow

```
User Question
    ↓
[Frontend] Send to /api/chat/
    ↓
[Backend] rag_query(question)
    ↓
[Ollama] Generate embedding
    ↓
[PostgreSQL] Search similar vectors (pgvector)
    ↓
[Backend] Get top 3 chunks
    ↓
[Ollama] Generate answer from context
    ↓
[Frontend] Display response
```

## 🧪 Test Commands

### Check Ollama
```bash
curl http://localhost:11434/api/tags
```

### Check Documents
```bash
cd backend
python manage.py shell
>>> from api.models import Document
>>> Document.objects.count()
```

### Test RAG
```bash
cd backend
python verify_rag_setup.py
```

## 📝 Sample Questions

**About Company Policy (RAG):**
- "What is the vacation policy?"
- "How many sick days do I get?"
- "What are the working hours?"
- "Tell me about remote work policy"

## 🔄 Re-ingest PDF

If you update company_policy.pdf:
```bash
ingest_company_policy.bat
```

## 🐛 Common Issues

| Problem | Solution |
|---------|----------|
| "Ollama not found" | Run: `ollama serve` |
| "No documents found" | Run: `ingest_company_policy.bat` |
| "PyPDF2 error" | Run: `pip install PyPDF2==3.0.1` |
| "Port in use" | Close other instances |

## 📁 Key Files

```
backend/
├── ingest_pdf.py              # PDF → Vector conversion
├── verify_rag_setup.py        # System verification
├── api/
│   ├── rag.py                 # RAG pipeline
│   ├── ollama_service.py      # Ollama integration
│   └── views.py               # API endpoints
└── company_policy.pdf         # Your PDF document

Root/
├── ingest_company_policy.bat  # Load PDF
├── setup_rag_complete.bat     # Full setup
└── start_all.bat              # Start servers
```

## 🎯 What's Happening Behind the Scenes

1. **PDF Ingestion**: 
   - Extracts text → Chunks (500 chars) → Embeddings (768-dim) → PostgreSQL

2. **Query Processing**:
   - Question → Embedding → Similarity search → Top 3 chunks → LLM → Answer

3. **Vector Search**:
   - Uses cosine similarity (<=> operator in pgvector)
   - Finds semantically similar content

## 💡 Tips

- Keep Ollama running in background
- Chunk size: 500 chars (adjustable in ingest_pdf.py)
- Top K: 3 documents (adjustable in rag.py)
- Model: gemma:1b (fast, good quality)

## 🔐 Privacy

✅ Everything runs locally
✅ No external API calls
✅ Data stays on your machine
✅ Ollama processes locally

---

**Need Help?** Check `RAG_SETUP_GUIDE.md` for detailed documentation.
