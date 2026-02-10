"""
RAG Service - Retrieval Augmented Generation

This is the core RAG pipeline that:
1. Takes user question
2. Finds relevant documents (retrieval)
3. Builds context-aware prompt (augmentation)
4. Generates answer from LLM (generation)
"""

from api.models import Document
from api.ollama_service import generate_embedding, generate_response
from django.db import connection

def similarity_search(query_text, top_k=3):
    """
    WHAT: Finds the most similar documents to the query
    WHY: We need relevant context to answer the question accurately
    
    HOW IT WORKS:
    - Converts query to embedding vector
    - Uses cosine similarity (<=> operator in pgvector)
    - Returns top_k most similar documents
    
    COSINE SIMILARITY:
    - Measures angle between two vectors
    - Range: -1 (opposite) to 1 (identical)
    - Higher score = more similar
    - Formula: cos(θ) = (A·B) / (||A|| ||B||)
    """
    # Generate embedding for user query
    query_embedding = generate_embedding(query_text)
    
    # Perform similarity search using pgvector
    # <=> is cosine distance operator (lower = more similar)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata, (embedding <=> %s::vector) as distance
            FROM documents
            ORDER BY distance
            LIMIT %s
        """, [query_embedding, top_k])
        
        results = cursor.fetchall()
    
    # Convert to list of dicts
    documents = [
        {
            "content": row[0],
            "metadata": row[1],
            "similarity_score": 1 - row[2]  # Convert distance to similarity
        }
        for row in results
    ]
    
    return documents

def build_rag_prompt(user_question, retrieved_docs):
    """
    WHAT: Constructs a prompt with context and instructions
    WHY: LLM needs context and clear instructions to answer accurately
    
    RAG PROMPT STRUCTURE:
    1. System instruction (how to behave)
    2. Retrieved context (relevant knowledge)
    3. User question
    4. Constraints (answer only from context)
    """
    # Combine retrieved documents into context
    context = "\n\n".join([
        f"Document {i+1}: {doc['content']}"
        for i, doc in enumerate(retrieved_docs)
    ])
    
    # Build RAG prompt
    prompt = f"""You are a helpful assistant. Answer the question based ONLY on the provided context.

Context:
{context}

Question: {user_question}

Instructions:
- Answer based ONLY on the context above
- If the context doesn't contain the answer, say "I don't have information about that in my knowledge base."
- Be concise and accurate
- Do not make up information

Answer:"""
    
    return prompt

def rag_query(user_question):
    """
    WHAT: Complete RAG pipeline
    WHY: Orchestrates retrieval, augmentation, and generation
    
    FLOW:
    User Question → Embedding → Similarity Search → Retrieve Docs 
    → Build Prompt → LLM Generation → Answer
    """
    try:
        # Step 1: Retrieve relevant documents
        retrieved_docs = similarity_search(user_question, top_k=3)
        
        if not retrieved_docs:
            return "I don't have any information in my knowledge base yet."
        
        # Step 2: Build RAG prompt with context
        prompt = build_rag_prompt(user_question, retrieved_docs)
        
        # Step 3: Generate answer using local LLM
        answer = generate_response(prompt)
        
        return answer
        
    except Exception as e:
        return f"Error processing query: {str(e)}"
