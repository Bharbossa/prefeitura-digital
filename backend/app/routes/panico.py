import json
from urllib.parse import quote
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.schema import Usuario, LogAuditoria, Secretaria, Ocorrencia, StatusOcorrencia
from ..core.auth_deps import get_current_user, get_current_admin
from ..core.utils import generate_protocol, get_brasilia_time
from ..utils.notification_helper import notify_admins_of_new_record
from ..utils.sms_service import notify_subadmins_background, notify_subadmins_voice_background

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
    latitude: Optional[float] = None
    longitude: Optional[float] = None

def check_admin_permission(admin):
    tipo = getattr(admin, "tipo_usuario_verificado", "") or getattr(admin, "tipo_usuario", "")
    tipo_str = str(tipo).split('.')[-1].lower()
    if tipo_str == "admin":
        return True
    
    allowed_emails = [
        "patrulhamariadapenha.gcm.clp@gmail.com",
        "guardamunicipalcolonia@gmail.com",
        "daniel.carlos16@hotmail.com",
        "wilsongleidson@hotmail.com",
        "gameprf88@gmail.com",
        "ezequias_fernandes@outlook.com.br"
    ]
    if tipo_str == "subadmin":
        admin_email = (getattr(admin, "email", "") or "").strip().lower()
        sec_id = getattr(admin, "secretaria_id", None)
        sec_nome = (getattr(admin, "secretaria_nome", "") or "").strip().lower()
        if (
            admin_email in [e.lower() for e in allowed_emails]
            or sec_id in [16, 17]
            or "mulher" in sec_nome
            or "guarda" in sec_nome
            or "patrulha" in sec_nome
            or "seguran" in sec_nome
        ):
            return True
        
    raise HTTPException(status_code=403, detail="Sem permissão para gerenciar o Botão do Pânico.")

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
    
    # Identifica o ID da secretaria da Guarda Municipal / Patrulha Maria da Penha
    sec_gcm = db_sql.query(Secretaria).filter(
        func.lower(Secretaria.nome).like("%guarda%") |
        func.lower(Secretaria.nome).like("%patrulha%") |
        func.lower(Secretaria.nome).like("%mulher%") |
        func.lower(Secretaria.nome).like("%seguran%")
    ).first()
    gcm_sec_id = sec_gcm.id if sec_gcm else 17

    if data.latitude and data.longitude:
        maps_link = f"https://maps.google.com/?q={data.latitude},{data.longitude}"
    else:
        maps_link = f"https://maps.google.com/?q={quote(user.endereco or 'Colonia Leopoldina AL')}"

    msg = f"🚨 ALERTA DE SOCORRO! 🚨\nO(A) {user.nome} acionou o Botão do Pânico!\nTel: {user.telefone}\nEndereço: {user.endereco}\nRef: {ponto_ref}\nLocalização: {maps_link}"
    
    # Notificações em background (SMS e Ligações de voz para Guarda Municipal e Admin Geral)
    background_tasks.add_task(notify_subadmins_background, gcm_sec_id, msg)
    
    msg_voice = "Atenção Guarda Municipal! Existe um novo Alerta de Socorro do Botão do Pânico pendente. Verifique o painel imediatamente."
    background_tasks.add_task(notify_subadmins_voice_background, gcm_sec_id, msg_voice)
    
    # Registrar como Ocorrencia para visualização nos relatórios e atendimento
    protocolo = generate_protocol()
    ocorrencia = Ocorrencia(
        protocolo=protocolo,
        titulo="🚨 ALERTA DE BOTÃO DO PÂNICO",
        descricao=f"Ponto de referência: {ponto_ref}\nLink GPS: {maps_link}",
        rua=user.endereco,
        latitude=data.latitude,
        longitude=data.longitude,
        status=StatusOcorrencia.pendente,
        usuario_id=user.id,
        secretaria_id=gcm_sec_id,
        data=get_brasilia_time()
    )
    db_sql.add(ocorrencia)
    
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="botao_panico",
        detalhes=json.dumps({
            "endereco": user.endereco,
            "ponto_referencia": ponto_ref,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "protocolo": protocolo
        }),
        data=get_brasilia_time()
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {
        "message": "Alerta enviado com sucesso para a Guarda Municipal.",
        "protocolo": protocolo
    }

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
        from ..core.security import get_password_hash
        user = Usuario(
            nome=data.nome,
            cpf=data.cpf,
            telefone=data.telefone,
            whatsapp=data.telefone,
            endereco=data.endereco,
            email=f"{data.cpf}@panico.local",
            senha_hash=get_password_hash(data.cpf),
            botao_panico_autorizado=1,
            genero="feminino"
        )
        db_sql.add(user)
        db_sql.flush()
    
    tipo_adm = getattr(current_admin, "tipo_usuario_verificado", "") or getattr(current_admin, "tipo_usuario", "admin")
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=str(tipo_adm).split('.')[-1],
        acao="adicionar_panico",
        detalhes=f"Adicionou/Atualizou acesso ao Botão do Pânico para o usuário CPF {data.cpf}",
        data=get_brasilia_time()
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
        
    user.botao_panico_autorizado = 2 # 2 = Pendente
    
    log = LogAuditoria(
        usuario_id=user.id,
        usuario_tipo="cidadao",
        acao="solicitar_panico",
        detalhes=f"Solicitou acesso ao Botão do Pânico",
        data=get_brasilia_time()
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Solicitação enviada com sucesso. Aguarde análise da Guarda Municipal."}

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
    tipo_adm = getattr(current_admin, "tipo_usuario_verificado", "") or getattr(current_admin, "tipo_usuario", "admin")
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo=str(tipo_adm).split('.')[-1],
        acao="autorizar_panico",
        detalhes=f"{action_str} acesso ao Botão do Pânico para o usuário ID {user.id}",
        data=get_brasilia_time()
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {"message": "Status atualizado com sucesso."}

@router.get("/alerts")
def get_panic_alerts(current_admin = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    check_admin_permission(current_admin)
    
    # 1. Busca em logs de auditoria
    logs = db_sql.query(LogAuditoria).filter(
        (LogAuditoria.acao.ilike("%panico%")) & (LogAuditoria.usuario_tipo == "cidadao")
    ).order_by(LogAuditoria.data.desc()).limit(100).all()
    
    result = []
    seen_keys = set()

    for log in logs:
        user = db_sql.query(Usuario).filter(Usuario.id == log.usuario_id).first()
        if user:
            detalhes = {}
            if log.detalhes:
                try:
                    detalhes = json.loads(log.detalhes)
                except:
                    detalhes = {"endereco": user.endereco, "ponto_referencia": log.detalhes}
            
            data_iso = log.data.isoformat() if log.data else ""
            data_fmt = log.data.strftime("%d/%m/%Y às %H:%M:%S") if log.data else "N/A"
            key = f"{user.id}_{log.data.strftime('%Y%m%d%H%M') if log.data else ''}"
            seen_keys.add(key)
            
            result.append({
                "id": log.id,
                "data_hora": data_fmt,
                "data_iso": data_iso,
                "nome": user.nome,
                "telefone": user.telefone,
                "endereco": detalhes.get("endereco", user.endereco),
                "ponto_referencia": detalhes.get("ponto_referencia", "Não informado"),
                "latitude": detalhes.get("latitude"),
                "longitude": detalhes.get("longitude"),
                "protocolo": detalhes.get("protocolo", "N/A")
            })

    # 2. Busca também em Ocorrências
    ocors = db_sql.query(Ocorrencia).filter(
        Ocorrencia.titulo.ilike("%pânico%") | Ocorrencia.titulo.ilike("%panico%") | Ocorrencia.titulo.ilike("%socorro%")
    ).order_by(Ocorrencia.data.desc()).limit(100).all()

    for oc in ocors:
        user = db_sql.query(Usuario).filter(Usuario.id == oc.usuario_id).first()
        if user:
            key = f"{user.id}_{oc.data.strftime('%Y%m%d%H%M') if oc.data else ''}"
            if key not in seen_keys:
                seen_keys.add(key)
                data_iso = oc.data.isoformat() if oc.data else ""
                data_fmt = oc.data.strftime("%d/%m/%Y às %H:%M:%S") if oc.data else "N/A"
                result.append({
                    "id": oc.id,
                    "data_hora": data_fmt,
                    "data_iso": data_iso,
                    "nome": user.nome,
                    "telefone": user.telefone,
                    "endereco": oc.rua or user.endereco,
                    "ponto_referencia": oc.descricao or "Não informado",
                    "latitude": oc.latitude,
                    "longitude": oc.longitude,
                    "protocolo": oc.protocolo or "N/A"
                })

    return result
