#!/usr/bin/env python
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

def check_titanic_table():
    """Check if titanic table exists and has data"""
    try:
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'titanic'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if table_exists:
                print("Titanic table exists")
                
                # Check row count
                cursor.execute("SELECT COUNT(*) FROM titanic")
                count = cursor.fetchone()[0]
                print(f"Titanic table has {count} records")
                
                if count > 0:
                    # Show sample data
                    cursor.execute("SELECT * FROM titanic LIMIT 3")
                    rows = cursor.fetchall()
                    print("Sample data:")
                    for row in rows:
                        print(f"  {row}")
                else:
                    print("Titanic table is empty")
            else:
                print("Titanic table does not exist")
                
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    check_titanic_table()