import os
import sys
from dotenv import load_dotenv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.database import SessionLocal
from app.routes.auth import read_users_me
from app.core.auth_deps import get_current_user
from app.models.schema import Usuario

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.email == 'admin@leopoldina.gov.br').first()
# mock tipo_usuario_verificado like auth_deps.py does
user.tipo_usuario_verificado = 'admin'

try:
    res = read_users_me(user)
    print("Function Result:", res)
    
    # Test Pydantic validation
    from app.models.pydantic_schemas import UsuarioResponse
    validated = UsuarioResponse(**res)
    print("Pydantic Validation Success:", validated)
except Exception as e:
    import traceback
    traceback.print_exc()
