from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from .schema import TipoUsuario, StatusOcorrencia, StatusUsuario

class UsuarioBase(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    telefone: Optional[str] = None
    endereco: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class UsuarioResponse(UsuarioBase):
    id: str
    tipo_usuario: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    type: Optional[str] = None

class OcorrenciaBase(BaseModel):
    titulo: str
    descricao: str
    secretaria_id: str

class OcorrenciaCreate(OcorrenciaBase):
    pass # foto and video are handled via Form data in endpoints

class RespostaResponse(BaseModel):
    id: str
    mensagem: str
    data: datetime
    admin_id: str
    model_config = ConfigDict(from_attributes=True)

class OcorrenciaResponse(OcorrenciaBase):
    id: str
    foto: Optional[str] = None
    video: Optional[str] = None
    status: str
    data: datetime
    usuario_id: str
    respostas: List[RespostaResponse] = []
    model_config = ConfigDict(from_attributes=True)

class ChatIARequest(BaseModel):
    mensagem: str

class ChatIAResponse(BaseModel):
    resposta: str
