from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import os
import uuid
import shutil
import traceback

from ..database import get_db
from ..models.schema import Ocorrencia, Resposta, AdminSecretaria, LogAuditoria, Secretaria
from ..models.pydantic_schemas import OcorrenciaResponse, RespostaResponse
from ..core.auth_deps import get_current_user, get_current_admin, get_general_admin
from ..utils.sms_service import send_status_sms, get_resolved_message, get_progress_message, get_cancelled_message
from ..utils.notification_helper import notify_admins_of_new_record
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
            query = db_sql.query(Ocorrencia).options(joinedload(Ocorrencia.usuario), joinedload(Ocorrencia.secretaria))
            if sec_id:
                query = query.filter(Ocorrencia.secretaria_id == sec_id)
            # Administrador global (sem sec_id) vai ver TODAS a partir daqui
        else:
            query = db_sql.query(Ocorrencia).options(joinedload(Ocorrencia.usuario), joinedload(Ocorrencia.secretaria)).filter(Ocorrencia.usuario_id == current_user.id)
        
        ocorrencias = query.order_by(Ocorrencia.data.desc()).all()
        
        # Populate secretaria_nome and usuario_nome
        for o in ocorrencias:
            if o.secretaria:
                o.secretaria_nome = o.secretaria.nome
            else:
                o.secretaria_nome = "Geral"
            o.usuario_nome = o.usuario.nome if o.usuario else "Desconhecido"
                
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
    documento: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    anonima: Optional[bool] = Form(False),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    print(f"DEBUG: Recebendo ocorrência - Lat: {latitude}, Lng: {longitude}")
    UPLOAD_DIR = "uploads"
    if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
    
    def save_file(ufile):
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.mp4', '.mov', '.avi'}
        ext = os.path.splitext(ufile.filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Extensão de arquivo '{ext}' não permitida.")
            
        file_id = str(uuid.uuid4())
        content = ufile.file.read()
        
        # Compress images to save space
        if ext in {'.jpg', '.jpeg', '.png', '.webp'}:
            try:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(content))
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.thumbnail((1200, 1200))
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=75)
                content = output.getvalue()
                ext = ".jpg"
                ufile.content_type = "image/jpeg"
            except Exception:
                pass
                
        content_type = ufile.content_type or "application/octet-stream"
        from ..models.schema import FileStorage
        new_file = FileStorage(
            id=file_id,
            filename=f"{file_id}{ext}",
            content_type=content_type,
            data=content
        )
        db_sql.add(new_file)
        # Flush to make it available (will commit at end of request)
        db_sql.flush()
        
        return f"api/files/{file_id}"

    foto_path = save_file(foto) if foto and foto.filename else None
    video_path = save_file(video) if video and video.filename else None
    documento_path = save_file(documento) if documento and documento.filename else None
    protocolo = generate_protocol()

    try:
        ocorrencia = Ocorrencia(
            protocolo=protocolo,
            titulo=titulo, 
            descricao=descricao, 
            rua=rua,
            ponto_referencia=ponto_referencia,
            secretaria_id=secretaria_id,
            latitude=latitude,
            longitude=longitude,
            foto=foto_path, 
            video=video_path,
            documento=documento_path,
            usuario_id=None if anonima else current_user.id
        )
        db_sql.add(ocorrencia)
        db_sql.commit()
        db_sql.refresh(ocorrencia)

        # Notificar administradores
        msg = f"COLÔNIA DIGITAL: Nova Ocorrência ({protocolo}) registrada. Verifique o painel!"
        notify_admins_of_new_record(db_sql, secretaria_id, msg)

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
            # Use FileStorage logic for foto_resolucao
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
            ext = os.path.splitext(foto_resolucao.filename)[1].lower()
            
            file_id = str(uuid.uuid4())
            content = foto_resolucao.file.read()
            
            if ext in {'.jpg', '.jpeg', '.png', '.webp'}:
                try:
                    import io
                    from PIL import Image
                    img = Image.open(io.BytesIO(content))
                    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                    img.thumbnail((1200, 1200))
                    output = io.BytesIO()
                    img.save(output, format="JPEG", quality=75)
                    content = output.getvalue()
                    ext = ".jpg"
                    foto_resolucao.content_type = "image/jpeg"
                except Exception:
                    pass
            
            content_type = foto_resolucao.content_type or "application/octet-stream"
            from ..models.schema import FileStorage
            new_file = FileStorage(
                id=file_id,
                filename=f"{file_id}{ext}",
                content_type=content_type,
                data=content
            )
            db_sql.add(new_file)
            ocorrencia.foto_resolucao = f"api/files/{file_id}"
            
        if resposta:
            db_sql.add(Resposta(mensagem=resposta, ocorrencia_id=id, admin_id=current_user.id if current_user.tipo_usuario_verificado == "subadmin" else None))
            
        # Pega as informações ANTES de dar commit, pois o commit expira os objetos do SQLAlchemy
        should_send = False
        phone_to_send = None
        msg_titulo = ocorrencia.titulo
        status_limpo = status.lower().strip()
        
        if status_limpo in ["resolvido", "em_atendimento", "cancelado"] and ocorrencia.usuario:
            phone_to_send = ocorrencia.usuario.whatsapp or ocorrencia.usuario.telefone
            should_send = True

        db_sql.commit()
        
        # Envia a mensagem após salvar o status com sucesso
        if should_send and phone_to_send:
            if status_limpo == "resolvido":
                msg = get_resolved_message(msg_titulo)
            elif status_limpo == "em_atendimento":
                msg = get_progress_message(msg_titulo)
            elif status_limpo == "cancelado":
                msg = get_cancelled_message(msg_titulo)
                
            if 'msg' in locals():
                send_status_sms(phone_to_send, msg)
                
        return {"message": "Status atualizado"}
    except Exception as e:
        db_sql.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{id}/cobrar")
async def cobrar_secretaria(
    id: int, 
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    try:
        if current_user.tipo_usuario_verificado != "admin":
            raise HTTPException(status_code=403, detail="Apenas administrador geral pode cobrar secretaria.")
            
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id).first()
        if not ocorrencia or not ocorrencia.secretaria_id:
            raise HTTPException(status_code=404, detail="Ocorrência ou secretaria não encontrada.")
            
        subadmins = db_sql.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == ocorrencia.secretaria_id).all()
        
        msg = f"URGENTE - COLÔNIA DIGITAL: A ocorrência '{ocorrencia.titulo}' precisa ser resolvida. Verifique no painel!"
        msg_voice = "Atenção. Você recebeu uma cobrança urgente do Administrador Geral sobre uma ocorrência pendente na sua secretaria. Por favor, verifique o painel."
        
        from ..utils.sms_service import make_voice_call
        for sa in subadmins:
            if sa.telefone:
                send_status_sms(sa.telefone, msg)
                make_voice_call(sa.telefone, msg_voice)
                
                
        # Add to audit log
        log = LogAuditoria(usuario_id=current_user.id, usuario_tipo="admin", acao="Alerta/Cobrança Enviada", detalhes=f"Ocorrência {ocorrencia.id} cobrada para a Secretaria {ocorrencia.secretaria_id}")
        db_sql.add(log)
        db_sql.commit()
        
        return {"message": "Alerta enviado aos responsáveis"}
    except Exception as e:
        db_sql.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel

class AvaliacaoSchema(BaseModel):
    nota: int
    comentario: Optional[str] = None

@router.post("/{id}/avaliar")
async def avaliar_ocorrencia(
    id: int, 
    data: AvaliacaoSchema,
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    try:
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == id, Ocorrencia.usuario_id == current_user.id).first()
        if not ocorrencia:
            raise HTTPException(status_code=404, detail="Ocorrência não encontrada.")
            
        if ocorrencia.status.lower() not in ["resolvido", "concluído", "concluido"]:
            raise HTTPException(status_code=400, detail="Apenas serviços resolvidos podem ser avaliados.")
            
        if ocorrencia.avaliacao_nota is not None:
            raise HTTPException(status_code=400, detail="Esta solicitação já foi avaliada.")
            
        if not (1 <= data.nota <= 5):
            raise HTTPException(status_code=400, detail="Nota deve ser de 1 a 5.")
            
        setattr(ocorrencia, 'avaliacao_nota', data.nota)
        setattr(ocorrencia, 'avaliacao_comentario', data.comentario)
        db_sql.commit()
        return {"message": "Avaliação enviada com sucesso"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db_sql.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{ocorrencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_ocorrencia(ocorrencia_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Deleta uma ocorrência. Apenas o administrador geral."""
    from app.models.schema import LogAuditoria, Resposta
    
    oc = db_sql.query(Ocorrencia).filter(Ocorrencia.id == ocorrencia_id).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada.")
    
    protocolo = oc.protocolo
    
    # Delete related responses
    db_sql.query(Resposta).filter(Resposta.ocorrencia_id == ocorrencia_id).delete()
    
    db_sql.delete(oc)
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo="admin",
        acao="delete_ocorrencia",
        detalhes=f"Deletada ocorrência protocolo {protocolo}"
    )
    db_sql.add(log)
    db_sql.commit()
    
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
