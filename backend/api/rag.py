import requests
import hashlib
from django.db import connection

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:1b"

def get_embedding(text):
    """Create 768-dim embedding from text"""
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()
    
    embedding = []
    for i in range(768):
        embedding.append(float(hash_bytes[i % len(hash_bytes)]) / 255.0)
    
    return embedding

def similarity_search(query, top_k=3):
    """Search similar documents using pgvector"""
    query_embedding = get_embedding(query)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata
            FROM documents
            WHERE metadata->>'source' = 'titanic'
            ORDER BY embedding <-> %s::vector
            LIMIT %s
        """, [query_embedding, top_k])
        
        results = cursor.fetchall()
    
    return [{"content": row[0], "metadata": row[1]} for row in results]

def generate_answer(context, question):
    """Generate answer using Ollama"""
    prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {question}

Answer:"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        return f"Error: {str(e)}"

def rag_query(question):
    """Complete RAG pipeline"""
    docs = similarity_search(question, top_k=3)
    
    if not docs:
        return "No relevant information found in the database."
    
    context = "\n\n".join([f"- {doc['content']}" for doc in docs])
    answer = generate_answer(context, question)
    
    return answer
