from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, Agendamento, LogAuditoria
from ..models.pydantic_schemas import AgendamentoCreate, AgendamentoResponse
from ..core.auth_deps import get_current_user, get_current_admin
from ..utils.sms_service import send_status_sms, get_confirmed_message
from ..utils.notification_helper import notify_admins_of_new_record
from ..core.utils import generate_protocol, get_brasilia_time, generate_ticket_number
from sqlalchemy.orm import joinedload

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_upload_file(upload_file: UploadFile) -> str:
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
    file_ext = os.path.splitext(upload_file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Extensão de arquivo '{file_ext}' não permitida.")
        
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

@router.post("", response_model=AgendamentoResponse)
def criar_agendamento(agend: AgendamentoCreate, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar agendamentos pelo perfil.")
    
    protocolo = generate_protocol()
    
    if agend.tipo == "Bolsa Família":
        # Limite de 15 senhas por dia para o Bolsa Família
        data_escolhida = agend.data_hora.date()
        count = db_sql.query(Agendamento).filter(
            Agendamento.tipo == "Bolsa Família",
            func.date(Agendamento.data_hora) == data_escolhida
        ).count()
        
        if count >= 15:
            raise HTTPException(status_code=400, detail="Limite diário de 15 agendamentos para Bolsa Família atingido para esta data.")
        
        senha = f"BF-{count + 1:02d}"
    else:
        senha = generate_ticket_number()

    
    novo_agendamento = Agendamento(
        protocolo=protocolo,
        senha=senha,
        usuario_id=current_user.id,
        secretaria_id=agend.secretaria_id,
        tipo=agend.tipo,
        assunto=agend.assunto,
        motivo=agend.motivo,
        acompanhante=agend.acompanhante,
        cartao_sus=agend.cartao_sus,
        data_hora=agend.data_hora.replace(tzinfo=None), # Preserva o horário escolhido
        criado_em=get_brasilia_time()
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)

    # Notificar administradores
    msg = f"COLÔNIA DIGITAL: Novo Agendamento ({protocolo}) solicitado. Senha: {senha}. Verifique o painel!"
    notify_admins_of_new_record(db_sql, agend.secretaria_id, msg)

    return novo_agendamento

@router.post("/viagem", response_model=AgendamentoResponse)
def criar_agendamento_viagem(
    secretaria_id: int = Form(...),
    tipo: str = Form(...),
    assunto: str = Form(...),
    motivo: Optional[str] = Form(None),
    acompanhante: Optional[str] = Form(None),
    data_hora: str = Form(...),
    comprovante: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)):
    
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar agendamentos pelo perfil.")
        
    try:
        # Tenta converter a string ISO para datetime
        data_obj = datetime.fromisoformat(data_hora.replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use ISO 8601.")
        
    arquivo_path = save_upload_file(comprovante) if comprovante else None
    protocolo = generate_protocol()
    senha = generate_ticket_number()

    novo_agendamento = Agendamento(
        protocolo=protocolo,
        senha=senha,
        usuario_id=current_user.id,
        secretaria_id=secretaria_id,
        tipo=tipo,
        assunto=assunto,
        motivo=motivo,
        acompanhante=acompanhante,
        data_hora=data_obj,
        cartao_sus=None, 
        anexo=arquivo_path,
        criado_em=get_brasilia_time()
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)

    # Notificar administradores
    msg = f"COLÔNIA DIGITAL: Novo Agendamento de Viagem ({protocolo}) solicitado. Senha: {senha}."
    notify_admins_of_new_record(db_sql, secretaria_id, msg)

    return novo_agendamento


@router.post("/concurso", response_model=AgendamentoResponse)
def criar_agendamento_concurso(
    secretaria_id: int = Form(...),
    tipo: str = Form(...),
    assunto: str = Form(...),
    motivo: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    pdf: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar inscrições pelo perfil.")

    # Gerar número de inscrição sequencial crescente (INS-0001, INS-0002, etc.)
    count = db_sql.query(Agendamento).filter(Agendamento.tipo == "Concurso").count()
    senha = f"INS-{count + 1:04d}"

    # Salvar arquivos se existirem
    anexos = []
    if foto and foto.filename:
        foto_path = save_upload_file(foto)
        anexos.append(foto_path)
    if pdf and pdf.filename:
        pdf_path = save_upload_file(pdf)
        anexos.append(pdf_path)
    
    anexo_str = ",".join(anexos) if anexos else None

    protocolo = generate_protocol()
    data_hora_atual = get_brasilia_time()

    novo_agendamento = Agendamento(
        protocolo=protocolo,
        senha=senha,
        usuario_id=current_user.id,
        secretaria_id=secretaria_id,
        tipo=tipo,
        assunto=assunto,
        motivo=motivo if motivo else "",
        data_hora=data_hora_atual,
        anexo=anexo_str,
        criado_em=data_hora_atual
    )
    db_sql.add(novo_agendamento)
    db_sql.commit()
    db_sql.refresh(novo_agendamento)

    # Notificar administradores
    msg = f"COLÔNIA DIGITAL: Nova Inscrição de Concurso ({protocolo}) solicitada. Inscrição: {senha}."
    notify_admins_of_new_record(db_sql, secretaria_id, msg)

    novo_agendamento.usuario_nome = current_user.nome
    return novo_agendamento


@router.get("", response_model=List[AgendamentoResponse])
def listar_meus_agendamentos(current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    role = current_user.tipo_usuario_verificado
    query = db_sql.query(Agendamento).options(joinedload(Agendamento.usuario))

    if role == "cidadao":
        results = query.filter(Agendamento.usuario_id == current_user.id).order_by(Agendamento.data_hora.desc()).all()
    elif role in ["admin", "subadmin"]:
        sec_id = current_user.secretaria_id
        if sec_id:
            results = query.filter(Agendamento.secretaria_id == sec_id).order_by(Agendamento.data_hora.desc()).all()
        else:
            # General Admin see all
            results = query.order_by(Agendamento.data_hora.desc()).all()
    else:
        raise HTTPException(status_code=403, detail="Não autorizado.")

    # Populate usuario_nome for response
    for r in results:
        r.usuario_nome = r.usuario.nome if r.usuario else f"Cidadão #{r.usuario_id}"
    return results

@router.get("/{agend_id}", response_model=AgendamentoResponse)
def obter_agendamento(agend_id: int, current_user = Depends(get_current_user), db_sql: Session = Depends(get_db)):
    agend = db_sql.query(Agendamento).options(joinedload(Agendamento.usuario)).filter(Agendamento.id == agend_id).first()
    if not agend:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    
    # Check access
    t_verificado = getattr(current_user, "tipo_usuario_verificado", "")
    if t_verificado == "cidadao" and agend.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    
    sec_id = getattr(current_user, "secretaria_id", None)
    if sec_id and agend.secretaria_id != sec_id:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    agend.usuario_nome = agend.usuario.nome if agend.usuario else f"Cidadão #{agend.usuario_id}"
    return agend

@router.patch("/{agend_id}/status")
def atualizar_status(agend_id: int, status: str, current_user = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    if status not in ["Confirmado", "Cancelado", "Pendente"]:
        raise HTTPException(status_code=400, detail="Status inválido.")
        
    agendamento = db_sql.query(Agendamento).filter(Agendamento.id == agend_id).first()
    if not agendamento:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado.")
    
    # Permission check for subadmin
    if current_user.tipo_usuario_verificado == "subadmin":
        if agendamento.secretaria_id != current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Agendamento pertence a outra secretaria.")
            
    old_status = agendamento.status
    agendamento.status = status
    
    if status == "Confirmado" and old_status != "Confirmado":
        if agendamento.usuario and agendamento.usuario.telefone:
            dt_str = agendamento.data_hora.strftime("%d/%m/%Y %H:%M")
            msg = get_confirmed_message(agendamento.assunto, dt_str)
            send_status_sms(agendamento.usuario.telefone, msg)
            
    db_sql.commit()
    db_sql.refresh(agendamento)
    return agendamento

