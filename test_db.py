import os
import sys

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from app.database import SessionLocal
from app.models.schema import Secretaria

def test():
    db = SessionLocal()
    try:
        secs = db.query(Secretaria).all()
        print(f"Found {len(secs)} secretarias")
        for s in secs:
            print(f"ID: {s.id}, Nome: {s.nome}")
            # Simulate the return logic
            res = {"id": str(s.id), "nome": s.nome}
            print(f"Serialized: {res}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test()
