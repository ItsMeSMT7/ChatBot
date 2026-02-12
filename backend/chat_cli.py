"""
Interactive CLI for P Square RAG System
Run this to chat with your database/PDFs from the command line.
"""
import os
import sys
import django

# Setup Django environment
# This allows us to access the database and RAG logic
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.rag import rag_query

def start_chat():
    print("=" * 60)
    print("🤖 P Square RAG Chat (Connected to Local Database)")
    print("=" * 60)
    print("This interface uses your ingested PDFs and SQL database.")
    print("It will NOT use general internet knowledge for specific queries.")
    print("Type 'exit' or 'quit' to stop.")
    print("-" * 60)

    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for exit command
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue

            print("Thinking...", end="\r")
            
            # Send to RAG pipeline (same logic as the frontend)
            response = rag_query(user_input)
            
            # Clear thinking message and print response
            print(" " * 20, end="\r")
            print(f"Bot: {response}")

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    start_chat()