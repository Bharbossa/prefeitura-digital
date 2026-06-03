import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.database import SessionLocal
from app.models.schema import AdminSecretaria, Usuario, TipoUsuario

db = SessionLocal()

print("Sub-Administrators:")
subadmins = db.query(AdminSecretaria).all()
for sa in subadmins:
    print(f"ID: {sa.id}, Nome: {sa.nome}, Secretaria_ID: {sa.secretaria_id}, Telefone: {sa.telefone}")

print("\nGeneral Administrators:")
global_admins = db.query(Usuario).filter(Usuario.tipo_usuario == TipoUsuario.admin).all()
for ga in global_admins:
    print(f"ID: {ga.id}, Nome: {ga.nome}, Telefone: {ga.telefone}, WhatsApp: {ga.whatsapp}")
