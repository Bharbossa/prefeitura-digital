from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from ..database import get_db
from ..models.schema import Usuario, StatusUsuario, AdminSecretaria, LogAuditoria, TipoUsuario, Ocorrencia, StatusOcorrencia
from ..models.pydantic_schemas import (
    UsuarioResponse, 
    AdminSecretariaCreate, 
    AdminSecretariaResponse, 
    AdminPasswordUpdate
)
from ..core.auth_deps import get_current_user, get_current_admin, get_general_admin
from ..core.security import get_password_hash, verify_password
from ..utils.sms_service import send_status_sms

router = APIRouter()

@router.post("/secretaria-admins/{admin_id}/notificar-pendencias")
def notify_subadmin_pending(admin_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    admin = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Sub-administrador não encontrado.")
    
    if not admin.telefone:
        raise HTTPException(status_code=400, detail="Sub-administrador não possui telefone cadastrado.")

    # Contar ocorrências pendentes da secretaria dele
    count_pending = db_sql.query(Ocorrencia).filter(
        Ocorrencia.secretaria_id == admin.secretaria_id,
        Ocorrencia.status == StatusOcorrencia.pendente
    ).count()

    if count_pending == 0:
        msg = f"COLÔNIA DIGITAL: Olá {admin.nome.split(' ')[0]}, o sistema está em dia! Nenhuma nova ocorrência pendente em sua secretaria."
    else:
        msg = f"ALERTA URGENTE - COLÔNIA DIGITAL: Olá {admin.nome.split(' ')[0]}, existem {count_pending} ocorrências PENDENTES aguardando resposta em sua secretaria. Verifique o painel agora!"

    success = send_status_sms(admin.telefone, msg)
    
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao enviar notificação.")

    # Auditoria
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo="admin",
        acao="notify_subadmin",
        detalhes=f"Enviou alerta de {count_pending} pendências para sub-admin {admin.email} (Tel: {admin.telefone})"
    )
    db_sql.add(log)
    db_sql.commit()

    return {"message": "Notificação enviada com sucesso!", "count_pending": count_pending}

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
    
    from ..models.schema import Agendamento, Ocorrencia, Resposta
    
    # 1. Delete all Agendamentos
    db_sql.query(Agendamento).filter(Agendamento.usuario_id == user_id).delete()
    
    # 2. Delete all Ocorrencias and their Respostas
    ocorrencias = db_sql.query(Ocorrencia).filter(Ocorrencia.usuario_id == user_id).all()
    for oco in ocorrencias:
        db_sql.query(Resposta).filter(Resposta.ocorrencia_id == oco.id).delete()
        db_sql.delete(oco)
    
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
def get_secretaria_admins(current_admin = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    if current_admin.tipo_usuario_verificado == "subadmin":
        return db_sql.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == current_admin.secretaria_id).all()
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
    
    # 1. Handle foreign keys: Unlink their responses from the deleted admin
    from ..models.schema import Resposta
    respostas = db_sql.query(Resposta).filter(Resposta.admin_id == admin_id).all()
    for resp in respostas:
        resp.admin_id = None
        
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
            "tipo": "admin" if str(u.tipo_usuario).split('.')[-1] == "admin" else "cidadao",
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
    current_admin = Depends(get_current_admin), 
    db_sql: Session = Depends(get_db)
):
    hashed_password = get_password_hash(data.new_password)
    
    source_normalized = data.source.strip().lower() if data.source else ""
    if source_normalized == "usuario":
        if current_admin.tipo_usuario_verificado == "subadmin":
            raise HTTPException(status_code=403, detail="Sub-admin não pode resetar senhas de cidadãos.")
        user = db_sql.query(Usuario).filter(Usuario.id == data.user_id).first()
        if not user: raise HTTPException(status_code=404, detail="Usuário não encontrado")
        user.senha_hash = hashed_password
    elif source_normalized == "subadmin":
        sadmin = db_sql.query(AdminSecretaria).filter(AdminSecretaria.id == data.user_id).first()
        if not sadmin: raise HTTPException(status_code=404, detail="Sub-admin não encontrado")
        if current_admin.tipo_usuario_verificado == "subadmin" and sadmin.id != current_admin.id:
            raise HTTPException(status_code=403, detail="Você só pode alterar sua própria senha. Apenas o administrador geral pode alterar outras senhas.")
        sadmin.senha_hash = hashed_password
    else:
        raise HTTPException(status_code=400, detail=f"Fonte inválida recebida: '{data.source}'")
    
    # Audit log
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="reset_password",
        detalhes=f"Resetou senha do {data.source} ID {data.user_id}"
    )
    db_sql.add(log)
    db_sql.commit()
    
    # Optional: Update Firestore if DB_MODE == "firestore"
    from ..core.firebase_config import DB_MODE, db
    if DB_MODE == "firestore":
        if data.source == "usuario" and user:
            user_docs = db.collection("usuarios").where("email", "==", user.email).limit(1).get()
            if user_docs: db.collection("usuarios").document(user_docs[0].id).update({"senha_hash": hashed_password})
        elif data.source == "subadmin" and sadmin:
            admin_docs = db.collection("admin_secretarias").where("email", "==", sadmin.email).limit(1).get()
            if admin_docs: db.collection("admin_secretarias").document(admin_docs[0].id).update({"senha_hash": hashed_password})
            
    return {"message": "Senha alterada com sucesso"}
