import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.models.schema import Usuario, TipoUsuario, StatusUsuario
from app.core.security import get_password_hash

def setup_test_users():
    db = SessionLocal()
    try:
        # 1. Setup Admin
        admin_email = 'admin@leopoldina.gov.br'
        admin = db.query(Usuario).filter(Usuario.email == admin_email).first()
        admin_pass = get_password_hash('admin123')
        
        if not admin:
            print("Creating new admin user...")
            admin = Usuario(
                nome='Administrador Geral',
                cpf='000.000.000-00',
                email=admin_email,
                senha_hash=admin_pass,
                tipo_usuario=TipoUsuario.admin,
                status=StatusUsuario.ativo
            )
            db.add(admin)
        else:
            print("Updating existing admin user password...")
            admin.senha_hash = admin_pass
            admin.status = StatusUsuario.ativo
            admin.tipo_usuario = TipoUsuario.admin
        
        # 2. Setup Pending User
        pend_email = 'novo_usuario@leopoldina.gov.br'
        pend_user = db.query(Usuario).filter(Usuario.email == pend_email).first()
        pend_pass = get_password_hash('senha123')
        
        if not pend_user:
            print("Creating pending user...")
            pend_user = Usuario(
                nome='Cidadão Teste Pendente',
                cpf='111.111.111-11',
                email=pend_email,
                senha_hash=pend_pass,
                tipo_usuario=TipoUsuario.cidadao,
                status=StatusUsuario.pendente
            )
            db.add(pend_user)
        else:
            print("Resetting pending user status...")
            pend_user.status = StatusUsuario.pendente
            pend_user.senha_hash = pend_pass
            
        db.commit()
        print("Test users ready!")
        print(f"Admin: {admin_email} / admin123")
        print(f"Pending: {pend_email} / senha123")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_users()
