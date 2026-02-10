# How to Run RAG Application

## First Time Setup (Run Once)

1. **Setup RAG Pipeline:**
   ```
   Double-click: setup_rag.bat
   ```
   This will:
   - Create database tables
   - Enable pgvector
   - Load sample documents

## Every Time You Want to Use the App

2. **Start Everything:**
   ```
   Double-click: start_all.bat
   ```
   
   Three windows will open:
   - Ollama Server
   - Django Backend
   - React Frontend

3. **Open Browser:**
   ```
   http://localhost:3000
   ```

4. **Stop Everything:**
   - Press any key in the main window
   - OR close all three windows

---

## Manual Start (Alternative)

If `start_all.bat` doesn't work:

**Terminal 1:**
```
ollama serve
```

**Terminal 2:**
```
cd backend
python manage.py runserver
```

**Terminal 3:**
```
cd frontend
npm start
```

---

## Troubleshooting

**"Ollama not found"**
- Install: https://ollama.ai/download
- Pull model: `ollama pull gemma:1b`

**"Port already in use"**
- Close existing processes
- Or change ports in settings

**"No documents found"**
- Run: `setup_rag.bat` first
