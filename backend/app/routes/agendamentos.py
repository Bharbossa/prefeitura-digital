from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, Agendamento, LogAuditoria, Secretaria
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
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.txt'}
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


@router.get("/concurso/camisas")
def obter_quantidade_camisas_concurso(
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    # Permissão: admin geral ou subadmin de cultura/esporte
    if current_user.tipo_usuario_verificado == "subadmin":
        if not current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Acesso restrito ao administrador de Cultura e Esporte.")
            
        sec = db_sql.query(Secretaria).filter(Secretaria.id == current_user.secretaria_id).first()
        if not sec or not ("CULTURA E ESPORTE" in sec.nome.upper()):
            raise HTTPException(status_code=403, detail="Apenas sub-administradores da Secretaria de Cultura e Esporte podem ver o resumo de camisas.")

    # Buscar todos agendamentos do tipo "Concurso" do "Pé de Aço"
    concursos = db_sql.query(Agendamento).filter(
        Agendamento.tipo == "Concurso",
        Agendamento.assunto.like("%Pé de Aço%")
    ).all()

    total_inscritos = len(concursos)
    # Filtrar ativos (status != "Cancelado") para contagem das camisas
    concursos_ativos = [c for c in concursos if c.status != "Cancelado"]
    total_ativos = len(concursos_ativos)

    inscritos_camisas = {"P": 0, "M": 0, "G": 0, "GG": 0}
    parceiros_camisas = {"P": 0, "M": 0, "G": 0, "GG": 0}

    import re
    for c in concursos_ativos:
        assunto = c.assunto or ""
        parts = [p.strip() for p in assunto.split("|")]
        participant_size = None
        partner_size = None
        
        for part in parts:
            if "Camisa Parceiro" in part or "Camisa do Parceiro" in part:
                match_val = re.search(r':\s*(P|M|G|GG)\b', part, re.IGNORECASE)
                if match_val:
                    partner_size = match_val.group(1).upper()
            elif "Camisa" in part:
                match_val = re.search(r':\s*(P|M|G|GG)\b', part, re.IGNORECASE)
                if match_val:
                    participant_size = match_val.group(1).upper()
        
        # Regex fallbacks
        if not participant_size:
            match = re.search(r'(?<!Parceiro\(a\))\bCamisa:\s*(P|M|G|GG)\b', assunto, re.IGNORECASE)
            if match:
                participant_size = match.group(1).upper()
        
        if not partner_size:
            match = re.search(r'Camisa\s+Parceiro\(?a?\)?:\s*(P|M|G|GG)\b', assunto, re.IGNORECASE)
            if match:
                partner_size = match.group(1).upper()

        if participant_size in inscritos_camisas:
            inscritos_camisas[participant_size] += 1
        if partner_size in parceiros_camisas:
            parceiros_camisas[partner_size] += 1

    return {
        "total_inscritos": total_inscritos,
        "total_ativos": total_ativos,
        "inscritos_camisas": inscritos_camisas,
        "parceiros_camisas": parceiros_camisas
    }


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


CONCURSOS_DOCS_JSON = "uploads/concursos_documentos.json"

def load_concursos_docs():
    import json
    if os.path.exists(CONCURSOS_DOCS_JSON):
        try:
            with open(CONCURSOS_DOCS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "Papa-Cuscuz": {
            "regulamento": "documentos/regras_papa_cuscuz.txt",
            "termo": ""
        },
        "Pé de Aço": {
            "regulamento": "documentos/regras_pe_de_aco.txt",
            "termo": ""
        }
    }

def save_concursos_docs(data):
    import json
    with open(CONCURSOS_DOCS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@router.get("/concursos/documentos")
def obter_documentos_concursos():
    return load_concursos_docs()

@router.post("/concursos/documentos")
def fazer_upload_documento_concurso(
    concurso: str = Form(...),
    tipo_documento: str = Form(...),
    arquivo: UploadFile = File(...),
    current_user = Depends(get_current_admin),
    db_sql: Session = Depends(get_db)
):
    if concurso not in ["Papa-Cuscuz", "Pé de Aço"]:
        raise HTTPException(status_code=400, detail="Concurso inválido.")
        
    if tipo_documento not in ["regulamento", "termo"]:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido.")
        
    if current_user.tipo_usuario_verificado == "subadmin":
        if not current_user.secretaria_id:
            raise HTTPException(status_code=403, detail="Acesso restrito ao administrador de Cultura e Esporte.")
            
        sec = db_sql.query(Secretaria).filter(Secretaria.id == current_user.secretaria_id).first()
        if not sec or not ("CULTURA E ESPORTE" in sec.nome.upper()):
            raise HTTPException(status_code=403, detail="Apenas sub-administradores da Secretaria de Cultura e Esporte podem atualizar documentos de concursos.")

    path = save_upload_file(arquivo)
    
    docs = load_concursos_docs()
    if concurso not in docs:
        docs[concurso] = {"regulamento": "", "termo": ""}
    docs[concurso][tipo_documento] = path.replace("\\", "/")
    
    save_concursos_docs(docs)
    
    return {"message": "Documento atualizado com sucesso!", "path": path}


