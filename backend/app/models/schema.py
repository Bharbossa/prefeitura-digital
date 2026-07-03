from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum, Float, LargeBinary
from sqlalchemy.orm import relationship
import enum
import datetime
from ..database import Base
from ..core.utils import get_brasilia_time

class TipoUsuario(str, enum.Enum):
    cidadao = "cidadao"
    subadmin = "subadmin"
    admin = "admin"

class StatusOcorrencia(str, enum.Enum):
    pendente = "pendente"
    em_atendimento = "em_atendimento"
    resolvido = "resolvido"
    cancelado = "cancelado"

class StatusUsuario(str, enum.Enum):
    pendente = "pendente"
    ativo = "ativo"
    rejeitado = "rejeitado"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    cpf = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    telefone = Column(String(20), nullable=False)
    whatsapp = Column(String(20), nullable=False)
    endereco = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    tipo_usuario = Column(Enum(TipoUsuario), default=TipoUsuario.cidadao)
    status = Column(Enum(StatusUsuario), default=StatusUsuario.ativo)
    last_login = Column(DateTime, nullable=True)
    foto_perfil = Column(Text, nullable=True)

    ocorrencias = relationship("Ocorrencia", back_populates="usuario")
    agendamentos = relationship("Agendamento", back_populates="usuario")

class Secretaria(Base):
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), unique=True, nullable=False)

    admins = relationship("AdminSecretaria", back_populates="secretaria")
    ocorrencias = relationship("Ocorrencia", back_populates="secretaria")
    agendamentos = relationship("Agendamento", back_populates="secretaria")

class AdminSecretaria(Base):
    __tablename__ = "admins_secretaria"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    cpf = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    telefone = Column(String(20))
    endereco = Column(String(255))
    senha_hash = Column(String(255), nullable=False)
    secretaria_id = Column(Integer, ForeignKey("secretarias.id"))
    tipo_usuario = Column(String(50), default="subadmin") # Helper to distinguish in auth
    foto_perfil = Column(Text, nullable=True)

    secretaria = relationship("Secretaria", back_populates="admins")
    respostas = relationship("Resposta", back_populates="admin")

class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(20), unique=True, index=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=False)
    foto = Column(String(255), nullable=True)   # Path/URL
    video = Column(String(255), nullable=True)  # Path/URL
    documento = Column(String(255), nullable=True) # Path/URL for PDF
    rua = Column(String(255), nullable=True)
    ponto_referencia = Column(String(255), nullable=True)
    foto_resolucao = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(Enum(StatusOcorrencia), default=StatusOcorrencia.pendente)
    data = Column(DateTime, default=get_brasilia_time)
    avaliacao_nota = Column(Integer, nullable=True)
    avaliacao_comentario = Column(Text, nullable=True)
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    secretaria_id = Column(Integer, ForeignKey("secretarias.id"))

    usuario = relationship("Usuario", back_populates="ocorrencias")
    secretaria = relationship("Secretaria", back_populates="ocorrencias")
    respostas = relationship("Resposta", back_populates="ocorrencia")

class Resposta(Base):
    __tablename__ = "respostas"

    id = Column(Integer, primary_key=True, index=True)
    mensagem = Column(Text, nullable=False)
    data = Column(DateTime, default=get_brasilia_time)

    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    admin_id = Column(Integer, ForeignKey("admins_secretaria.id"))

    ocorrencia = relationship("Ocorrencia", back_populates="respostas")
    admin = relationship("AdminSecretaria", back_populates="respostas")

class ChatIA(Base):
    __tablename__ = "chat_ia"

    id = Column(Integer, primary_key=True, index=True)
    mensagem_usuario = Column(Text, nullable=False)
    resposta_ia = Column(Text, nullable=False)
    data = Column(DateTime, default=get_brasilia_time)
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # Optional link to user if logged in

    usuario = relationship("Usuario")

class Agendamento(Base):
    __tablename__ = "agendamentos"

    id = Column(Integer, primary_key=True, index=True)
    protocolo = Column(String(20), unique=True, index=True)
    senha = Column(String(10), nullable=True) # "Senha" de atendimento (ex: 1024)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    secretaria_id = Column(Integer, ForeignKey("secretarias.id"))
    tipo = Column(String(50)) # "Online" ou "Presencial"
    assunto = Column(String(200)) # Ex: "Consulta Médica"
    motivo = Column(Text, nullable=True) # Descrição detalhada do motivo
    acompanhante = Column(String(100), nullable=True) # Nome do acompanhante (Viagem)
    cartao_sus = Column(String(50), nullable=True)
    data_hora = Column(DateTime)
    status = Column(String(50), default="Pendente") # Pendente, Confirmado, Cancelado
    anexo = Column(Text, nullable=True) # Path/URL for the uploaded proof
    criado_em = Column(DateTime, default=get_brasilia_time)
    avaliacao_nota = Column(Integer, nullable=True)
    avaliacao_comentario = Column(Text, nullable=True)

    usuario = relationship("Usuario", back_populates="agendamentos")
    secretaria = relationship("Secretaria", back_populates="agendamentos")

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False) # ID of admin/subadmin
    usuario_tipo = Column(String(50)) # "admin" or "subadmin"

class LogRecuperacaoSenha(Base):
    __tablename__ = "logs_recuperacao_senha"

    id = Column(Integer, primary_key=True, index=True)
    usuario_nome = Column(String(150), nullable=False)
    usuario_tipo = Column(String(50), nullable=False) # cidadao, subadmin
    metodo = Column(String(50), nullable=False) # sms, email
    sucesso = Column(Integer, default=0) # 1=sucesso, 0=falha
    data_solicitacao = Column(DateTime, default=get_brasilia_time)

    acao = Column(String(100)) # "create_user", "update_status", etc.
    detalhes = Column(Text)
    data = Column(DateTime, default=get_brasilia_time)

class Aviso(Base):
    __tablename__ = "avisos"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    tipo = Column(String(50), default="info") # info, alerta, urgente
    ativo = Column(Integer, default=1) # 1 for active, 0 for inactive. Using Integer for sqlite compatibility if needed, or Boolean
    data_criacao = Column(DateTime, default=get_brasilia_time)
    autor_id = Column(Integer, nullable=True) # ID of the admin who created it
    destinatarios_alcancados = Column(Integer, default=0) # Contagem de envios de SMS bem sucedidos

class FileStorage(Base):
    __tablename__ = "file_storage"

    id = Column(String(36), primary_key=True, index=True) # UUID
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    data = Column(LargeBinary, nullable=False)
    criado_em = Column(DateTime, default=get_brasilia_time)
