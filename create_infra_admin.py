
import sys
import os

# Adiciona o diretório backend ao path para importar os modelos
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import SessionLocal
from app.models.schema import AdminSecretaria
from app.core.security import get_password_hash

def create_sub_admin():
    db = SessionLocal()
    try:
        nome = "Teste Infraestrutura"
        email = "infra@teste.com"
        senha = "123"
        secretaria_id = 19
        
        # Verifica se já existe
        exists = db.query(AdminSecretaria).filter(AdminSecretaria.email == email).first()
        if exists:
            # Update password if exists
            exists.senha_hash = get_password_hash(senha)
            exists.secretaria_id = secretaria_id
            print(f"Usuário {email} já existia. Senha e secretaria atualizadas.")
        else:
            new_admin = AdminSecretaria(
                nome=nome,
                email=email,
                senha_hash=get_password_hash(senha),
                secretaria_id=secretaria_id
            )
            db.add(new_admin)
            print(f"Sub-administrador {email} criado com sucesso!")
        
        db.commit()
    except Exception as e:
        print(f"Erro ao criar sub-admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sub_admin()
