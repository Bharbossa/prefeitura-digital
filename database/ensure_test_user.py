import os
import sys
import bcrypt
from sqlalchemy.orm import Session

# Add the 'backend' directory to sys.path so we can import 'app'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import SessionLocal, engine
from backend.app.models.schema import Usuario, TipoUsuario

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def ensure_test_user():
    db: Session = SessionLocal()
    
    user_email = 'usuario@test.com'
    user_nome = 'Cidadão de Teste'
    user_cpf = '111.222.333-44'
    password = 'user123'
    
    print(f"Ensuring test user {user_email} exists and has the correct password...")
    
    try:
        # Check if user exists
        user = db.query(Usuario).filter(Usuario.email == user_email).first()
        
        new_hash = get_password_hash(password)
        
        if user:
            user.senha_hash = new_hash
            user.tipo_usuario = TipoUsuario.cidadao
            print(f"Updated existing user {user_email}")
        else:
            new_user = Usuario(
                nome=user_nome,
                cpf=user_cpf,
                email=user_email,
                senha_hash=new_hash,
                tipo_usuario=TipoUsuario.cidadao
            )
            db.add(new_user)
            print(f"Created new user {user_email}")
            
        db.commit()
        print(f"Success: Citizen user ready with password '{password}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ensure_test_user()
