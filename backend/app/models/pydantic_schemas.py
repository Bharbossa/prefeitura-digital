from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from .schema import TipoUsuario, StatusOcorrencia, StatusUsuario

class UsuarioBase(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    telefone: Optional[str] = None
    whatsapp: Optional[str] = None
    endereco: Optional[str] = None
    foto_perfil: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class UsuarioResponse(UsuarioBase):
    id: int # Postgres uses integers by default in our model
    tipo_usuario: str
    status: str
    secretaria_id: Optional[int] = None
    secretaria_nome: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    type: Optional[str] = None

class OcorrenciaBase(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    rua: Optional[str] = None
    ponto_referencia: Optional[str] = None
    secretaria_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class OcorrenciaCreate(OcorrenciaBase):
    pass # foto and video are handled via Form data in endpoints

class RespostaResponse(BaseModel):
    id: int
    mensagem: str
    data: datetime
    admin_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class OcorrenciaResponse(OcorrenciaBase):
    id: Optional[int] = None
    protocolo: Optional[str] = None
    foto: Optional[str] = None
    video: Optional[str] = None
    documento: Optional[str] = None
    foto_resolucao: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    data: Optional[datetime] = None
    usuario_id: Optional[int] = None
    usuario_nome: Optional[str] = None
    secretaria_nome: Optional[str] = None
    respostas: Optional[List[RespostaResponse]] = []
    model_config = ConfigDict(from_attributes=True)

class LogAuditoriaBase(BaseModel):
    usuario_id: int
    usuario_tipo: str
    acao: str
    detalhes: str

class LogAuditoriaResponse(LogAuditoriaBase):
    id: int
    data: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatIARequest(BaseModel):
    mensagem: str

class ChatIAResponse(BaseModel):
    resposta: str

class AdminSecretariaCreate(BaseModel):
    nome: str
    cpf: str
    email: EmailStr
    telefone: Optional[str] = None
    senha: str
    secretaria_id: int

class AdminSecretariaResponse(BaseModel):
    id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    secretaria_id: int
    status: str = "Ativo"
    tipo_usuario: str = "subadmin"
    foto_perfil: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)



class AgendamentoBase(BaseModel):
    secretaria_id: int
    tipo: str
    assunto: str
    motivo: Optional[str] = None
    acompanhante: Optional[str] = None
    cartao_sus: Optional[str] = None
    data_hora: datetime

class AgendamentoCreate(AgendamentoBase):
    pass

class AgendamentoResponse(AgendamentoBase):
    id: int
    protocolo: Optional[str] = None
    senha: Optional[str] = None
    usuario_id: int
    usuario_nome: Optional[str] = None
    usuario_endereco: Optional[str] = None
    status: str
    anexo: Optional[str] = None
    cartao_sus: Optional[str] = None
    criado_em: datetime
    model_config = ConfigDict(from_attributes=True)
class AdminPasswordUpdate(BaseModel):
    user_id: int
    source: str # 'usuario' or 'subadmin'
    new_password: str

class ForgotPasswordRequest(BaseModel):
    identifier: str
    method: str # 'email' or 'sms'

class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str

class UpdateNameRequest(BaseModel):
    nome: str

class AvisoBase(BaseModel):
    titulo: str
    mensagem: str
    tipo: str = "info"

class AvisoCreate(AvisoBase):
    pass

class AvisoResponse(AvisoBase):
    id: int
    ativo: int
    data_criacao: datetime
    autor_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)
