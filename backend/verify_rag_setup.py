"""
RAG System Verification Script

Checks if all components are ready for RAG workflow
"""

import os
import sys
import requests

def check_ollama():
    """Check if Ollama is running"""
    print("1. Checking Ollama server...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if any('gemma' in name for name in model_names):
                print("   ✓ Ollama is running")
                print(f"   ✓ Models available: {', '.join(model_names)}")
                return True
            else:
                print("   ✗ Gemma model not found")
                print("   Run: ollama pull gemma:1b")
                return False
        else:
            print("   ✗ Ollama not responding")
            return False
    except Exception as e:
        print(f"   ✗ Ollama not running: {str(e)}")
        print("   Run: ollama serve")
        return False

def check_pdf():
    """Check if company_policy.pdf exists"""
    print("\n2. Checking PDF file...")
    if os.path.exists("company_policy.pdf"):
        size = os.path.getsize("company_policy.pdf")
        print(f"   ✓ company_policy.pdf found ({size} bytes)")
        return True
    else:
        print("   ✗ company_policy.pdf not found in backend folder")
        return False

def check_database():
    """Check if documents table has data"""
    print("\n3. Checking database...")
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        django.setup()
        
        from api.models import Document
        count = Document.objects.count()
        
        if count > 0:
            print(f"   ✓ Database has {count} document chunks")
            
            # Show sample
            sample = Document.objects.first()
            print(f"   ✓ Sample content: {sample.content[:80]}...")
            return True
        else:
            print("   ✗ No documents in database")
            print("   Run: python ingest_pdf.py")
            return False
    except Exception as e:
        print(f"   ✗ Database check failed: {str(e)}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n4. Checking dependencies...")
    try:
        import PyPDF2
        print("   ✓ PyPDF2 installed")
    except ImportError:
        print("   ✗ PyPDF2 not installed")
        print("   Run: pip install PyPDF2==3.0.1")
        return False
    
    try:
        import requests
        print("   ✓ requests installed")
    except ImportError:
        print("   ✗ requests not installed")
        return False
    
    return True

def main():
    print("=" * 50)
    print("  RAG System Verification")
    print("=" * 50)
    
    checks = [
        check_dependencies(),
        check_ollama(),
        check_pdf(),
        check_database()
    ]
    
    print("\n" + "=" * 50)
    if all(checks):
        print("✓ ALL CHECKS PASSED - System Ready!")
        print("\nYou can now:")
        print("1. Start backend: python manage.py runserver")
        print("2. Start frontend: cd ../frontend && npm start")
        print("3. Ask questions about company policy!")
    else:
        print("✗ Some checks failed - Please fix issues above")
    print("=" * 50)

if __name__ == "__main__":
    main()
