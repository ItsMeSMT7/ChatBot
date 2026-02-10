# RAG Pipeline - Quick Reference

## 🚀 Quick Start

```bash
# 1. Setup (one time)
setup_rag.bat

# 2. Start Ollama
ollama serve

# 3. Start backend
cd backend
python manage.py runserver

# 4. Start frontend
cd frontend
npm start
```

---

## 📁 File Structure

```
backend/
├── api/
│   ├── models.py              # Document model with VectorField
│   ├── ollama_service.py      # Embedding & LLM functions
│   ├── rag_service.py         # Core RAG logic
│   └── views.py               # ChatBotAPI (uses RAG)
├── ingest_data.py             # Load documents into DB
└── backend/settings.py        # Added pgvector.django
```

---

## 🔑 Key Functions

### **Generate Embedding**
```python
from api.ollama_service import generate_embedding
embedding = generate_embedding("your text here")
# Returns: [0.123, -0.456, ...] (768 dimensions)
```

### **Similarity Search**
```python
from api.rag_service import similarity_search
docs = similarity_search("user question", top_k=3)
# Returns: [{"content": "...", "similarity_score": 0.85}, ...]
```

### **Full RAG Query**
```python
from api.rag_service import rag_query
answer = rag_query("What is P Square?")
# Returns: "P Square is an intelligent chatbot..."
```

---

## 📝 Adding New Documents

### **Method 1: Edit ingest_data.py**
```python
KNOWLEDGE_BASE = [
    {
        "content": "Your document text here",
        "metadata": {"category": "faq"}
    },
]
```
Then run: `python ingest_data.py`

### **Method 2: Django Shell**
```python
python manage.py shell

from api.models import Document
from api.ollama_service import generate_embedding

text = "Your new document"
embedding = generate_embedding(text)
Document.objects.create(content=text, embedding=embedding)
```

### **Method 3: Bulk Import**
```python
import csv
from api.models import Document
from api.ollama_service import generate_embedding

with open('data.csv') as f:
    for row in csv.DictReader(f):
        emb = generate_embedding(row['text'])
        Document.objects.create(content=row['text'], embedding=emb)
```

---

## 🧪 Testing Commands

```bash
# Check documents count
python manage.py shell -c "from api.models import Document; print(Document.objects.count())"

# Test embedding generation
curl http://localhost:11434/api/embeddings -d '{"model":"gemma:1b","prompt":"test"}'

# Test RAG via API
curl -X POST http://localhost:8000/api/chat/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is P Square?"}'
```

---

## 🎯 RAG Pipeline Flow

```
User: "What is P Square?"
    ↓
1. Convert question to embedding [0.12, -0.34, ...]
    ↓
2. Search similar docs in PostgreSQL (cosine similarity)
    ↓
3. Retrieve top 3 documents
    ↓
4. Build prompt:
   "Context: [doc1, doc2, doc3]
    Question: What is P Square?
    Answer only from context."
    ↓
5. Send to Ollama LLM
    ↓
6. Return: "P Square is an intelligent chatbot system..."
```

---

## ⚙️ Configuration

### **Change Top-K (number of retrieved docs)**
```python
# In api/rag_service.py, line ~45
retrieved_docs = similarity_search(user_question, top_k=5)  # Default: 3
```

### **Change LLM Model**
```python
# In api/ollama_service.py, line ~30
"model": "llama2"  # Options: gemma:1b, llama2, mistral
```

### **Change Embedding Model**
```python
# In api/ollama_service.py, line ~15
"model": "nomic-embed-text"  # Better embeddings
```

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| "pgvector not found" | `CREATE EXTENSION vector;` in PostgreSQL |
| "Ollama connection refused" | Run `ollama serve` |
| "No documents found" | Run `python ingest_data.py` |
| "Dimension mismatch" | Re-ingest all documents with same model |

---

## 📊 Database Schema

```sql
-- documents table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Similarity search query
SELECT content, (embedding <=> '[0.1, 0.2, ...]'::vector) AS distance
FROM documents
ORDER BY distance
LIMIT 3;
```

---

## 🔄 Request-Response Flow

### **Frontend (React)**
```javascript
fetch('http://localhost:8000/api/chat/', {
    method: 'POST',
    headers: {
        'Authorization': 'Token abc123',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({ question: "What is P Square?" })
})
```

### **Backend (Django)**
```python
# views.py - ChatBotAPI
question = request.data.get("question")
answer = rag_query(question)  # RAG pipeline
return Response({"answer": answer})
```

### **RAG Service**
```python
# rag_service.py
1. query_embedding = generate_embedding(question)
2. docs = similarity_search(question, top_k=3)
3. prompt = build_rag_prompt(question, docs)
4. answer = generate_response(prompt)  # Ollama
5. return answer
```

---

## 📈 Performance Optimization

```sql
-- Add vector index for faster search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Analyze table
ANALYZE documents;
```

---

## 🎓 Key Concepts

- **Embedding**: Text → 768-dim vector (captures meaning)
- **Cosine Similarity**: Measures angle between vectors (0-1)
- **Top-K**: Retrieve K most similar documents
- **RAG**: Retrieval + Augmentation + Generation
- **pgvector**: PostgreSQL extension for vector operations

---

## 📞 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/` | POST | RAG-powered chat (main) |
| `/api/database-query/` | POST | Legacy Gemini queries (optional) |
| `/api/signup/` | POST | User registration |
| `/api/login/` | POST | User authentication |
| `/api/chats/` | GET/POST/PUT/DELETE | Chat history |

---

## ✅ Checklist

- [ ] pgvector extension enabled
- [ ] Ollama running (`ollama serve`)
- [ ] Documents ingested (`python ingest_data.py`)
- [ ] Migrations applied (`python manage.py migrate`)
- [ ] Backend running (port 8000)
- [ ] Frontend running (port 3000)
- [ ] Test query successful

---

**Ready to use!** Your RAG pipeline is fully operational. 🚀
