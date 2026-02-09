import os
import json
import google.generativeai as genai
from django.db import connection

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def execute_sql_query(sql_query):
    """Execute SQL query safely"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            return columns, results
    except Exception as e:
        return None, str(e)

def get_database_schema():
    """Get database schema information"""
    return """
    Available tables:
    1. state_data: state (text), population (integer), income (decimal)
    2. titanic: passenger_id (int), survived (int), pclass (int), name (text), sex (text), age (float), fare (float)
    """

def is_greeting_or_general(user_question):
    """Check if the question is a greeting or general conversation"""
    greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'how are you', 'what can you do', 'help']
    question_lower = user_question.lower().strip()
    
    # Check for exact matches or if question starts with greeting
    for greeting in greetings:
        if question_lower == greeting or question_lower.startswith(greeting):
            return True
    
    # Check if question is too short and likely a greeting
    if len(question_lower.split()) <= 2 and any(word in question_lower for word in ['hi', 'hello', 'hey']):
        return True
        
    return False

def handle_greeting_or_general(user_question):
    """Handle greetings and general questions"""
    question_lower = user_question.lower().strip()
    
    if any(word in question_lower for word in ['hi', 'hello', 'hey']):
        return "Hello! I'm Solven, your intelligent chatbot. I can help you with questions about state data and Titanic passenger information. What would you like to know?"
    
    if 'how are you' in question_lower:
        return "I'm doing great, thank you for asking! I'm here to help you with data queries. What information are you looking for?"
    
    if any(word in question_lower for word in ['help', 'what can you do']):
        return "I can help you with:\n• State data queries (population, income)\n• Titanic passenger information (survival rates, demographics)\n• Just ask me questions like 'What is the population of Maharashtra?' or 'How many passengers survived?'"
    
    return "Hello! I'm Solven, your data assistant. I can help you explore state data and Titanic passenger information. What would you like to know?"

def process_user_query(user_question):
    """Process user question using Gemini API to generate SQL"""
    try:
        # Check if it's a greeting or general question first
        if is_greeting_or_general(user_question):
            return handle_greeting_or_general(user_question)
        
        schema = get_database_schema()
        
        prompt = f"""
        Convert this natural language question into a PostgreSQL query.
        
        Database Schema:
        {schema}
        
        User Question: {user_question}
        
        Rules:
        1. Generate only SELECT queries
        2. Use proper PostgreSQL syntax
        3. Handle complex conditions (age ranges, combined counts, etc.)
        4. For state data: use state_data table
        5. For Titanic data: use titanic table
        6. Return ONLY the SQL query
        
        Examples:
        "Population of Delhi" -> SELECT state, population FROM state_data WHERE LOWER(state) LIKE '%delhi%'
        "Combined count of male and female between age 20-40" -> SELECT sex, COUNT(*) FROM titanic WHERE age BETWEEN 20 AND 40 GROUP BY sex
        "How many survived" -> SELECT COUNT(*) FROM titanic WHERE survived = 1
        "States with income over 80000" -> SELECT state, income FROM state_data WHERE income > 80000
        
        SQL Query:
        """
        
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=200
            )
        )
        
        if not response.text:
            return "I'm having trouble understanding your question. Could you please rephrase it or ask about state data or Titanic information?"
        
        sql_query = response.text.strip()
        
        # Clean the response
        if sql_query.startswith('```sql'):
            sql_query = sql_query[6:-3]
        elif sql_query.startswith('```'):
            sql_query = sql_query[3:-3]
        
        sql_query = sql_query.strip()
        
        # Execute the generated SQL
        columns, results = execute_sql_query(sql_query)
        
        if columns is None:
            return "I couldn't find the information you're looking for. Please try asking about state data or Titanic passenger information."
        
        if not results:
            return "No data found for your query. Try asking about different states or Titanic passenger details."
        
        # Format response using Gemini
        return format_response_with_gemini(user_question, columns, results)
        
    except Exception as e:
        return "I'm having some technical difficulties. Please try asking a simpler question about state data or Titanic information."

def format_response_with_gemini(question, columns, results):
    """Use Gemini to format the database results into natural language"""
    try:
        # Limit results to prevent overwhelming response
        limited_results = results[:10]  # Show up to 10 results
        
        # Convert results to readable format
        data_text = f"Columns: {', '.join(columns)}\n"
        for i, row in enumerate(limited_results):
            data_text += f"Row {i+1}: {', '.join(map(str, row))}\n"
        
        if len(results) > 10:
            data_text += f"... and {len(results) - 10} more results\n"
        
        prompt = f"""
        Convert this database result into a natural, conversational response for the user's question.
        
        User Question: {question}
        Database Results:
        {data_text}
        
        Instructions:
        1. Write a clear, natural response
        2. Include specific numbers and names from the data
        3. Keep it concise but complete
        4. Don't mention technical database terms
        5. If there are many results, summarize the key findings
        
        Response:
        """
        
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1000
            )
        )
        
        if response.text:
            return response.text.strip()
        else:
            # Fallback formatting
            return format_results_fallback(results, columns)
        
    except Exception as e:
        # Fallback to simple formatting
        return format_results_fallback(results, columns)

def format_results_fallback(results, columns):
    """Fallback formatting when Gemini fails"""
    if len(results) == 1 and len(results[0]) == 1:
        return f"Result: {results[0][0]}"
    elif len(results) == 1:
        return f"Result: {', '.join(map(str, results[0]))}"
    else:
        formatted = []
        limited_results = results[:10]  # Show up to 10 results
        for i, row in enumerate(limited_results):
            formatted.append(f"{i+1}. {', '.join(map(str, row))}")
        
        response = "Results:\n" + '\n'.join(formatted)
        if len(results) > 10:
            response += f"\n... and {len(results) - 10} more results"
        return response

def summarize_text(text):
    """Summarize long text for chat history using Gemini API"""
    if len(text) <= 50:
        return text
    
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"Summarize this text in exactly 5-7 words: {text}"
        response = model.generate_content(prompt)
        if response.text:
            summary = response.text.strip()
            # Ensure it's not too long
            if len(summary) > 50:
                return text[:47] + "..."
            return summary
        else:
            return text[:47] + "..."
    except Exception as e:
        # Fallback to simple truncation
        return text[:47] + "..."

def extract_query(user_question):
    """Legacy function - kept for compatibility"""
    return process_user_query(user_question)