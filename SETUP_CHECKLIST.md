# ✅ RAG System Setup Checklist

## 📋 Follow These Steps in Order

### ☐ Step 1: Prerequisites
- [ ] PostgreSQL installed and running
- [ ] Ollama installed (download from https://ollama.ai)
- [ ] Python 3.x installed
- [ ] Node.js installed
- [ ] company_policy.pdf in backend/ folder

### ☐ Step 2: Install Ollama Model
```bash
ollama pull gemma:1b
```
- [ ] Model downloaded successfully

### ☐ Step 3: Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```
- [ ] All packages installed (including PyPDF2)

### ☐ Step 4: Verify System
```bash
cd backend
python verify_rag_setup.py
```
- [ ] Ollama check passed
- [ ] PDF file found
- [ ] Dependencies check passed

### ☐ Step 5: Start Ollama Server
```bash
ollama serve
```
- [ ] Ollama running on http://localhost:11434
- [ ] Keep this terminal open

### ☐ Step 6: Ingest PDF (One-time)
```bash
# From root directory
ingest_company_policy.bat

# OR manually
cd backend
python ingest_pdf.py
```
- [ ] PDF text extracted
- [ ] Chunks created
- [ ] Embeddings generated
- [ ] Stored in database

### ☐ Step 7: Verify Documents in Database
```bash
cd backend
python manage.py shell
```
```python
from api.models import Document
print(f"Total documents: {Document.objects.count()}")
# Should show number > 0
```
- [ ] Documents count > 0

### ☐ Step 8: Start Backend Server
```bash
cd backend
python manage.py runserver
```
- [ ] Backend running on http://localhost:8000
- [ ] Keep this terminal open

### ☐ Step 9: Start Frontend Server
```bash
cd frontend
npm start
```
- [ ] Frontend running on http://localhost:3000
- [ ] Browser opens automatically

### ☐ Step 10: Test the System
1. [ ] Open http://localhost:3000
2. [ ] Login or Signup
3. [ ] Ask: "What is the vacation policy?"
4. [ ] Receive answer from PDF content
5. [ ] Try more questions about company policy

---

## 🎯 Quick Test Questions

Once everything is running, try these:

- [ ] "What is the vacation policy?"
- [ ] "How many sick days do I get?"
- [ ] "What are the working hours?"
- [ ] "Tell me about remote work"

---

## ✅ Success Indicators

You'll know it's working when:
- ✅ No error messages in any terminal
- ✅ Questions get answered with content from PDF
- ✅ Answers are relevant and accurate
- ✅ Response time is 3-6 seconds

---

## 🐛 If Something Goes Wrong

### Ollama not running
```bash
# Start it
ollama serve
```

### No documents in database
```bash
# Re-run ingestion
cd backend
python ingest_pdf.py
```

### Port already in use
```bash
# Kill existing processes
# Windows: taskkill /F /IM python.exe
# Then restart servers
```

### PyPDF2 error
```bash
pip install PyPDF2==3.0.1
```

---

## 📊 System Health Check

Run this anytime to check system status:
```bash
cd backend
python verify_rag_setup.py
```

Should show:
```
✓ Ollama is running
✓ company_policy.pdf found
✓ Database has X document chunks
✓ PyPDF2 installed
✓ ALL CHECKS PASSED - System Ready!
```

---

## 🎉 You're Done!

When all checkboxes are ✅, your RAG system is fully operational!

**What you can do now:**
- Ask questions about company_policy.pdf
- Get AI-powered answers
- All processing happens locally
- Complete privacy

**To use daily:**
1. Start Ollama: `ollama serve`
2. Start Backend: `cd backend && python manage.py runserver`
3. Start Frontend: `cd frontend && npm start`
4. Chat at http://localhost:3000

---

**Need help?** Check:
- RAG_SETUP_GUIDE.md (detailed guide)
- RAG_QUICK_START.md (quick reference)
- RAG_ARCHITECTURE.md (technical details)
- CHANGES_SUMMARY.md (what was changed)
