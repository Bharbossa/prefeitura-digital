import sys
sys.path.append('.')
from backend.app.database import engine
from sqlalchemy import text

def add_columns():
    with engine.begin() as conn:
        print("Migrating ocorrencias table...")
        
        # Add protocolo
        conn.execute(text("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS protocolo VARCHAR(20);"))
        
        # Add foto
        conn.execute(text("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS foto VARCHAR(255);"))
        
        # Add video
        conn.execute(text("ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS video VARCHAR(255);"))
        
        print("Success! Ocorrencia Columns have been ensured.")

if __name__ == "__main__":
    add_columns()
