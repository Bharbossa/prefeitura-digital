from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from ..database import get_db
from ..models.schema import Ocorrencia, Resposta, AdminSecretaria, LogAuditoria, Secretaria
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
    foto_path = None
    if foto and foto.filename:
        foto_path = save_upload_file(foto)
        
    video_path = None
    if video and video.filename:
        video_path = save_upload_file(video)
        
    protocolo = generate_protocol()

    try:
        # SQL Implementation
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

@router.get("", response_model=List[OcorrenciaResponse])
def get_current_ocorrencias(
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    import traceback
    try:
        role = current_user.tipo_usuario_verificado
        
        if role in ["admin", "subadmin"]:
            sec_id = current_user.secretaria_id
            # Use join to get secretaria name for Admin visibility
            query = db_sql.query(Ocorrencia)
            if sec_id:
                query = query.filter(Ocorrencia.secretaria_id == sec_id)
        else:
            # Citizen: show only own
            query = db_sql.query(Ocorrencia).filter(Ocorrencia.usuario_id == current_user.id)
        
        ocorrencias = query.order_by(Ocorrencia.data.desc()).all()
        for o in ocorrencias:
            if o.secretaria:
                o.secretaria_nome = o.secretaria.nome
        return ocorrencias
    except Exception as e:
        print("ERROR IN get_current_ocorrencias:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug-raw")
def get_debug_raw(db_sql: Session = Depends(get_db)):
    ocorrencias = db_sql.query(Ocorrencia).all()
    return [{"id": o.id, "status": o.status, "data": str(o.data), "sec_id": o.secretaria_id} for o in ocorrencias]
async def update_status(
    id: int, 
    status: str, 
    resposta: Optional[str] = None,
    foto_resolucao: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    import traceback
    try:
        # Normalize status to lowercase to match PostgreSQL enum
        status = status.lower().strip()
        valid_statuses = ["pendente", "em_atendimento", "resolvido"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Status inválido. Use: {valid_statuses}")
        
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id).first()
        if not ocorrencia: 
            raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        
        # Permission check: subadmin must belong to the secretariat
        if current_user.tipo_usuario_verificado == "subadmin":
            if ocorrencia.secretaria_id != current_user.secretaria_id:
                raise HTTPException(status_code=403, detail="Sem permissão para esta secretaria")
        
        old_status = ocorrencia.status
        ocorrencia.status = status
        
        # Handle resolution photo
        if foto_resolucao:
            res_foto_path = save_upload_file(foto_resolucao)
            ocorrencia.foto_resolucao = res_foto_path
        
        # Save the typed resolution 'resposta' if provided
        if resposta:
            nova_resposta = Resposta(
                mensagem=resposta,
                ocorrencia_id=id,
                admin_id=current_user.id if current_user.tipo_usuario_verificado == "subadmin" else None
            )
            db_sql.add(nova_resposta)
        
        # Audit trail
        log = LogAuditoria(
            usuario_id=current_user.id,
            usuario_tipo=current_user.tipo_usuario_verificado,
            acao="update_status",
            detalhes=f"Ocorrência {id} ({ocorrencia.protocolo}): {old_status} -> {status}"
        )
        db_sql.add(log)
        
        # SMS notification
        try:
            if status == "resolvido" and str(old_status).lower() != "resolvido":
                if ocorrencia.usuario and ocorrencia.usuario.telefone:
                    msg = get_resolved_message(ocorrencia.titulo)
                    send_status_sms(ocorrencia.usuario.telefone, msg)
        except Exception:
            pass  # SMS failure should not block resolution
                
        db_sql.commit()
        
        return {"message": "Status atualizado com sucesso", "id": id, "status": status}
    except HTTPException:
        raise
    except Exception as e:
        db_sql.rollback()
        print(f"ERRO update_status: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


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

