import os
import sys
from dotenv import load_dotenv

# Add the 'backend' directory to sys.path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from app.database import engine, Base
import app.models.schema # Import the models so they are registered with Base

def init_db():
    db_url = os.environ.get('DATABASE_URL')
    print(f"Connecting to database at: {db_url}")
    
    if not db_url:
        print("Error: DATABASE_URL environment variable not set.")
        return

    print("Creating tables...")
    try:
        # Create all tables defined in the schema
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    init_db()
