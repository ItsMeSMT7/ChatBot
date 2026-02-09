import requests
import json

def test_chatbot_api():
    """Test the chatbot API with various queries"""
    api_url = "http://localhost:8000/api/chat/"
    
    test_queries = [
        "What is the population of Maharashtra?",
        "Show me the income of Karnataka",
        "How many passengers survived on Titanic?",
        "What is the average age of Titanic passengers?",
        "List states with population over 50000",
        "How many male passengers were on Titanic?"
    ]
    
    print("Testing Chatbot API...")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        
        try:
            response = requests.post(
                api_url,
                json={"question": query},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Answer: {data.get('answer', 'No answer received')}")
            else:
                print(f"   Error: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("   Error: Cannot connect to backend. Make sure Django server is running.")
        except Exception as e:
            print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("API testing completed!")

if __name__ == "__main__":
    test_chatbot_api()