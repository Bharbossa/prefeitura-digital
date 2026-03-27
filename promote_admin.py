import sys
import os

# Adiciona o diretório atual ao path para importar os módulos
sys.path.append(os.getcwd())

from backend.app.database import SessionLocal
from backend.app.models.schema import Usuario, TipoUsuario, StatusUsuario

def promote_user(email):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if not user:
            print(f"Erro: Usuário com email {email} não encontrado no banco de dados SQL.")
            return

        user.tipo_usuario = TipoUsuario.admin
        user.status = StatusUsuario.ativo
        db.commit()
        print(f"Sucesso: Usuário {email} agora é um ADMINISTRADOR GERAL.")
    except Exception as e:
        print(f"Erro ao promover usuário: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python promote_admin.py <email>")
    else:
        promote_user(sys.argv[1])
