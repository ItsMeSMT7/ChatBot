#!/usr/bin/env python
import subprocess
import threading
import time
import webbrowser
import os
import sys
import django

def setup_rag():
    """Setup RAG on first run"""
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        django.setup()
        from django.core.management import execute_from_command_line
        from django.db import connection
        from api.models import Document
        
        print("📦 Setting up database...")
        execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
        
        with connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;')
        
        if not Document.objects.exists():
            print("📚 Loading RAG documents...")
            subprocess.run([sys.executable, 'ingest_data.py'], cwd=os.path.dirname(__file__))
        
        print("✅ RAG setup complete")
    except Exception as e:
        print(f"⚠️  RAG setup skipped: {e}")

def start_ollama():
    """Start Ollama server"""
    try:
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("🤖 Ollama started")
    except:
        print("⚠️  Ollama not started (optional)")

def start_frontend():
    """Start React frontend"""
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        subprocess.run(['npm', 'start'], cwd=frontend_path, shell=True)
    except Exception as e:
        print(f'Frontend error: {e}')

def open_browser():
    """Open browser"""
    time.sleep(5)
    webbrowser.open('http://localhost:3000')

if __name__ == '__main__':
    print("🚀 Starting P Square Application...")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 Backend: http://localhost:8000")
    print("🤖 Ollama: http://localhost:11434")
    print("-" * 40)
    
    setup_rag()
    
    ollama_thread = threading.Thread(target=start_ollama)
    ollama_thread.daemon = True
    ollama_thread.start()
    time.sleep(2)
    
    frontend_thread = threading.Thread(target=start_frontend)
    frontend_thread.daemon = True
    frontend_thread.start()
    
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver'])
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
