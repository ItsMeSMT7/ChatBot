#!/usr/bin/env python
import subprocess #run npm and django command
import threading # run frontend + browser 
import time 
import webbrowser
import os
import sys

def start_frontend():
    """Start React frontend"""
    try:
        frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
        subprocess.run(['npm', 'start'], cwd=frontend_path, shell=True)
    except Exception as e:
        print(f'Frontend error: {e}')

def open_browser():
    """Open browser """
    time.sleep(4)
    webbrowser.open('http://localhost:3000')

if __name__ == '__main__':
    print("🚀 Starting Chatbot Application...")
    print("📱 Frontend: http://localhost:3000")
    print("🔧 Backend: http://localhost:8000")
    print("-" * 40)
    
    # Start frontend in background
    frontend_thread = threading.Thread(target=start_frontend)
    frontend_thread.daemon = True
    frontend_thread.start()
    
    # Open browser after delay
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Django server (blocking)
    try:
        subprocess.run([sys.executable, 'manage.py', 'runserver'])
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")