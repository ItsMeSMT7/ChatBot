#!/usr/bin/env python
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import StateData, Titanic
from django.db import connection

def test_database_connection():
    """Test database connection and data"""
    print("Testing database connection...")
    
    try:
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✓ Database connection successful")
        
        # Test StateData
        state_count = StateData.objects.count()
        print(f"✓ StateData table: {state_count} records")
        
        if state_count > 0:
            sample_state = StateData.objects.first()
            print(f"  Sample: {sample_state.state} - Population: {sample_state.population}")
        
        # Test Titanic
        titanic_count = Titanic.objects.count()
        print(f"✓ Titanic table: {titanic_count} records")
        
        print("\n✓ All database tests passed!")
        
    except Exception as e:
        print(f"✗ Database error: {e}")

if __name__ == "__main__":
    test_database_connection()