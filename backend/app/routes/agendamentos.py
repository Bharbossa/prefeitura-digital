from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, Agendamento
from ..models.pydantic_schemas import AgendamentoCreate, AgendamentoResponse
from ..core.auth_deps import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_upload_file(upload_file: UploadFile) -> str:
    file_ext = os.path.splitext(upload_file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

router = APIRouter()

@router.post("/", response_model=AgendamentoResponse)
def criar_agendamento(agend: AgendamentoCreate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar agendamentos pelo perfil.")
    
    novo_agendamento = Agendamento(
        usuario_id=current_user.id,
        secretaria_id=agend.secretaria_id,
        tipo=agend.tipo,
        assunto=agend.assunto,
        motivo=agend.motivo,
        acompanhante=agend.acompanhante,
        data_hora=agend.data_hora
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)
    return novo_agendamento

@router.post("/viagem", response_model=AgendamentoResponse)
def criar_agendamento_viagem(
    secretaria_id: int = Form(...),
    tipo: str = Form(...),
    assunto: str = Form(...),
    motivo: Optional[str] = Form(None),
    acompanhante: Optional[str] = Form(None),
    data_hora: str = Form(...),
    comprovante: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)):
    
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar agendamentos pelo perfil.")
        
    try:
        data_obj = datetime.fromisoformat(data_hora.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use ISO 8601.")
        
    arquivo_path = save_upload_file(comprovante) if comprovante else None

    novo_agendamento = Agendamento(
        usuario_id=current_user.id,
        secretaria_id=secretaria_id,
        tipo=tipo,
        assunto=assunto,
        motivo=motivo,
        acompanhante=acompanhante,
        data_hora=data_obj,
        anexo=arquivo_path
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)
    return novo_agendamento


@router.get("/", response_model=List[AgendamentoResponse])
def listar_meus_agendamentos(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    t_verificado = getattr(current_user, "tipo_usuario_verificado", "")
    
    if t_verificado == "cidadao":
        # Cidadão lista apenas os seus próprios agendamentos
        return db_sql.query(Agendamento).filter(Agendamento.usuario_id == current_user.id).order_by(Agendamento.data_hora.desc()).all()
    
    if t_verificado == "admin":
        # Se tiver secretaria_id no objeto, filtra por ela
        sec_id = getattr(current_user, "secretaria_id", None)
        if sec_id:
            return db_sql.query(Agendamento).filter(Agendamento.secretaria_id == sec_id).order_by(Agendamento.data_hora.desc()).all()
        # Admin geral
        return db_sql.query(Agendamento).order_by(Agendamento.data_hora.desc()).all()
    
    raise HTTPException(status_code=403, detail="Não autorizado.")

@router.patch("/{agend_id}/status")
def atualizar_status(agend_id: int, status: str, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if status not in ["Confirmado", "Cancelado", "Pendente"]:
        raise HTTPException(status_code=400, detail="Status inválido.")
        
    agendamento = db_sql.query(Agendamento).filter(Agendamento.id == agend_id).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    
    # Se for sub-admin de secretaria, verifica se pertence a ela
    sec_id = getattr(current_user, "secretaria_id", None)
    if sec_id and agendamento.secretaria_id != sec_id:
        raise HTTPException(status_code=403, detail="Agendamento pertence a outra secretaria.")
            
    agendamento.status = status
    db_sql.commit()
    return {"message": "Status atualizado com sucesso"}
