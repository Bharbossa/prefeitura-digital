import sys
import traceback
sys.path.append('.')

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.schema import AdminSecretaria
from backend.app.routes.admin_users import delete_secretaria_admin
from types import SimpleNamespace

db = SessionLocal()

# Mock current admin
current_admin = SimpleNamespace(
    id=1,
    tipo_usuario_verificado="admin",
    tipo_admin="geral"
)

try:
    # Get the first sub-admin to try and delete
    subadmin = db.query(AdminSecretaria).first()
    if subadmin:
        print(f"Tentando excluir subadmin ID {subadmin.id} ({subadmin.email})")
        res = delete_secretaria_admin(
            admin_id=subadmin.id,
            current_admin=current_admin,
            db_sql=db
        )
        print("Success:", res)
    else:
        print("Nenhum subadmin encontrado no banco de dados para testar.")
except Exception as e:
    print("CRASH:", traceback.format_exc())
