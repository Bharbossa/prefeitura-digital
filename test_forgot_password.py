import asyncio
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from database import SessionLocal
from app.models.schema import Usuario
from sqlalchemy import func
from app.models.pydantic_schemas import ForgotPasswordRequest
from app.routes.auth import forgot_password

def test_password_recovery():
    db = SessionLocal()
    try:
        # Pega um usuário de teste
        user = db.query(Usuario).first()
        if not user:
            print("Nenhum usuário encontrado no banco para testar.")
            return

        print(f"Testando recuperação para E-mail: {user.email}")
        req_email = ForgotPasswordRequest(identifier=user.email, method="email")
        res_email = forgot_password(req_email, db)
        print("Resposta E-mail:", res_email)
        
        if user.telefone:
            print(f"Testando recuperação para SMS: {user.telefone}")
            req_sms = ForgotPasswordRequest(identifier=user.email, method="sms")
            res_sms = forgot_password(req_sms, db)
            print("Resposta SMS:", res_sms)
        else:
            print("Usuário não possui telefone, testando com número fictício falharia ou exigiria update." )

    except Exception as e:
        print("Erro durante o teste:", e)
    finally:
        db.close()

if __name__ == "__main__":
    test_password_recovery()
