@echo off
echo ========================================
echo RAG Pipeline Setup
echo ========================================
echo.

cd backend

echo Step 1: Creating migrations...
python manage.py makemigrations
echo.

echo Step 2: Applying migrations...
python manage.py migrate
echo.

echo Step 3: Enabling pgvector extension...
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); import django; django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;'); print('✓ pgvector extension enabled')"
echo.

echo Step 4: Ingesting sample data...
python ingest_data.py
echo.

echo ========================================
echo RAG Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure Ollama is running: ollama serve
echo 2. Start backend: python manage.py runserver
echo 3. Start frontend: cd ../frontend ^&^& npm start
echo.
pause
