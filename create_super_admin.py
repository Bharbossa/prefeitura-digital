
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.schema import Usuario, TipoUsuario, StatusUsuario
from backend.app.core.security import get_password_hash

def create_super_admin():
    db = SessionLocal()
    try:
        email = "super@teste.com"
        exists = db.query(Usuario).filter(Usuario.email == email).first()
        if exists:
            db.delete(exists)
            db.commit()
            
        hashed_password = get_password_hash("123")
        admin = Usuario(
            nome="Super Administrador Teste",
            cpf="999.999.999-99",
            email=email,
            senha_hash=hashed_password,
            tipo_usuario=TipoUsuario.admin,
            status=StatusUsuario.ativo
        )
        db.add(admin)
        db.commit()
        print(f"Super Admin {email} criado com sucesso!")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
