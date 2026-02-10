"""
Step-2B Verification Script
Checks if Document model with pgvector is properly configured
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from api.models import Document

print("=" * 50)
print("Step-2B Verification")
print("=" * 50)

# Check 1: pgvector extension
print("\n[1] Checking pgvector extension...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        result = cursor.fetchone()
        if result:
            print("✅ pgvector extension is enabled")
        else:
            print("❌ pgvector extension NOT found")
            print("   Run: CREATE EXTENSION vector; in PostgreSQL")
except Exception as e:
    print(f"❌ Error checking extension: {e}")

# Check 2: Document model
print("\n[2] Checking Document model...")
try:
    from api.models import Document
    print("✅ Document model imported successfully")
    print(f"   - content field: {Document._meta.get_field('content')}")
    print(f"   - embedding field: {Document._meta.get_field('embedding')}")
    print(f"   - metadata field: {Document._meta.get_field('metadata')}")
except Exception as e:
    print(f"❌ Error with Document model: {e}")

# Check 3: Documents table exists
print("\n[3] Checking documents table...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM documents;")
        count = cursor.fetchone()[0]
        print(f"✅ documents table exists with {count} records")
except Exception as e:
    print(f"❌ documents table NOT found: {e}")
    print("   Run: python manage.py migrate")

# Check 4: Test vector operations
print("\n[4] Testing vector operations...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT '[1,2,3]'::vector;")
        print("✅ Vector operations working")
except Exception as e:
    print(f"❌ Vector operations failed: {e}")

print("\n" + "=" * 50)
print("Step-2B Status:")
print("=" * 50)

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        ext_ok = cursor.fetchone() is not None
        
        cursor.execute("SELECT COUNT(*) FROM documents;")
        table_ok = True
        
    if ext_ok and table_ok:
        print("✅ Step-2B COMPLETED - Ready for Step-3")
        print("\nNext: Run 'python ingest_data.py' to load documents")
    else:
        print("❌ Step-2B INCOMPLETE")
        if not ext_ok:
            print("   - Enable pgvector extension")
        if not table_ok:
            print("   - Run migrations")
except Exception as e:
    print(f"❌ Step-2B INCOMPLETE: {e}")
    print("\nRun: python manage.py migrate")

print("=" * 50)
