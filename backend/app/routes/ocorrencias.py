from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
import traceback

from ..database import get_db
from ..models.schema import Ocorrencia, Resposta, AdminSecretaria, LogAuditoria, Secretaria
from ..models.pydantic_schemas import OcorrenciaResponse, RespostaResponse
from ..core.auth_deps import get_current_user, get_current_admin
from ..utils.sms_service import send_status_sms, get_resolved_message
from ..core.utils import generate_protocol
from datetime import datetime

router = APIRouter()

@router.get("", response_model=List[OcorrenciaResponse])
def get_current_ocorrencias(
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    try:
        role = getattr(current_user, "tipo_usuario_verificado", "cidadao")
        
        if role in ["admin", "subadmin"]:
            sec_id = getattr(current_user, "secretaria_id", None)
            query = db_sql.query(Ocorrencia)
            if sec_id:
                query = query.filter(Ocorrencia.secretaria_id == sec_id)
        else:
            query = db_sql.query(Ocorrencia).filter(Ocorrencia.usuario_id == current_user.id)
        
        ocorrencias = query.order_by(Ocorrencia.data.desc()).all()
        
        # Populate secretaria_nome
        for o in ocorrencias:
            if o.secretaria:
                o.secretaria_nome = o.secretaria.nome
            else:
                o.secretaria_nome = "Geral"
                
        return ocorrencias
    except Exception as e:
        print(f"DEBUG ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("", response_model=OcorrenciaResponse)
async def create_ocorrencia(
    titulo: str = Form(...),
    descricao: str = Form(...),
    secretaria_id: int = Form(...),
    rua: Optional[str] = Form(None),
    ponto_referencia: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    UPLOAD_DIR = "uploads"
    if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
    
    def save_file(ufile):
        ext = os.path.splitext(ufile.filename)[1]
        name = f"{uuid.uuid4()}{ext}"
        path = os.path.join(UPLOAD_DIR, name)
        with open(path, "wb") as buf: shutil.copyfileobj(ufile.file, buf)
        return path

    foto_path = save_file(foto) if foto and foto.filename else None
    video_path = save_file(video) if video and video.filename else None
    protocolo = generate_protocol()

    try:
        ocorrencia = Ocorrencia(
            protocolo=protocolo,
            titulo=titulo, 
            descricao=descricao, 
            rua=rua,
            ponto_referencia=ponto_referencia,
            secretaria_id=secretaria_id,
            foto=foto_path, 
            video=video_path, 
            usuario_id=current_user.id
        )
        db_sql.add(ocorrencia)
        db_sql.commit()
        db_sql.refresh(ocorrencia)
        return ocorrencia
    except Exception as e:
        db_sql.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{id}/status")
async def update_status(
    id: int, 
    status: str, 
    resposta: Optional[str] = None,
    foto_resolucao: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    try:
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id).first()
        if not ocorrencia: raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        
        if current_user.tipo_usuario_verificado == "subadmin":
            if ocorrencia.secretaria_id != current_user.secretaria_id:
                raise HTTPException(status_code=403, detail="Sem permissão")
        
        ocorrencia.status = status.lower().strip()
        if foto_resolucao:
            # Re-using internal save_file won't work easily here, just manually save
            ext = os.path.splitext(foto_resolucao.filename)[1]
            name = f"{uuid.uuid4()}{ext}"
            path = os.path.join("uploads", name)
            with open(path, "wb") as buf: shutil.copyfileobj(foto_resolucao.file, buf)
            ocorrencia.foto_resolucao = path
            
        if resposta:
            db_sql.add(Resposta(mensagem=resposta, ocorrencia_id=id, admin_id=current_user.id if current_user.tipo_usuario_verificado == "subadmin" else None))
            
        db_sql.commit()
        return {"message": "Status atualizado"}
    except Exception as e:
        db_sql.rollback()
        raise HTTPException(status_code=500, detail=str(e))
