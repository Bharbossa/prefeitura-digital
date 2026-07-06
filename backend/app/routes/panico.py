from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any
from ..database import get_db
from ..models.schema import Usuario, LogAuditoria
from ..core.auth_deps import get_current_user, get_current_admin
from ..utils.notification_helper import notify_admins_of_new_record

router = APIRouter()

class PanicAuthRequest(BaseModel):
    user_id: int
    authorize: bool

@router.post("")
def trigger_panic_button(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
        
    user = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    if getattr(user, 'botao_panico_autorizado', 0) != 1:
        raise HTTPException(status_code=403, detail="Você não tem autorização para utilizar o Botão do Pânico.")

    msg = f"🚨 ALERTA DE PÂNICO 🚨\nA usuária {user.nome} acionou o Botão do Pânico!\nTel: {user.telefone}\nEndereço: {user.endereco}"
    
    # 17 is the GUARDA MUNICIPAL
    background_tasks.add_task(notify_admins_of_new_record, db_sql, 17, msg)
    
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="botao_panico",
        detalhes=f"Acionou o Botão do Pânico"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Alerta enviado com sucesso para a Guarda Municipal."}

@router.post("/request")
def request_panic_authorization(
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if not hasattr(current_user, 'id'):
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
        
    user = db_sql.query(Usuario).filter(Usuario.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    if getattr(user, 'botao_panico_autorizado', 0) == 1:
        return {"message": "Você já possui acesso autorizado."}
        
    user.botao_panico_autorizado = 2 # 2 = Pendente
    
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="solicitar_panico",
        detalhes=f"Solicitou acesso ao Botão do Pânico"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Solicitação enviada com sucesso. Aguarde análise da Guarda Municipal."}

def check_admin_permission(admin):
    # Only general admin or Guarda Municipal sub-admin (sec_id 17) can access
    if admin.tipo_usuario_verificado == "admin":
        return True
    if admin.tipo_usuario_verificado == "subadmin" and getattr(admin, "secretaria_id", None) == 17:
        return True
    raise HTTPException(status_code=403, detail="Sem permissão para gerenciar o Botão do Pânico.")

@router.get("/requests")
def list_panic_requests(
    current_admin = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    check_admin_permission(current_admin)
    
    users = db_sql.query(Usuario).filter(Usuario.botao_panico_autorizado.in_([1, 2])).order_by(Usuario.botao_panico_autorizado.desc()).all()
    
    results = []
    for u in users:
        results.append({
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "telefone": u.telefone,
            "cpf": u.cpf,
            "endereco": u.endereco,
            "status": u.botao_panico_autorizado
        })
        
    return results

@router.patch("/authorize")
def authorize_panic_request(
    data: PanicAuthRequest,
    current_admin = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    check_admin_permission(current_admin)
    
    user = db_sql.query(Usuario).filter(Usuario.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
    user.botao_panico_autorizado = 1 if data.authorize else 0
    
    action_str = "Autorizou" if data.authorize else "Negou/Revogou"
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="autorizar_panico",
        detalhes=f"{action_str} acesso ao Botão do Pânico para o usuário ID {user.id}"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": f"Status alterado com sucesso."}
