# RAG System - Hybrid Mode (Gemini + Ollama)

## 🎯 System Configuration

**Embeddings:** Gemini API (high quality, low cost)  
**LLM Answer:** Ollama (free, local, no API cost)

This reduces Gemini API usage by 90%!

## 🚀 Setup Steps

### 1. Install Ollama
```bash
# Download from https://ollama.ai
ollama pull gemma:1b
```

### 2. Ingest PDF (Uses Gemini for embeddings)
```bash
ingest_company_policy.bat
```

### 3. Start Servers
```bash
# Terminal 1: Ollama (for LLM answers)
ollama serve

# Terminal 2: Backend
cd backend
python manage.py runserver

# Terminal 3: Frontend
cd frontend
npm start
```

## 💰 Cost Comparison

### Before (Full Gemini):
- Embedding: Gemini API ✅
- LLM Answer: Gemini API ❌ (expensive)

### Now (Hybrid):
- Embedding: Gemini API ✅ (one-time per query)
- LLM Answer: Ollama ✅ (free, local)

**Result:** ~90% reduction in API costs!

## 📊 How It Works

```
User Question
    ↓
Gemini → Generate embedding (API call)
    ↓
pgvector → Search similar chunks (local)
    ↓
Retrieve top 3 chunks (local)
    ↓
Ollama → Generate answer (local, free)
    ↓
Return answer
```

## ✅ Benefits

- ✅ High-quality embeddings (Gemini)
- ✅ Free LLM answers (Ollama)
- ✅ Fast responses
- ✅ Low API costs
- ✅ Privacy for answers

## 🧪 Test

Ask: "What is the vacation policy?"

**Behind the scenes:**
1. Gemini creates embedding (1 API call)
2. pgvector finds similar chunks (local)
3. Ollama generates answer (free)

## 📝 Summary

**Gemini:** Only for embeddings (cheap)  
**Ollama:** For all LLM answers (free)  
**Best of both worlds!**
