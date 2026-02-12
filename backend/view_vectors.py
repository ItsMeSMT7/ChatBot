import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Document

def view_vectors():
    print("=== Checking Vector Data in PostgreSQL ===\n")
    
    # 1. Check Company Policy Data
    policy_doc = Document.objects.filter(metadata__source='company_policy').first()
    if policy_doc:
        print(f"--- Company Policy Document (ID: {policy_doc.id}) ---")
        print(f"Text Content: \"{policy_doc.content[:60]}...\"")
        print(f"Vector Length: {len(policy_doc.embedding)} dimensions")
        print(f"Vector Data (First 5 numbers): {policy_doc.embedding[:5]}...")
    else:
        print("No Company Policy vectors found.")

    print("\n" + "-"*40 + "\n")

    # 2. Check Titanic Data
    titanic_doc = Document.objects.filter(metadata__source='titanic').first()
    if titanic_doc:
        print(f"--- Titanic Document (ID: {titanic_doc.id}) ---")
        print(f"Text Content: \"{titanic_doc.content[:60]}...\"")
        print(f"Vector Length: {len(titanic_doc.embedding)} dimensions")
        print(f"Vector Data (First 5 numbers): {titanic_doc.embedding[:5]}...")
    else:
        print("No Titanic vectors found.")

if __name__ == "__main__":
    view_vectors()