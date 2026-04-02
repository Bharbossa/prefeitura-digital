import sys
import traceback
sys.path.append('.')

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.pydantic_schemas import AgendamentoCreate
from backend.app.routes.agendamentos import criar_agendamento
from datetime import datetime
from types import SimpleNamespace

# Create a local db session
db = SessionLocal()

agend = AgendamentoCreate(
    secretaria_id=15,
    tipo="Consulta Presencial",
    assunto="[POSTO CENTRO (PSF 02)] queda de moto",
    motivo=None,
    acompanhante=None,
    data_hora=datetime.fromisoformat("2026-03-31T12:40:00.000Z"),
    cartao_sus="54846174561248941564"
)

current_user = SimpleNamespace(
    id=1,
    tipo_usuario_verificado="cidadao"
)

try:
    res = criar_agendamento(agend, current_user, db)
    print("Success:", res)
except Exception as e:
    print("CRASH:", traceback.format_exc())
