# P Square RAG System Architecture

## 🏗️ Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React Frontend - Port 3000)                 │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Chat UI    │  │   Sidebar    │  │     Auth     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP POST /api/chat/
                              │ {question: "What is vacation policy?"}
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO BACKEND                             │
│                    (API Server - Port 8000)                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  views.py: ChatBotAPI                                    │  │
│  │  ↓                                                        │  │
│  │  rag.py: rag_query(question)                            │  │
│  │  ├─ Step 1: Generate embedding                          │  │
│  │  ├─ Step 2: Similarity search                           │  │
│  │  ├─ Step 3: Retrieve top 3 chunks                       │  │
│  │  └─ Step 4: Generate answer                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                                    │
           │ Step 1 & 4                        │ Step 2 & 3
           │ Ollama API                        │ SQL Query
           ↓                                    ↓
┌──────────────────────────┐    ┌──────────────────────────────┐
│   OLLAMA SERVER          │    │   POSTGRESQL DATABASE        │
│   (Port 11434)           │    │   (Port 5432)                │
│                          │    │                              │
│  Model: gemma:1b         │    │  ┌────────────────────────┐ │
│                          │    │  │  documents table       │ │
│  ┌────────────────────┐  │    │  │                        │ │
│  │ /api/embeddings    │  │    │  │  id | content |       │ │
│  │ Text → 768-dim     │  │    │  │     | embedding |     │ │
│  │ vector             │  │    │  │     | metadata        │ │
│  └────────────────────┘  │    │  │                        │ │
│                          │    │  │  pgvector extension    │ │
│  ┌────────────────────┐  │    │  │  (cosine similarity)   │ │
│  │ /api/generate      │  │    │  └────────────────────────┘ │
│  │ Prompt → Answer    │  │    │                              │
│  └────────────────────┘  │    │  Other tables:               │
│                          │    │  - User                      │
│                          │    │  - UserChat                  │
└──────────────────────────┘    │  - StateData                 │
                                │  - Titanic                   │
                                └──────────────────────────────┘
```

## 📊 RAG Pipeline Detailed Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION PHASE (One-time)                   │
└─────────────────────────────────────────────────────────────────┘

company_policy.pdf
    ↓
[PyPDF2] Extract text from all pages
    ↓
"Employees are entitled to 15 days of paid vacation per year..."
    ↓
[Chunking] Split into 500-char chunks with 50-char overlap
    ↓
Chunk 1: "Employees are entitled to 15 days..."
Chunk 2: "...vacation per year. Sick leave..."
Chunk 3: "...Sick leave policy allows 10 days..."
    ↓
[Ollama] Generate 768-dim embedding for each chunk
    ↓
Chunk 1 → [0.123, -0.456, 0.789, ..., 0.234]  (768 numbers)
Chunk 2 → [0.234, -0.567, 0.890, ..., 0.345]
Chunk 3 → [0.345, -0.678, 0.901, ..., 0.456]
    ↓
[PostgreSQL] Store in documents table
    ↓
┌──────────────────────────────────────────────────────────────┐
│ id │ content                    │ embedding      │ metadata  │
├────┼────────────────────────────┼────────────────┼───────────┤
│ 1  │ "Employees are entitled..." │ [0.123, ...]   │ {chunk:1} │
│ 2  │ "...vacation per year..."   │ [0.234, ...]   │ {chunk:2} │
│ 3  │ "...Sick leave policy..."   │ [0.345, ...]   │ {chunk:3} │
└──────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    QUERY PHASE (Every question)                 │
└─────────────────────────────────────────────────────────────────┘

User asks: "What is the vacation policy?"
    ↓
[Ollama] Generate embedding for question
    ↓
Question embedding: [0.120, -0.450, 0.785, ..., 0.230]
    ↓
[PostgreSQL + pgvector] Similarity search using <=> operator
    ↓
Calculate cosine distance between question and all chunks:
- Chunk 1: distance = 0.05 (very similar!)
- Chunk 2: distance = 0.12 (similar)
- Chunk 3: distance = 0.45 (less similar)
    ↓
[Retrieve] Top 3 most similar chunks
    ↓
Context = "
- Employees are entitled to 15 days of paid vacation per year...
- ...vacation per year. Sick leave policy allows 10 days...
- ...Sick leave policy allows 10 days per year...
"
    ↓
[Build Prompt]
"Based on the following context, answer the question.

Context:
- Employees are entitled to 15 days of paid vacation per year...
- ...vacation per year. Sick leave policy allows 10 days...

Question: What is the vacation policy?

Answer:"
    ↓
[Ollama LLM] Generate natural language answer
    ↓
"According to the company policy, employees are entitled to 
15 days of paid vacation per year."
    ↓
[Return to User]
```

## 🔄 Component Interactions

```
┌──────────────┐
│  ingest_pdf  │  (One-time setup)
└──────┬───────┘
       │
       ├─→ PyPDF2.PdfReader(company_policy.pdf)
       │   └─→ Extract text from pages
       │
       ├─→ chunk_text(text, size=500, overlap=50)
       │   └─→ Split into chunks
       │
       ├─→ ollama_service.generate_embedding(chunk)
       │   └─→ POST http://localhost:11434/api/embeddings
       │       └─→ Returns 768-dim vector
       │
       └─→ Document.objects.create(content, embedding, metadata)
           └─→ Store in PostgreSQL


┌──────────────┐
│  rag_query   │  (Every user question)
└──────┬───────┘
       │
       ├─→ ollama_service.generate_embedding(question)
       │   └─→ Convert question to vector
       │
       ├─→ similarity_search(query_embedding, top_k=3)
       │   └─→ SELECT content, metadata, (embedding <=> %s) as distance
       │       FROM documents
       │       ORDER BY distance
       │       LIMIT 3
       │   └─→ Returns 3 most similar chunks
       │
       ├─→ Build context from retrieved chunks
       │
       └─→ ollama_service.generate_response(prompt)
           └─→ POST http://localhost:11434/api/generate
               └─→ Returns natural language answer
```

## 🗄️ Database Schema Details

```sql
-- documents table (for RAG)
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,                    -- Original text chunk
    embedding VECTOR(768) NOT NULL,           -- 768-dimensional vector
    metadata JSONB DEFAULT '{}',              -- {source, chunk_id, type}
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for fast vector search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);

-- Example query (what happens during similarity search)
SELECT 
    content,
    metadata,
    (embedding <=> '[0.123, -0.456, ...]'::vector) as distance
FROM documents
ORDER BY distance ASC
LIMIT 3;
```

## 🔢 Vector Similarity Explained

```
Question: "What is vacation policy?"
Embedding: [0.12, -0.45, 0.78, ..., 0.23]  (768 numbers)

Document Chunks in Database:
┌────────────────────────────────────────────────────────────┐
│ Chunk 1: "Employees get 15 days vacation..."              │
│ Embedding: [0.13, -0.44, 0.79, ..., 0.22]                 │
│ Cosine Distance: 0.05  ← MOST SIMILAR (closest to 0)      │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Chunk 2: "Sick leave policy allows 10 days..."            │
│ Embedding: [0.25, -0.30, 0.65, ..., 0.18]                 │
│ Cosine Distance: 0.35  ← LESS SIMILAR                     │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Chunk 3: "Office hours are 9 AM to 5 PM..."               │
│ Embedding: [0.89, -0.12, 0.34, ..., 0.67]                 │
│ Cosine Distance: 0.82  ← NOT SIMILAR                      │
└────────────────────────────────────────────────────────────┘

Cosine Distance Formula:
distance = 1 - (A · B) / (||A|| × ||B||)

Where:
- A = question embedding
- B = document embedding
- Lower distance = More similar
- Range: 0 (identical) to 2 (opposite)
```

## 📦 File Structure

```
P Square/
│
├── backend/
│   ├── company_policy.pdf          ← Your PDF document
│   ├── ingest_pdf.py               ← PDF → Vector conversion
│   ├── verify_rag_setup.py         ← System verification
│   │
│   └── api/
│       ├── models.py               ← Document model (with VectorField)
│       ├── views.py                ← ChatBotAPI (calls rag_query)
│       ├── rag.py                  ← RAG pipeline logic
│       ├── ollama_service.py       ← Ollama API wrapper
│       └── embeddings.py           ← (legacy, not used)
│
├── frontend/
│   └── src/
│       ├── Components/
│       │   └── Chatbot.js          ← Chat interface
│       └── services/
│           └── authService.js      ← API calls
│
├── ingest_company_policy.bat       ← Run PDF ingestion
├── setup_rag_complete.bat          ← Full setup
├── start_all.bat                   ← Start all servers
│
└── Documentation/
    ├── RAG_SETUP_GUIDE.md          ← Detailed guide
    ├── RAG_QUICK_START.md          ← Quick reference
    └── RAG_ARCHITECTURE.md         ← This file
```

## 🎯 Key Concepts

### 1. Embeddings
- Convert text to numbers (vectors)
- Similar meanings → Similar vectors
- 768 dimensions = 768 numbers per text

### 2. Vector Database (pgvector)
- Store embeddings in PostgreSQL
- Fast similarity search
- Uses cosine distance

### 3. RAG (Retrieval Augmented Generation)
- Retrieval: Find relevant documents
- Augmented: Add context to prompt
- Generation: LLM creates answer

### 4. Chunking
- Split long text into smaller pieces
- Each chunk gets its own embedding
- Overlap prevents context loss

## 🚀 Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| PDF Ingestion | ~30s | One-time, for 10-page PDF |
| Embedding Generation | ~100ms | Per chunk |
| Vector Search | ~50ms | With 1000 chunks |
| LLM Response | ~2-5s | Depends on answer length |
| Total Query Time | ~3-6s | End-to-end |

## 🔐 Security & Privacy

```
┌─────────────────────────────────────────────────────────┐
│  ALL PROCESSING HAPPENS LOCALLY                         │
│                                                         │
│  ✅ PDF stays on your machine                          │
│  ✅ Embeddings generated locally (Ollama)              │
│  ✅ Vectors stored in your PostgreSQL                  │
│  ✅ LLM runs locally (Ollama)                          │
│  ✅ No data sent to external APIs                      │
│  ✅ No internet required (after setup)                 │
└─────────────────────────────────────────────────────────┘
```

---

**This architecture provides:**
- ✅ Fast semantic search
- ✅ Accurate context retrieval
- ✅ Natural language responses
- ✅ Complete privacy
- ✅ Offline capability
