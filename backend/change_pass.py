import os
import sys

# Adiciona o diretório backend ao PYTHONPATH para poder importar os módulos do app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.security import get_password_hash
from app.database import SessionLocal
from app.models.schema import Usuario
from sqlalchemy import text

def reset_password(email: str, new_password: str):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if not user:
            print(f"Usuário com email {email} não encontrado.")
            return

        user.senha_hash = get_password_hash(new_password)
        db.commit()
        print(f"Senha de {email} alterada com sucesso.")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_password("bharbossa@gmail.com", "17130288")
