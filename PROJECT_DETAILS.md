# P Square - Intelligent Hybrid RAG Chatbot

## 1. Project Overview
This project is an intelligent chatbot system that uses a **Hybrid RAG (Retrieval-Augmented Generation)** approach. It can dynamically switch between querying structured data (SQL database) and unstructured data (PDF documents) based on the user's question. It runs entirely locally using **Ollama** for AI processing, ensuring data privacy and zero API costs.

---

## 2. Technology Stack

### **Backend**
*   **Framework**: Django (Python) - The core web framework managing requests, database interactions, and authentication.
*   **API**: Django REST Framework (DRF) - Exposes the `/api/chat/` endpoint for the frontend.
*   **Database**: PostgreSQL - The primary relational database.
    *   **Extension**: `pgvector` - Enables vector similarity search directly within PostgreSQL.
*   **PDF Processing**: `PyPDF2` - Used to extract text from PDF documents during ingestion.

### **AI & LLM (Local)**
*   **Runner**: Ollama - A local server for running large language models.
*   **Generation Model**: `gemma3:1b` - A lightweight, high-performance LLM used for:
    *   Classifying user questions.
    *   Generating SQL queries.
    *   Synthesizing natural language answers from retrieved context.
*   **Embedding Model**: `nomic-embed-text` - Converts text into 768-dimensional vectors for semantic search.

### **Frontend**
*   **Library**: React.js - Provides the chat interface for users to interact with the bot.

---

## 3. Project File Structure

```
P Square/
├── backend/
│   ├── api/
│   │   ├── models.py           # Defines DB models (Document, Titanic, User)
│   │   ├── ollama_service.py   # Service to communicate with Ollama
│   │   ├── rag.py              # Core logic for Hybrid RAG
│   │   └── views.py            # API endpoints (chat, auth)
│   │
│   ├── backend/                # Django project settings folder
│   │   └── settings.py
│   │
│   ├── company_policy.pdf      # PDF for knowledge base
│   ├── ingest_pdf.py           # Script to process and embed the PDF
│   ├── manage.py               # Django management script
│   └── requirements.txt        # Python dependencies
│
├── frontend/
│   ├── node_modules/
│   ├── public/
│   ├── src/                    # React source code
│   └── package.json            # Frontend dependencies
│
├── ingest_company_policy.bat   # Script to run PDF ingestion
└── PROJECT_DETAILS.md          # This documentation file
```

---

## 4. Project Workflow

The system operates in two main phases: **Data Ingestion** (Setup) and **Query Processing** (Runtime).

### **Phase A: Data Ingestion (Offline)**
*File: `backend/ingest_pdf.py`*

1.  **Read PDF**: The script reads `company_policy.pdf`.
2.  **Chunking**: The text is split into smaller, overlapping chunks (e.g., 500 characters).
3.  **Embedding**: Each chunk is sent to Ollama (`nomic-embed-text`) to generate a vector representation.
4.  **Storage**: The text chunk and its vector are saved to the `documents` table in PostgreSQL.

### **Phase B: Query Processing (Runtime)**
*File: `backend/api/rag.py`*

When a user sends a message, the following pipeline executes:

1.  **Classification**:
    *   The LLM analyzes the question to determine its intent.
    *   **Categories**:
        *   `database`: Questions about Titanic passengers (structured data).
        *   `knowledge`: Questions about Company Policy (unstructured PDF data).
        *   `conversational`: Greetings or follow-ups.
        *   `irrelevant`: Off-topic queries.

2.  **Routing**:
    *   **If `database`**:
        1.  The LLM acts as a SQL Expert. It receives the table schema and generates a raw SQL query (e.g., `SELECT COUNT(*) FROM titanic...`).
        2.  The system sanitizes the query (removes markdown, checks for dangerous keywords like `DROP`).
        3.  The query executes against the PostgreSQL `titanic` table.
        4.  Raw results are returned to the user.
    *   **If `knowledge`**:
        1.  The user's question is converted into a vector embedding.
        2.  **Vector Search**: The system queries the `documents` table using Cosine Similarity (`<=>`) to find the top 5 most relevant text chunks.
        3.  **Augmentation**: The retrieved text chunks are combined into a "Context".
        4.  **Generation**: The LLM receives the Context + Question and generates a final natural language answer.
    *   **If `conversational`**:
        *   Returns a polite message explaining that the bot processes questions independently (stateless).

---

## 5. Key Files & Details

| File Path | Description |
| :--- | :--- |
| `backend/api/rag.py` | **The Brain**. Contains the main logic for classification, SQL generation, and RAG retrieval. |
| `backend/api/ollama_service.py` | **The Bridge**. Handles HTTP requests to the local Ollama instance (ports to `localhost:11434`). |
| `backend/api/models.py` | **The Data Structure**. Defines `Document` (for vectors), `Titanic` (for SQL data), and `User` models. |
| `backend/api/views.py` | **The Gatekeeper**. Handles API requests, authentication, and calls `rag_query`. |
| `backend/ingest_pdf.py` | **The Loader**. Script to process PDFs and populate the vector database. |
| `ingest_company_policy.bat` | **Automation**. Windows batch file to install dependencies and run the ingestion script. |

---

## 6. Database Schema Details

### **1. Titanic Table (Structured)**
Used for SQL generation queries.
*   `survived`: Integer (0/1)
*   `pclass`: Integer (1/2/3)
*   `sex`: Text (male/female)
*   `age`: Float
*   `fare`: Float
*   `embarked`: Text (C/Q/S)

### **2. Documents Table (Unstructured)**
Used for Vector Search.
*   `content`: Text (The actual text chunk from the PDF).
*   `embedding`: Vector(768) (The mathematical representation of the text).
*   `metadata`: JSON (Source filename, chunk ID).

---

## 7. How to Use

### **Prerequisites**
1.  **Install Ollama**: Download from ollama.com.
2.  **Pull Models**:
    ```bash
    ollama pull gemma3:1b
    ollama pull nomic-embed-text
    ```
3.  **PostgreSQL**: Ensure PostgreSQL is installed with the `pgvector` extension enabled.

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