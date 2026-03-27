from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models.schema import Usuario, StatusUsuario, AdminSecretaria, LogAuditoria
from ..models.pydantic_schemas import (
    UsuarioResponse, 
    AdminSecretariaCreate, 
    AdminSecretariaResponse, 
    AdminPasswordUpdate
)
from ..core.auth_deps import get_current_user, get_current_admin, get_general_admin
from ..core.security import get_password_hash, verify_password

router = APIRouter()

@router.get("/pending", response_model=List[UsuarioResponse])
def get_pending_users(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    # Only General Admin can see pending users
    return db_sql.query(Usuario).filter(Usuario.status == StatusUsuario.pendente).all()

@router.get("/", response_model=List[UsuarioResponse])
def get_all_users(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    return db_sql.query(Usuario).all()

@router.post("/{user_id}/approve")
def approve_user(user_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    user = db_sql.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    user.status = StatusUsuario.ativo
    
    # Audit
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="approve_user",
        detalhes=f"Aprovou usuário {user_id} ({user.email})"
    )
    db_sql.add(log)
    db_sql.commit()
    return {"message": "Usuário aprovado com sucesso."}

@router.post("/{user_id}/reject")
def reject_user(user_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    user = db_sql.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    user.status = StatusUsuario.rejeitado
    
    # Audit
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="reject_user",
        detalhes=f"Rejeitou usuário {user_id} ({user.email})"
    )
    db_sql.add(log)
    db_sql.commit()
    return {"message": "Usuário rejeitado."}

class AdminOwnPasswordUpdate(BaseModel):
    senha_atual: str
    nova_senha: str

@router.delete("/{user_id}")
def delete_user(user_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Delete a citizen user entirely."""
    user = db_sql.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    email = user.email
    db_sql.delete(user)
    
    # Audit
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="delete_user",
        detalhes=f"Excluiu usuário {user_id} ({email})"
    )
    db_sql.add(log)
    db_sql.commit()
    return {"message": "Usuário excluído com sucesso."}

@router.get("/secretaria-admins", response_model=List[AdminSecretariaResponse])
def get_secretaria_admins(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    # Only General Admin can see list of sub-admins
    return db_sql.query(AdminSecretaria).all()

@router.post("/secretaria-admins", response_model=AdminSecretariaResponse)
def create_secretaria_admin(admin_in: AdminSecretariaCreate, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    # Only General Admin can create sub-admins
    
    existing = db_sql.query(AdminSecretaria).filter(AdminSecretaria.email == admin_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado para outro administrador.")
        
    new_admin = AdminSecretaria(
        nome=admin_in.nome,
        cpf=admin_in.cpf,
        email=admin_in.email,
        telefone=admin_in.telefone,
        senha_hash=get_password_hash(admin_in.senha),
        secretaria_id=admin_in.secretaria_id
    )

    db_sql.add(new_admin)
    
    # Audit
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_admin if hasattr(current_admin, 'tipo_admin') else current_admin.tipo_usuario_verificado,
        acao="create_subadmin",
        detalhes=f"Criou sub-admin {admin_in.email} para secretaria {admin_in.secretaria_id}"
    )
    db_sql.add(log)
    db_sql.commit()
    db_sql.refresh(new_admin)
    return new_admin
@router.delete("/secretaria-admins/{admin_id}")
def delete_secretaria_admin(admin_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    admin_to_delete = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == admin_id).first()
    if not admin_to_delete:
        raise HTTPException(status_code=404, detail="Administrador de secretaria não encontrado.")
    
    email = admin_to_delete.email
    db_sql.delete(admin_to_delete)
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="delete_subadmin",
        detalhes=f"Excluiu sub-admin {admin_id} ({email})"
    )
    db_sql.add(log)
    db_sql.commit()
    return {"message": "Administrador excluído com sucesso."}

@router.get("/all-combined")
def get_all_combined_users(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    # 1. Get Citizens and Admins from Usuario table
    usuarios = db_sql.query(Usuario).all()
    
    # 2. Get Sub-Admins from AdminSecretaria table
    subadmins = db_sql.query(AdminSecretaria).all()
    
    # Combined list
    combined = []
    
    for u in usuarios:
        combined.append({
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "tipo": "admin" if u.tipo_usuario == TipoUsuario.admin else "cidadao",
            "status": u.status,
            "source": "usuario"
        })
        
    for s in subadmins:
        combined.append({
            "id": s.id,
            "nome": s.nome,
            "email": s.email,
            "tipo": "subadmin",
            "status": "Ativo", # AdminSecretaria doesn't have a status field in schema? Check it.
            "source": "subadmin"
        })
        
    return combined
    
@router.patch("/password-reset")
def reset_user_password(
    data: AdminPasswordUpdate, 
    current_admin = Depends(get_general_admin), 
    db_sql: Session = Depends(get_db)
):
    hashed_password = get_password_hash(data.new_password)
    
    if data.source == "usuario":
        user = db_sql.query(Usuario).filter(Usuario.id == data.user_id).first()
        if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
        user.senha_hash = hashed_password
    elif data.source == "subadmin":
        sadmin = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == data.user_id).first()
        if not sadmin: raise HTTPException(status_code=404, detail="Sub-admin não encontrado")
        sadmin.senha_hash = hashed_password
    else:
        raise HTTPException(status_code=400, detail="Fonte inválida")
    
    # Audit log
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo="admin",
        acao="reset_password",
        detalhes=f"Resetou senha do {data.source} ID {data.user_id}"
    )
    db_sql.add(log)
    db_sql.commit()
    return {"message": "Senha alterada com sucesso"}
