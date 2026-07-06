import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

def add_genero_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS genero VARCHAR(50)"))
            conn.commit()
            print("Coluna genero adicionada (ou já existe).")
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    add_genero_column()
