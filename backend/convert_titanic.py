"""
Convert Titanic data to vector embeddings and store in PostgreSQL
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Titanic, Document
from api.embeddings import generate_embedding

def convert_titanic_to_text(passenger):
    """Convert Titanic passenger record to descriptive text"""
    age_str = f"{passenger.age} years old" if passenger.age else "unknown age"
    cabin_str = f"cabin {passenger.cabin}" if passenger.cabin else "no cabin info"
    
    text = (
        f"Passenger {passenger.name}, a {age_str} {passenger.sex} "
        f"traveling in class {passenger.pclass}. "
        f"{'Survived' if passenger.survived == 1 else 'Did not survive'} the Titanic. "
        f"Ticket: {passenger.ticket}, Fare: ${passenger.fare}, {cabin_str}, "
        f"embarked from {passenger.embarked or 'unknown port'}."
    )
    return text

def ingest_titanic_data():
    """Convert all Titanic records to embeddings and store"""
    
    print("Starting Titanic data conversion...")
    print(f"Total passengers: {Titanic.objects.count()}")
    
    # Clear existing Titanic documents
    Document.objects.filter(metadata__source='titanic').delete()
    
    passengers = Titanic.objects.all()
    total = passengers.count()
    
    for idx, passenger in enumerate(passengers, 1):
        # Convert to text
        text = convert_titanic_to_text(passenger)
        
        # Generate embedding
        embedding = generate_embedding(text)
        
        # Store in documents table
        Document.objects.create(
            content=text,
            embedding=embedding,
            metadata={
                'source': 'titanic',
                'passenger_id': passenger.passenger_id,
                'survived': passenger.survived,
                'pclass': passenger.pclass
            }
        )
        
        if idx % 10 == 0:
            print(f"Processed {idx}/{total} passengers...")
    
    print(f"\nCompleted! {total} Titanic records converted to vectors.")
    print("Data stored in 'documents' table in pgAdmin.")

if __name__ == "__main__":
    ingest_titanic_data()
