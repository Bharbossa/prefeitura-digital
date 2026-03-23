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

from ..core.security import get_password_hash
from ..models.schema import AdminSecretaria
from ..models.pydantic_schemas import AdminSecretariaCreate, AdminSecretariaResponse, AdminPasswordUpdate

@router.get("/secretaria-admins", response_model=List[AdminSecretariaResponse])
def get_secretaria_admins(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if not isinstance(current_user, Usuario) or current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode listar sub-admins.")
    
    admins = db_sql.query(AdminSecretaria).all()
    # Adicionar status padrão Ativo para manter consistência
    for a in admins:
        if not hasattr(a, "status"):
            a.status = "Ativo"
    return admins

@router.post("/secretaria-admins", response_model=AdminSecretariaResponse)
def create_secretaria_admin(admin_in: AdminSecretariaCreate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if not isinstance(current_user, Usuario) or current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode criar sub-admins.")
    
    # Check if email exists
    existing = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == admin_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado para outro administrador.")
        
    hashed_password = get_password_hash(admin_in.senha)
    new_admin = AdminSecretaria(
        nome=admin_in.nome,
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
    if not isinstance(current_user, Usuario) or current_user.tipo_usuario_verificado != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador geral pode alterar senhas.")
    
    admin_to_update = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == admin_id).first()
    if not admin_to_update:
        raise HTTPException(status_code=404, detail="Administrador de secretaria não encontrado.")
        
    admin_to_update.senha_hash = get_password_hash(pw_in.nova_senha)
    db_sql.commit()
    return {"message": "Senha atualizada com sucesso."}
