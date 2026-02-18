import re
from django.db import connection
from api.ollama_service import generate_embedding, generate_response

def similarity_search(query, top_k=3):
    """
    Hybrid Search: Combines Vector Search (Semantic) + Keyword Search (Exact Match)
    """
    query_embedding = generate_embedding(query)
    
    # 1. Vector Search (Semantic)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata, (embedding <=> %s::vector) as distance
            FROM document_chunks
            ORDER BY distance
            LIMIT %s
        """, [query_embedding, top_k])
        vector_results = cursor.fetchall()

    # 2. Keyword Search (Exact Match using PostgreSQL Full-Text Search)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT content, metadata, 0.0 as distance
            FROM document_chunks
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
            LIMIT %s
        """, [query, top_k])
        keyword_results = cursor.fetchall()
    
    # 3. Combine & Deduplicate
    # We use a dictionary to merge results, preferring vector results (preserving distance)
    combined_results = {}
    
    for row in vector_results:
        combined_results[row[0]] = {"content": row[0], "metadata": row[1], "distance": row[2]}
        
    for row in keyword_results:
        if row[0] not in combined_results:
            # Assign 0.0 distance for exact keyword matches (high priority)
            combined_results[row[0]] = {"content": row[0], "metadata": row[1], "distance": 0.0}
            
    # Convert back to list and sort by distance
    final_results = list(combined_results.values())
    final_results.sort(key=lambda x: x['distance'])
    
    return final_results[:top_k]

def rag_query(question, chat_history=None):
    # -------------------------
    # 0️⃣ Contextualize Question (Memory)
    # -------------------------
    search_query = question
    
    if chat_history and len(chat_history) > 0:
        # Format history for the LLM
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-4:]])
        
        rewrite_prompt = f"""
Given the following conversation history and a follow-up question, rephrase the follow-up question to be a standalone question that can be understood without the history.

Chat History:
{history_text}

Follow-up Question: {question}

Standalone Question:
"""
        # Get the rewritten question
        rewritten = generate_response(rewrite_prompt).strip()
        # Basic cleanup if LLM is chatty
        if "Standalone Question:" in rewritten:
            rewritten = rewritten.split("Standalone Question:")[-1].strip()
            
        print(f"DEBUG: Original: '{question}' -> Rewritten: '{rewritten}'")
        search_query = rewritten

    question_lower = search_query.lower()

    # -------------------------
    # 1️⃣ Ask LLM to classify question
    # -------------------------
    classification_prompt = f"""
Classify the user's question into ONE of the following categories:
- database: For questions about Titanic passengers, such as counts, details, ages, survival, fares, or lists (e.g., "show me details of women", "how many men").
- knowledge: For questions about company policy, employment, leave, travel, office environment, or any specific terms defined in the documents.
- conversational: ONLY for greetings (hello, hi) or simple pleasantries.
- irrelevant: For questions completely unrelated to the Titanic dataset or company policy.
 
Return ONLY one word.

Question:
{search_query}
"""

    question_type = generate_response(classification_prompt).strip().lower()
    print(f"DEBUG: Question '{search_query}' classified as: {question_type}")

    # -------------------------
    # 2️⃣ If Database → Generate SQL
    # -------------------------
    if "database" in question_type:

        sql_prompt = f"""
You are a PostgreSQL expert tasked with converting natural language questions into PostgreSQL queries for the 'titanic' table.

Table Schema:
- table_name: titanic
- columns:
  - survived: INTEGER (0 = No, 1 = Yes)
  - pclass: INTEGER (Passenger Class: 1, 2, 3)
  - sex: TEXT ('male', 'female')
  - age: FLOAT (can be NULL)
  - sibsp: INTEGER (Number of Siblings/Spouses Aboard)
  - parch: INTEGER (Number of Parents/Children Aboard)
  - fare: FLOAT
  - embarked: TEXT (Port of Embarkation: 'C' = Cherbourg, 'Q' = Queenstown, 'S' = Southampton)

STRICT RULES:
1.  **Return ONLY raw SQL.** No markdown, no explanations, just the query.
2.  Use exact column names and values (e.g., `sex = 'female'`, not `'woman'`).
3.  When filtering by age, always exclude NULLs (e.g., `WHERE age IS NOT NULL AND ...`).
4.  For general counts of passengers, use `COUNT(*)`.
5.  For questions about survival, use `survived = 1`. For non-survival, use `survived = 0`.
6.  Do NOT add `survived = 1` unless the user explicitly asks about survival.
7.  Map 'women'/'woman' to `sex = 'female'` and 'men'/'man' to `sex = 'male'`.

Examples:
- User Question: "How many passengers survived?"
  SQL Query: SELECT COUNT(*) FROM titanic WHERE survived = 1;

- User Question: "What is the total count of passengers?"
  SQL Query: SELECT COUNT(*) FROM titanic;

- User Question: "how many passengers were in pclass 1"
  SQL Query: SELECT COUNT(*) FROM titanic WHERE pclass = 1;

- User Question: "count of male and female passengers"
  SQL Query: SELECT sex, COUNT(*) FROM titanic GROUP BY sex;

- User Question: "give me details of women age group between 20 to 50"
  SQL Query: SELECT * FROM titanic WHERE sex = 'female' AND age BETWEEN 20 AND 50;

User Question:
{search_query}

SQL Query:
"""

        sql_query = generate_response(sql_prompt).strip()

        # ✅ Remove markdown formatting if LLM adds it
        match = re.search(r"```(?:sql)?\s*(.*?)```", sql_query, re.DOTALL | re.IGNORECASE)
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # ✅ Safety check (block dangerous queries)
        forbidden_keywords = ["drop", "delete", "update", "insert", "alter", "truncate"]
        if any(keyword in sql_query.lower() for keyword in forbidden_keywords):
            return "Unsafe query detected."

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()

            # ✅ Better formatting
            if not result:
                return "No records found."

            if len(result) == 1 and len(result[0]) == 1:
                return f"The answer is {result[0][0]}."

            return f"Query Result: {result}"

        except Exception as e:
            return f"Error executing generated SQL: {str(e)}"

    # -------------------------
    # 3️⃣ If Knowledge → Use RAG
    # -------------------------
    if "knowledge" in question_type:

        docs = similarity_search(search_query, top_k=5)

        if not docs:
            return "No relevant information found."

        context = "\n\n".join([doc["content"] for doc in docs])

        prompt = f"""You are a helpful assistant. Your task is to answer the user's question based *only* on the provided context.
Do not mention the context in your answer. Just provide the answer directly.
If the information is not in the context, state that the answer is not available in the provided data.

### Context:
{context}

### User's Question:
{search_query}

### Answer:
"""

        return generate_response(prompt)

    if "conversational" in question_type:
        # Simple conversational response
        return generate_response(f"Respond politely to this conversational input: {search_query}")

    # -------------------------
    # 4️⃣ Irrelevant
    # -------------------------
    return "Please ask a question related to the dataset."


# def rag_query(question):
#     """Complete RAG pipeline with Ollama"""
#     docs = similarity_search(question, top_k=3)
    
#     if not docs:
#         return "No relevant information found in the knowledge base."
    
#     context = "\n\n".join([f"- {doc['content']}" for doc in docs])
    
#     prompt = f"""Based on the following context, answer the question.

# Context:
# {context}

# Question: {question}

# Answer:"""
    
#     answer = generate_response(prompt)
#     return answer
