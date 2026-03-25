from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models.schema import Usuario, StatusUsuario, AdminSecretaria
from ..models.pydantic_schemas import (
    UsuarioResponse, 
    AdminSecretariaCreate, 
    AdminSecretariaResponse, 
    AdminPasswordUpdate
)
from ..core.auth_deps import get_current_user
from ..core.firebase_config import db, DB_MODE
from ..core.security import get_password_hash, verify_password

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

@router.get("/", response_model=List[UsuarioResponse])
def get_all_users(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    # Check if current user is admin
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        docs = db.collection("usuarios").get()
        users = []
        for d in docs:
            u = d.to_dict()
            u["id"] = d.id
            users.append(u)
        return users
    else:
        # Return all users (except maybe other admins if we want to be safe, but they are in different table)
        return db_sql.query(Usuario).all()

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

from pydantic import BaseModel

class AdminOwnPasswordUpdate(BaseModel):
    senha_atual: str
    nova_senha: str

@router.delete("/{user_id}")
def delete_user(user_id: str, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    """Delete a citizen user entirely."""
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("usuarios").document(user_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        doc_ref.delete()
    else:
        user = db_sql.query(Usuario).filter(Usuario.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        db_sql.delete(user)
        db_sql.commit()
    
    return {"message": "Usuário excluído com sucesso."}

@router.patch("/me/password")
def change_own_password(pw_in: AdminOwnPasswordUpdate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    """Allow admin to change their own password after verifying the current one."""
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Não autorizado.")
    
    if DB_MODE == "firestore":
        doc_ref = db.collection("usuarios").where("email", "==", current_user.email).limit(1).get()
        if not doc_ref:
            raise HTTPException(status_code=404, detail="Administrador não encontrado.")
        
        user_data = doc_ref[0].to_dict()
        if not verify_password(pw_in.senha_atual, user_data.get("senha_hash")):
            raise HTTPException(status_code=400, detail="Senha atual incorreta.")
        
        db.collection("usuarios").document(doc_ref[0].id).update({
            "senha_hash": get_password_hash(pw_in.nova_senha)
        })
    else:
        user = db_sql.query(Usuario).filter(Usuario.email == current_user.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Administrador não encontrado.")
        
        if not verify_password(pw_in.senha_atual, user.senha_hash):
            raise HTTPException(status_code=400, detail="Senha atual incorreta.")
        
        user.senha_hash = get_password_hash(pw_in.nova_senha)
        db_sql.commit()
    
    return {"message": "Senha alterada com sucesso."}


@router.get("/secretaria-admins", response_model=List[AdminSecretariaResponse])
def get_secretaria_admins(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode listar sub-admins.")
    
    admins = db_sql.query(AdminSecretaria).all()
    # Adicionar status padrão Ativo para manter consistência
    for a in admins:
        if not hasattr(a, "status"):
            a.status = "Ativo"
    return admins

@router.post("/secretaria-admins", response_model=AdminSecretariaResponse)
def create_secretaria_admin(admin_in: AdminSecretariaCreate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode criar sub-admins.")
    
    # Check if email exists
    existing = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == admin_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado para outro administrador.")
        
    hashed_password = get_password_hash(admin_in.senha)
    new_admin = AdminSecretaria(
        nome=admin_in.nome,
        cpf=admin_in.cpf,
        email=admin_in.email,
        senha_hash=hashed_password,
        secretaria_id=admin_in.secretaria_id
    )
    db_sql.add(new_admin)
    db_sql.commit()
    db_sql.refresh(new_admin)
    new_admin.status = "Ativo" # Transient status return
    return new_admin

@router.patch("/secretaria-admins/{admin_id}/password")
def update_secretaria_admin_password(admin_id: int, pw_in: AdminPasswordUpdate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode alterar senhas.")
    
    admin_to_update = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == admin_id).first()
    if not admin_to_update:
        raise HTTPException(status_code=404, detail="Administrador de secretaria não encontrado.")
        
    admin_to_update.senha_hash = get_password_hash(pw_in.nova_senha)
    db_sql.commit()
    return {"message": "Senha atualizada com sucesso."}

@router.delete("/secretaria-admins/{admin_id}")
def delete_secretaria_admin(admin_id: int, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode excluir sub-admins.")
    
    admin_to_delete = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == admin_id).first()
    if not admin_to_delete:
        raise HTTPException(status_code=404, detail="Administrador de secretaria não encontrado.")
    
    db_sql.delete(admin_to_delete)
    db_sql.commit()
    return {"message": "Administrador excluído com sucesso."}
