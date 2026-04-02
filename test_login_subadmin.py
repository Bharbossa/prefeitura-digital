import sys
sys.path.append('.')
from backend.app.database import SessionLocal
from backend.app.models.schema import AdminSecretaria

db = SessionLocal()
admin = db.query(AdminSecretaria).filter(AdminSecretaria.email == "allyson@leopoldina.gov.br").first()

if admin:
    print("Encontrado:", admin.email)
    print("ID:", admin.id)
    print("Status:", admin.status if hasattr(admin, 'status') else 'No status field')
    print("Senha hash (inicio):", admin.senha_hash[:15])
else:
    print("Sub-administrador allyson@leopoldina.gov.br NAO ENCONTRADO no banco de dados!")
