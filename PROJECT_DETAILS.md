# ltics - Business 
## 1. Project Overview
Solven Analytics is an
---

## 2. Technology Stack

### **Backend**
*   **Framework**: Django (Python) - The core web framework managing API requests and authentication.
*   **API**: Django REST Framework (DRF) - Exposes the `/api/chat/` endpoint for the frontend.
*   **Database**: PostgreSQL - Used for user management and chat history.
*   **Data Processing**:
    *   `pandas`: For ingesting and manipulating structured datasets (CSV, Excel).
    *   `openpyxl`: For Excel file support.

*   **Runner**: Ollama - A local server for running large language models.
*   **Generation Model**: `gemma3:1b` - A lightweight, high-performance LLM used for:
    *   Data Profiling & Schema Understanding
    *   KPI Generation & Prioritization
    *   Formula Engineering
    *   Chart Ideation & Selection
    *   Generating Business Insights & Recommendations

### **Frontend**
*   **Library**: React.js - Provides the chat interface for users to interact with the bot.

---

## 3. Project File Structure

```
P Square/
├── backend/
│   ├── api/
│   │   ├── models.py           # Defines DB models (User, etc.)
│   │   ├── ollama_service.py   # Service to communicate with Ollama
│   │   ├── rag.py              # Core logic for the 9-Phase Analytics Pipeline
│   │   └── views.py            # API endpoints (chat, auth)
│   │
│   ├── backend/                # Django project settings folder
│   │   └── settings.py
│   ├── manage.py               # Django management script
│   └── requirements.txt        # Python dependencies
│
├── frontend/
│   ├── node_modules/
│   ├── public/
│   ├── src/                    # React source code
│   └── package.json            # Frontend dependencies
│
└── PROJECT_DETAILS.md          # This documentation file
```

---

## 4. Project Workflow
The system executes a sequential 9-phase pipeline upon receiving a dataset:
*File: `backend/api/rag.py`*
1.  **Phase 1: Data Profiling**: Analyzes schema, types, and semantic meaning.
2.  **PPIo IpnslPas
| File Path | Description |

| `backend/api/rag.py` | **The Brain**. Contains the 9-phase analytics pipeline logic. |
| `backend/api/ollama_service.py` | **The Bridge**. Handles HTTP requests to the local Ollama instance (ports to `localhost:11434`). |
| `backend/api/models.py` | **The Data Structure**. Defines `Document` (for vectors), `Titanic` (for SQL data), and `User` models. |
| `backend/api/views.py` | **The Gatekeeper**. Handles API requests, authentication, and calls `rag_query`. |
| `backend/ingest_pdf.py` | **The Loader**. Script to process PDFs and populate the vector database. |
| `ingest_company_policy.bat` | **Automation**. Windows batch file to install dependencies and run the ingestion script. |

---


2.  **Pull Models**:
    ```bash
    ollama pull gemma3:1b
    ollama pull nomic-embed-text
    ```
3.  **Postgre
### **Setup**
1.  **Install Python Dependencies**:
    ```bash
    pip install django djangorestframework psycopg2-binary pgvector requests PyPDF2
    ```
2.  **Ingest Data**:
    Run the batch file to load your PDF data into the database.
    ```bash
    ingest_company_policy.bat
    ```

### **Running the Server**
1.  Navigate to the backend folder:
    ```bash
    cd backend
    ```
2.  Start Django:
    ```bash
    python manage.py runserver
    ```
3.  The API is now accessible at `http://127.0.0.1:8000/api/chat/`.