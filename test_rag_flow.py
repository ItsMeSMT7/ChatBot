"""
End-to-End RAG Test
Tests: React → Django → pgvector → Ollama → Django → React
"""

import requests

API_URL = "http://localhost:8000/api/chat/"
TOKEN = "YOUR_TOKEN_HERE"  # Replace with actual token

def test_rag():
    questions = [
        "Who was the oldest passenger?",
        "How many passengers survived?",
        "Tell me about first class passengers"
    ]
    
    print("=" * 60)
    print("RAG End-to-End Test")
    print("=" * 60)
    
    for question in questions:
        print(f"\nQ: {question}")
        
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Token {TOKEN}",
                "Content-Type": "application/json"
            },
            json={"question": question}
        )
        
        if response.status_code == 200:
            answer = response.json()["answer"]
            print(f"A: {answer}\n")
        else:
            print(f"Error: {response.status_code}\n")
    
    print("=" * 60)

if __name__ == "__main__":
    test_rag()
