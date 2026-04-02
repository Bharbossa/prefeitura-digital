import sys
sys.path.append('.')
from backend.app.database import SessionLocal
from backend.app.models.schema import AdminSecretaria
from backend.app.core.security import get_password_hash

db = SessionLocal()
admin = db.query(AdminSecretaria).filter(AdminSecretaria.email == "allyson@leopoldina.gov.br").first()

if admin:
    admin.senha_hash = get_password_hash("123456")
    db.commit()
    print("Senha de allyson@leopoldina.gov.br resetada com sucesso para: 123456")
else:
    print("Administrador nao encontrado.")
