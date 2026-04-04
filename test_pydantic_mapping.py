
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class RespostaResponse(BaseModel):
    id: int
    mensagem: str
    data: datetime
    admin_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class OcorrenciaBase(BaseModel):
    titulo: str
    descricao: str
    rua: Optional[str] = None
    ponto_referencia: Optional[str] = None
    secretaria_id: Optional[int] = None

class OcorrenciaResponse(OcorrenciaBase):
    id: int
    protocolo: Optional[str] = None
    foto: Optional[str] = None
    video: Optional[str] = None
    foto_resolucao: Optional[str] = None
    status: str
    data: datetime
    usuario_id: Optional[int] = None
    secretaria_nome: Optional[str] = None
    respostas: List[RespostaResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Mock data from SQL
mock_data = {
    "id": 1,
    "titulo": "teste admin",
    "descricao": "teste",
    "foto": "uploads/efbaa599-3f16-4377-9b0f-d2086ffe421a.png",
    "video": None,
    "status": "pendente",
    "data": datetime.now(), # SQLAlchemy returns datetime objects
    "usuario_id": 3,
    "secretaria_id": None,
    "protocolo": None,
    "rua": None,
    "ponto_referencia": None,
    "foto_resolucao": None
}

class MockObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.respostas = []
        self.secretaria_nome = "Teste Sec"

try:
    obj = MockObj(**mock_data)
    resp = OcorrenciaResponse.model_validate(obj)
    print("Mapeamento bem sucedido!")
    print(resp.model_dump_json(indent=2))
except Exception as e:
    print(f"Erro no mapeamento: {e}")
