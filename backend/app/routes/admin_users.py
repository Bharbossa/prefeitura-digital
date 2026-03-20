from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.schema import Usuario, StatusUsuario
from ..models.pydantic_schemas import UsuarioResponse
from ..core.auth_deps import get_current_user
from ..core.firebase_config import db, DB_MODE

router = APIRouter()

@router.get("/pending", response_model=List[UsuarioResponse])
def get_pending_users(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    # Check if current user is admin
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        docs = db.collection("usuarios").where("status", "==", "Pendente").get()
        users = []
        for d in docs:
            u = d.to_dict()
            u["id"] = d.id
            users.append(u)
        return users
    else:
        return db_sql.query(Usuario).filter(Usuario.status == StatusUsuario.pendente).all()

@router.post("/{user_id}/approve")
def approve_user(user_id: str, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("usuarios").document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        doc_ref.update({"status": "Ativo"})
    else:
        user = db_sql.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        user.status = StatusUsuario.ativo
        db_sql.commit()
    
    return {"message": "Usuário aprovado com sucesso."}

@router.post("/{user_id}/reject")
def reject_user(user_id: str, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("usuarios").document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        doc_ref.update({"status": "Rejeitado"})
    else:
        user = db_sql.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        user.status = StatusUsuario.rejeitado
        db_sql.commit()
    
    return {"message": "Usuário rejeitado."}
