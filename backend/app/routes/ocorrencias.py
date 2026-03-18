from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil

from ..database import get_db
from ..models.schema import Ocorrencia, Resposta, AdminSecretaria
from ..core.firebase_config import db, DB_MODE
from ..models.pydantic_schemas import OcorrenciaResponse, RespostaResponse
from ..core.auth_deps import get_current_user
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
    secretaria_id: str = Form(...),
    foto: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    foto_path = save_upload_file(foto) if foto else None
    video_path = save_upload_file(video) if video else None

    if DB_MODE == "firestore":
        ocorrencia_data = {
            "titulo": titulo, "descricao": descricao, "secretaria_id": secretaria_id,
            "foto": foto_path, "video": video_path, "usuario_id": current_user.id,
            "status": "Pendente", "data": datetime.utcnow()
        }
        doc_ref = db.collection("ocorrencias").document()
        doc_ref.set(ocorrencia_data)
        ocorrencia_data["id"] = doc_ref.id
        return ocorrencia_data
    else:
        # SQLite Fallback
        ocorrencia = Ocorrencia(
            titulo=titulo, descricao=descricao, secretaria_id=int(secretaria_id),
            foto=foto_path, video=video_path, usuario_id=current_user.id
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
    if DB_MODE == "firestore":
        if current_user.tipo_usuario_verificado == "admin":
            admin_docs = db.collection("admin_secretarias").document(current_user.id).get()
            if not admin_docs.exists: return []
            sec_id = admin_docs.to_dict().get("secretaria_id")
            docs = db.collection("ocorrencias").where("secretaria_id", "==", sec_id).get()
        else:
            docs = db.collection("ocorrencias").where("usuario_id", "==", current_user.id).get()
        
        results = []
        for d in docs:
            item = d.to_dict(); item["id"] = d.id
            results.append(item)
        return results
    else:
        # SQLite Fallback
        if current_user.tipo_usuario_verificado == "admin":
            admin = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
            query = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == admin.secretaria_id)
        else:
            query = db_sql.query(Ocorrencia).filter(Ocorrencia.usuario_id == current_user.id)
        
        results = []
        for o in query.all():
            results.append({
                "id": str(o.id), "titulo": o.titulo, "descricao": o.descricao,
                "status": o.status, "data": o.data, "usuario_id": str(o.usuario_id),
                "secretaria_id": str(o.secretaria_id), "foto": o.foto, "video": o.video
            })
        return results

@router.patch("/{id}/status", response_model=OcorrenciaResponse)
def update_status(
    id: str, 
    status: str, 
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem alterar status")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("ocorrencias").document(id)
        doc = doc_ref.get()
        if not doc.exists: raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        admin_doc = db.collection("admin_secretarias").document(current_user.id).get()
        if doc.to_dict().get("secretaria_id") != admin_doc.to_dict().get("secretaria_id"):
            raise HTTPException(status_code=403, detail="Sem permissão")
        doc_ref.update({"status": status})
        updated = doc_ref.get().to_dict(); updated["id"] = id
        return updated
    else:
        # SQLite Fallback
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == int(id)).first()
        if not ocorrencia: raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        admin = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == current_user.id).first()
        if ocorrencia.secretaria_id != admin.secretaria_id: raise HTTPException(status_code=403, detail="Sem permissão")
        ocorrencia.status = status
        db_sql.commit()
        return {
            "id": str(ocorrencia.id), "titulo": ocorrencia.titulo, "descricao": ocorrencia.descricao,
            "status": ocorrencia.status, "data": ocorrencia.data, "usuario_id": str(ocorrencia.usuario_id),
            "secretaria_id": str(ocorrencia.secretaria_id), "foto": ocorrencia.foto, "video": ocorrencia.video
        }

@router.post("/{id}/respostas", response_model=RespostaResponse)
def add_resposta(
    id: str, 
    mensagem: str = Form(...),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Apenas admins podem responder")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("ocorrencias").document(id)
        if not doc_ref.get().exists: raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        resposta_data = {
            "mensagem": mensagem, "ocorrencia_id": id, "admin_id": current_user.id, "data": datetime.utcnow()
        }
        resp_ref = db.collection("respostas").document(); resp_ref.set(resposta_data)
        resposta_data["id"] = resp_ref.id
        return resposta_data
    else:
        # SQL Implementation
        ocorrencia = db_sql.query(Ocorrencia).filter(Ocorrencia.id == int(id)).first()
        if not ocorrencia:
            raise HTTPException(status_code=404, detail="Ocorrencia não encontrada")
        
        resposta = Resposta(
            mensagem=mensagem,
            ocorrencia_id=int(id),
            admin_id=current_user.id
        )
        db_sql.add(resposta)
        db_sql.commit()
        db_sql.refresh(resposta)
        return {
            "id": str(resposta.id),
            "mensagem": resposta.mensagem,
            "ocorrencia_id": str(resposta.ocorrencia_id),
            "admin_id": str(resposta.admin_id),
            "data": resposta.data
        }
