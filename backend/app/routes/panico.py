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

class PanicAddUserRequest(BaseModel):
    nome: str
    cpf: str
    telefone: str
    endereco: str

class PanicTriggerRequest(BaseModel):
    ponto_referencia: str = ""

@router.post("")
def trigger_panic_button(
    data: PanicTriggerRequest,
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

    ponto_ref = data.ponto_referencia if data and data.ponto_referencia else "(Não informado)"
    
    from urllib.parse import quote
    maps_link = f"https://maps.google.com/?q={quote(user.endereco)}"

    msg = f"🚨 ALERTA DE SOCORRO! 🚨\nO(A) {user.nome} acionou o Botão do Pânico!\nTel: {user.telefone}\nEndereço: {user.endereco}\nRef: {ponto_ref}\nLocalização: {maps_link}"
    
    # 17 is the GUARDA MUNICIPAL
    from ..utils.sms_service import notify_subadmins_background
    background_tasks.add_task(notify_subadmins_background, 17, msg)
    background_tasks.add_task(notify_admins_of_new_record, db_sql, 17, msg)
    
    # Registrar como Ocorrencia para aparecer na Contabilidade da Secretaria 17
    from ..models.schema import Ocorrencia, StatusOcorrencia
    from ..core.utils import generate_protocol
    
    protocolo = generate_protocol()
    ocorrencia = Ocorrencia(
        protocolo=protocolo,
        titulo="🚨 ALERTA DE BOTÃO DO PÂNICO",
        descricao=f"Ponto de referência: {ponto_ref}",
        rua=user.endereco,
        status=StatusOcorrencia.pendente,
        usuario_id=user.id,
        secretaria_id=17
    )
    db_sql.add(ocorrencia)
    
    import json
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="botao_panico",
        detalhes=json.dumps({"endereco": user.endereco, "ponto_referencia": ponto_ref})
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Alerta enviado com sucesso para a Guarda Municipal."}

@router.post("/add_user")
def add_panic_user(
    data: PanicAddUserRequest,
    current_admin = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    check_admin_permission(current_admin)
    
    user = db_sql.query(Usuario).filter(Usuario.cpf == data.cpf).first()
    
    if user:
        user.nome = data.nome
        user.telefone = data.telefone
        user.endereco = data.endereco
        user.botao_panico_autorizado = 1
    else:
        # Create new user
        from ..core.security import get_password_hash
        user = Usuario(
            nome=data.nome,
            cpf=data.cpf,
            telefone=data.telefone,
            whatsapp=data.telefone,
            endereco=data.endereco,
            email=f"{data.cpf}@panico.local", # placeholder email
            senha_hash=get_password_hash(data.cpf), # Default password is CPF
            botao_panico_autorizado=1
        )
        db_sql.add(user)
        db_sql.flush()
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=current_admin.tipo_usuario_verificado,
        acao="adicionar_panico",
        detalhes=f"Adicionou/Atualizou acesso ao Botão do Pânico para o usuário CPF {data.cpf}"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Cidadão adicionado e autorizado com sucesso."}

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
        
    # Restrição: apenas cidadãos do gênero feminino
    if not user.genero or user.genero.lower() != 'feminino':
        raise HTTPException(status_code=403, detail="O Botão do Pânico é exclusivo para cidadãos do gênero feminino.")
        
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
    
    return {"message": "Status atualizado com sucesso."}

@router.get("/alerts")
def get_panic_alerts(current_admin = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    check_admin_permission(current_admin)
    
    logs = db_sql.query(LogAuditoria).filter(LogAuditoria.acao == "botao_panico").order_by(LogAuditoria.data.desc()).limit(50).all()
    
    result = []
    for log in logs:
        user = db_sql.query(Usuario).filter(Usuario.id == log.usuario_id).first()
        if user:
            import json
            detalhes = {}
            try:
                detalhes = json.loads(log.detalhes)
            except:
                detalhes = {"endereco": user.endereco, "ponto_referencia": "Não informado"}
                
            result.append({
                "id": log.id,
                "data_hora": log.data.isoformat() if log.data else None,
                "nome": user.nome,
                "telefone": user.telefone,
                "endereco": detalhes.get("endereco", user.endereco),
                "ponto_referencia": detalhes.get("ponto_referencia", "Não informado")
            })
            
    return result
