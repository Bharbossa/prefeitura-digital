from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Enum
from sqlalchemy.orm import relationship
import enum
import datetime
from ..database import Base

class TipoUsuario(str, enum.Enum):
    cidadao = "cidadao"
    admin = "admin"

class StatusOcorrencia(str, enum.Enum):
    pendente = "Pendente"
    em_atendimento = "Em atendimento"
    resolvido = "Resolvido"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    cpf = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    telefone = Column(String(20))
    endereco = Column(String(255))
    senha_hash = Column(String(255), nullable=False)
    tipo_usuario = Column(Enum(TipoUsuario), default=TipoUsuario.cidadao)

    ocorrencias = relationship("Ocorrencia", back_populates="usuario")

class Secretaria(Base):
    __tablename__ = "secretarias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), unique=True, nullable=False)

    admins = relationship("AdminSecretaria", back_populates="secretaria")
    ocorrencias = relationship("Ocorrencia", back_populates="secretaria")

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

    secretaria = relationship("Secretaria", back_populates="admins")
    respostas = relationship("Resposta", back_populates="admin")

class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=False)
    foto = Column(String(255), nullable=True)   # Path/URL
    video = Column(String(255), nullable=True)  # Path/URL
    status = Column(Enum(StatusOcorrencia), default=StatusOcorrencia.pendente)
    data = Column(DateTime, default=datetime.datetime.utcnow)
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    secretaria_id = Column(Integer, ForeignKey("secretarias.id"))

    usuario = relationship("Usuario", back_populates="ocorrencias")
    secretaria = relationship("Secretaria", back_populates="ocorrencias")
    respostas = relationship("Resposta", back_populates="ocorrencia")

class Resposta(Base):
    __tablename__ = "respostas"

    id = Column(Integer, primary_key=True, index=True)
    mensagem = Column(Text, nullable=False)
    data = Column(DateTime, default=datetime.datetime.utcnow)

    ocorrencia_id = Column(Integer, ForeignKey("ocorrencias.id"))
    admin_id = Column(Integer, ForeignKey("admins_secretaria.id"))

    ocorrencia = relationship("Ocorrencia", back_populates="respostas")
    admin = relationship("AdminSecretaria", back_populates="respostas")

class ChatIA(Base):
    __tablename__ = "chat_ia"

    id = Column(Integer, primary_key=True, index=True)
    mensagem_usuario = Column(Text, nullable=False)
    resposta_ia = Column(Text, nullable=False)
    data = Column(DateTime, default=datetime.datetime.utcnow)
    
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # Optional link to user if logged in

    usuario = relationship("Usuario")
