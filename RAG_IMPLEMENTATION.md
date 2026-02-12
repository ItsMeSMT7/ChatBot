# Hybrid RAG Implementation Guide

## 📂 Core Files

| File | Purpose |
| :--- | :--- |
| `backend/api/rag.py` | **The Brain**. Handles classification, routing, and logic. |
| `backend/api/ollama_service.py` | **The Bridge**. Communicates with the local Ollama instance. |
| `backend/ingest_pdf.py` | **The Loader**. Processes PDFs into vector embeddings. |
| `backend/api/models.py` | **The Data**. Defines the database structure. |

---

## 🧠 1. The Brain (`rag.py`)

The `rag_query` function is the main entry point. It orchestrates the entire flow.

```python
def rag_query(user_question):
    # Step 1: Classify Intent
    intent = classify_intent(user_question)
    
    # Step 2: Route to appropriate handler
    if intent == 'database':
        return handle_sql_query(user_question)
    elif intent == 'knowledge':
        return handle_knowledge_query(user_question)
    elif intent == 'conversational':
        return handle_conversational(user_question)
    else:
        return "I'm not sure how to help with that."
```

### Intent Classification
We use a specialized prompt to force the LLM to output a single category keyword.

```python
CLASSIFICATION_PROMPT = """
You are a router. Classify the following question into one of these categories:
- database: Questions about Titanic passengers, stats, numbers.
- knowledge: Questions about Company Policy, rules, leave, benefits.
- conversational: Greetings, hi, hello, thanks.

Question: {question}
Category:
"""
```

---

## 🌉 2. The Bridge (`ollama_service.py`)

This service handles raw HTTP requests to the local Ollama API.

### Generating Embeddings
Used for both ingestion and retrieval.

```python
def generate_embedding(text):
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return response.json()["embedding"]
```

### Generating Text
Used for SQL generation and final answers.

```python
def generate_response(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "gemma3:1b",
            "prompt": prompt,
            "stream": False
        }
    )
    return response.json()["response"]
```

---

## 📥 3. The Loader (`ingest_pdf.py`)

This script is run once to populate the vector database.

**Logic:**
1.  **Extract Text**: Uses `PyPDF2` to read the PDF page by page.
2.  **Chunking**: Splits text into 500-character segments with 50-character overlap to preserve context across boundaries.
3.  **Embedding**: Calls `ollama_service.generate_embedding` for each chunk.
4.  **Storage**: Saves to PostgreSQL.

```python
# Pseudocode for chunking
chunk_size = 500
overlap = 50

for i in range(0, len(text), chunk_size - overlap):
    chunk = text[i : i + chunk_size]
    vector = generate_embedding(chunk)
    Document.objects.create(content=chunk, embedding=vector)
```

---

## 🗄️ 4. Database Schema (`models.py`)

We use the `pgvector` extension to store high-dimensional vectors.

```python
from pgvector.django import VectorField

class Document(models.Model):
    content = models.TextField()
    # 768 dimensions matches nomic-embed-text output
    embedding = VectorField(dimensions=768) 
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
pip install django djangorestframework psycopg2-binary pgvector requests PyPDF2
```

### 2. Enable pgvector in PostgreSQL
```sql
CREATE EXTENSION vector;
```

### 3. Run Ingestion
```bash
python ingest_pdf.py
```

### 4. Start Server
```bash
python manage.py runserver
```