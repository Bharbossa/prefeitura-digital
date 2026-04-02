import sys
import traceback
sys.path.append('.')

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.pydantic_schemas import OcorrenciaCreate
from backend.app.routes.ocorrencias import create_ocorrencia
from datetime import datetime
from types import SimpleNamespace

db = SessionLocal()

current_user = SimpleNamespace(
    id=17,
    tipo_usuario_verificado="cidadao"
)

try:
    res = create_ocorrencia(
        titulo="Buraco na rua",
        descricao="Teste automatizado",
        secretaria_id=15,
        foto=None,
        video=None,
        current_user=current_user,
        db_sql=db
    )
    from fastapi.encoders import jsonable_encoder
    # Pydantic validation simulation:
    from backend.app.models.pydantic_schemas import OcorrenciaResponse
    response = OcorrenciaResponse.model_validate(res)
    print("Success:", response)
except Exception as e:
    print("CRASH:", traceback.format_exc())
