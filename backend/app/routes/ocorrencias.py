from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from ..database import get_db
from ..models.schema import Ocorrencia, Resposta, AdminSecretaria, LogAuditoria
from ..core.firebase_config import db, DB_MODE
from ..models.pydantic_schemas import OcorrenciaResponse, RespostaResponse
from ..core.auth_deps import get_current_user, get_current_admin
from ..utils.sms_service import send_status_sms, get_resolved_message

from ..core.utils import generate_protocol
from datetime import datetime

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

@router.post("/", response_model=OcorrenciaResponse)
def create_ocorrencia(
    titulo: str = Form(...),
    descricao: str = Form(...),
    secretaria_id: int = Form(...),
    foto: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    foto_path = save_upload_file(foto) if foto else None
    video_path = save_upload_file(video) if video else None
    protocolo = generate_protocol()

    # SQL Implementation
    ocorrencia = Ocorrencia(
        protocolo=protocolo,
        titulo=titulo, 
        descricao=descricao, 
        secretaria_id=secretaria_id,
        foto=foto_path, 
        video=video_path, 
        usuario_id=current_user.id
    )
    db_sql.add(ocorrencia)
    db_sql.commit()
    db_sql.refresh(ocorrencia)
    return ocorrencia

@router.get("/", response_model=List[OcorrenciaResponse])
def get_current_ocorrencias(
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    role = current_user.tipo_usuario_verificado
    
    if role in ["admin", "subadmin"]:
        # If they are tied to a secretariat, filter by it. If General Admin (no sec_id), show all.
        sec_id = current_user.secretaria_id
        if sec_id:
            query = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == sec_id)
        else:
            query = db_sql.query(Ocorrencia)
    else:
        # Citizen: show only own
        query = db_sql.query(Ocorrencia).filter(Ocorrencia.usuario_id == current_user.id)
    
    return query.order_by(Ocorrencia.data.desc()).all()

@router.patch("/{id}/status", response_model=OcorrenciaResponse)
def update_status(
    id: int, 
    status: str, 
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id).first()
    if not ocorrencia: 
        raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
    
    # Permission check: subadmin must belong to the secretariat
    if current_user.tipo_usuario_verificado == "subadmin":
        if ocorrencia.secretaria_id != current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Sem permissão para esta secretaria")
    
    old_status = ocorrencia.status
    ocorrencia.status = status
    
    # Audit trail
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo=current_user.tipo_usuario_verificado,
        acao="update_status",
        detalhes=f"Ocorrência {id} ({ocorrencia.protocolo}): {old_status} -> {status}"
    )
    db_sql.add(log)
    if status == "Resolvido" and old_status != "Resolvido":
        if ocorrencia.usuario and ocorrencia.usuario.telefone:
            msg = get_resolved_message(ocorrencia.titulo)
            send_status_sms(ocorrencia.usuario.telefone, msg)
            
    db_sql.commit()
    db_sql.refresh(ocorrencia)
    return ocorrencia


@router.post("/{id}/respostas", response_model=RespostaResponse)
def add_resposta(
    id: int, 
    mensagem: str = Form(...),
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id).first()
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
    
    # Permission check for subadmin
    if current_user.tipo_usuario_verificado == "subadmin":
        if ocorrencia.secretaria_id != current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Sem permissão para responder a esta secretaria")

    # If subadmin is tied to a secretariat, they use their AdminSecretaria table entry for the response relationship?
    # Wait, the Resposta model joins to AdminSecretaria. 
    # If the current_user is a General Admin (from Usuario table), we might need to adjust the model.
    # For now, I'll assume only Subadmins/Secretariat Admins respond.
    
    admin_id = current_user.id
    # Note: If current_user is General Admin, their ID might not exist in admins_secretaria.
    # I'll check if it exists or use a default.
    
    resposta = Resposta(
        mensagem=mensagem,
        ocorrencia_id=id,
        admin_id=admin_id if current_user.tipo_usuario_verificado == "subadmin" else None
    )
    db_sql.add(resposta)
    
    # Audit
    log = LogAuditoria(
        usuario_id=current_user.id,
        usuario_tipo=current_user.tipo_usuario_verificado,
        acao="add_response",
        detalhes=f"Resposta adicionada à ocorrência {id} ({ocorrencia.protocolo})"
    )
    db_sql.add(log)
    db_sql.commit()
    db_sql.refresh(resposta)
    return resposta

