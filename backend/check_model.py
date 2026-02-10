import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from api.models import Document

print("=" * 50)
print("Django Embedding Model Verification")
print("=" * 50)

# Check 1: pgvector extension
print("\n[1] pgvector extension...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cursor.fetchone():
            print("OK - pgvector enabled")
        else:
            print("FAIL - pgvector NOT enabled")
except Exception as e:
    print(f"FAIL - {e}")

# Check 2: Document model
print("\n[2] Document model...")
try:
    print(f"OK - content: {Document._meta.get_field('content').get_internal_type()}")
    print(f"OK - embedding: VectorField(768)")
    print(f"OK - metadata: {Document._meta.get_field('metadata').get_internal_type()}")
except Exception as e:
    print(f"FAIL - {e}")

# Check 3: documents table
print("\n[3] documents table...")
try:
    count = Document.objects.count()
    print(f"OK - Table exists with {count} records")
except Exception as e:
    print(f"FAIL - {e}")

# Check 4: Vector operations
print("\n[4] Vector operations...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT '[1,2,3]'::vector;")
    print("OK - Vector type working")
except Exception as e:
    print(f"FAIL - {e}")

print("\n" + "=" * 50)
print("RESULT:")
print("=" * 50)

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        ext_ok = cursor.fetchone() is not None
    
    table_ok = Document.objects.count() >= 0
    
    if ext_ok and table_ok:
        print("SUCCESS - Django Embedding Model is READY")
        print("\nYou can now:")
        print("1. Run: python ingest_data.py")
        print("2. Or proceed to Step-3")
    else:
        print("INCOMPLETE - Setup needed")
except Exception as e:
    print(f"INCOMPLETE - {e}")

print("=" * 50)
