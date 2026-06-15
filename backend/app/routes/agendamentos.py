from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from ..database import get_db
from ..models.schema import Usuario, AdminSecretaria, Agendamento, LogAuditoria, Secretaria, FileStorage
import io
from ..models.pydantic_schemas import AgendamentoCreate, AgendamentoResponse
from ..core.auth_deps import get_current_user, get_current_admin, get_general_admin
from ..utils.sms_service import send_status_sms, get_confirmed_message
from ..utils.notification_helper import notify_admins_of_new_record
from ..core.utils import generate_protocol, get_brasilia_time, generate_ticket_number
from sqlalchemy.orm import joinedload

router = APIRouter()

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_upload_file(upload_file: UploadFile, db_sql: Session) -> str:
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.txt', '.heic', '.heif'}
    file_ext = os.path.splitext(upload_file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Extensão de arquivo '{file_ext}' não permitida.")
        
    file_id = str(uuid.uuid4())
    content = upload_file.file.read()
    
    # Compress images to save space in the DB
    if file_ext in {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            # Resize if too large
            img.thumbnail((1200, 1200))
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=75)
            content = output.getvalue()
            file_ext = ".jpg" # Force jpg
            upload_file.content_type = "image/jpeg"
        except ImportError:
            pass # Pillow not installed, save as is
        except Exception:
            pass # Failed to compress, save as is
            
    content_type = upload_file.content_type or "application/octet-stream"
    
    new_file = FileStorage(
        id=file_id,
        filename=f"{file_id}{file_ext}",
        content_type=content_type,
        data=content
    )
    db_sql.add(new_file)
    db_sql.commit()
    
    # Return relative path for frontend
    return f"api/files/{file_id}"

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
        # Remove qualquer sufixo de timezone para preservar o horário exato escolhido pelo usuário
        import re
        clean_data_hora = re.sub(r'[Zz]$|[+-]\d{2}:\d{2}$', '', data_hora.strip())
        data_obj = datetime.fromisoformat(clean_data_hora)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use ISO 8601.")
        
    # Limite de 5 viagens por dia
    data_escolhida = data_obj.date()
    count = db_sql.query(Agendamento).filter(
        Agendamento.tipo == tipo,
        func.date(Agendamento.data_hora) == data_escolhida
    ).count()
    
    if count >= 5:
        raise HTTPException(status_code=400, detail="Limite diário de 5 viagens atingido para esta data.")

        
    arquivo_path = save_upload_file(comprovante, db_sql) if comprovante else None
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
    cidadao_rg: Optional[UploadFile] = File(None),
    cidadao_cpf: Optional[UploadFile] = File(None),
    cidadao_titulo: Optional[UploadFile] = File(None),
    parceiro_rg_foto: Optional[UploadFile] = File(None),
    parceiro_cpf_foto: Optional[UploadFile] = File(None),
    parceiro_titulo_foto: Optional[UploadFile] = File(None),
    current_user = Depends(get_current_user),
    db_sql: Session = Depends(get_db)
):
    if getattr(current_user, "tipo_usuario_verificado", "") != "cidadao":
        raise HTTPException(status_code=403, detail="Apenas cidadãos podem criar inscrições pelo perfil.")

    # Restrição de casal único no Concurso Pé de Aço
    if assunto and "Pé de Aço" in assunto:
        if not cidadao_rg or not cidadao_rg.filename or not cidadao_cpf or not cidadao_cpf.filename or not cidadao_titulo or not cidadao_titulo.filename:
            raise HTTPException(status_code=400, detail="O envio do seu RG, CPF e Título é obrigatório para a inscrição no Pé de Aço.")
        if not parceiro_rg_foto or not parceiro_rg_foto.filename or not parceiro_cpf_foto or not parceiro_cpf_foto.filename or not parceiro_titulo_foto or not parceiro_titulo_foto.filename:
            raise HTTPException(status_code=400, detail="O envio do RG, CPF e Título do seu parceiro(a) é obrigatório para a inscrição no Pé de Aço.")
        
        import re
        def clean_cpf(c: str) -> str:
            if not c:
                return ""
            return "".join([char for char in c if char.isdigit()])

        cidadao_cpf_str = clean_cpf(current_user.cpf)
        
        parceiro_cpf = ""
        if motivo:
            match_p = re.search(r'CPF Parceiro\(a\):\s*([0-9.-]+)', motivo)
            if match_p:
                parceiro_cpf = clean_cpf(match_p.group(1))

        # Buscar todas as inscrições ativas (não canceladas) no Concurso Pé de Aço
        from app.models.schema import Usuario
        concursos_ativos = db_sql.query(Agendamento).join(Usuario).filter(
            Agendamento.tipo == "Concurso",
            Agendamento.assunto.like("%Pé de Aço%"),
            Agendamento.status != "Cancelado"
        ).all()

        if len(concursos_ativos) >= 50:
            raise HTTPException(
                status_code=400,
                detail="LIMITE DE INSCRIÇÕES JÁ FEITAS!"
            )

        for c_ativo in concursos_ativos:
            c_cidadao_cpf = clean_cpf(c_ativo.usuario.cpf if c_ativo.usuario else "")
            
            c_parceiro_cpf = ""
            if c_ativo.motivo:
                match_c = re.search(r'CPF Parceiro\(a\):\s*([0-9.-]+)', c_ativo.motivo)
                if match_c:
                    c_parceiro_cpf = clean_cpf(match_c.group(1))

            # Valida duplicidade do CPF do cidadão solicitante
            if cidadao_cpf_str and (cidadao_cpf_str == c_cidadao_cpf or cidadao_cpf_str == c_parceiro_cpf):
                raise HTTPException(
                    status_code=400, 
                    detail="Seu CPF já está inscrito no concurso Pé de Aço (como candidato ou parceiro)."
                )

            # Valida duplicidade do CPF do parceiro
            if parceiro_cpf and (parceiro_cpf == c_cidadao_cpf or parceiro_cpf == c_parceiro_cpf):
                raise HTTPException(
                    status_code=400, 
                    detail="O CPF do seu parceiro já está inscrito no concurso Pé de Aço com outra pessoa."
                )

    # Gerar número de inscrição sequencial crescente (INS-0001, INS-0002, etc.)
    count = db_sql.query(Agendamento).filter(Agendamento.tipo == "Concurso").count()
    senha = f"INS-{count + 1:04d}"

    # Salvar arquivos se existirem
    anexos = []
    if foto and foto.filename:
        anexos.append(save_upload_file(foto, db_sql))
    if pdf and pdf.filename:
        anexos.append(save_upload_file(pdf, db_sql))
        
    if cidadao_rg and cidadao_rg.filename:
        anexos.append(save_upload_file(cidadao_rg, db_sql))
    if cidadao_cpf and cidadao_cpf.filename:
        anexos.append(save_upload_file(cidadao_cpf, db_sql))
    if cidadao_titulo and cidadao_titulo.filename:
        anexos.append(save_upload_file(cidadao_titulo, db_sql))
        
    if parceiro_rg_foto and parceiro_rg_foto.filename:
        anexos.append(save_upload_file(parceiro_rg_foto, db_sql))
    if parceiro_cpf_foto and parceiro_cpf_foto.filename:
        anexos.append(save_upload_file(parceiro_cpf_foto, db_sql))
    if parceiro_titulo_foto and parceiro_titulo_foto.filename:
        anexos.append(save_upload_file(parceiro_titulo_foto, db_sql))
    
    anexo_str = ",".join(anexos) if anexos else None

    protocolo = generate_protocol()
    data_hora_atual = get_brasilia_time()

    # SAFEGUARD: Forçar concursos para a Secretaria de Cultura e Esporte
    cultura_sec = db_sql.query(Secretaria).filter(
        func.upper(Secretaria.nome).like('%CULTURA%ESPORTE%')
    ).first()
    if cultura_sec:
        secretaria_id = cultura_sec.id
    
    novo_agendamento = Agendamento(
        protocolo=protocolo,
        senha=senha,
        usuario_id=current_user.id,
        secretaria_id=secretaria_id,
        tipo=tipo,
        assunto=assunto[:200] if assunto else "",
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
    novo_agendamento.usuario_endereco = getattr(current_user, 'endereco', "")
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

    # Populate usuario_nome and usuario_endereco for response
    for r in results:
        r.usuario_nome = r.usuario.nome if r.usuario else f"Cidadão #{r.usuario_id}"
        r.usuario_endereco = r.usuario.endereco if r.usuario else ""
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
    agend.usuario_endereco = agend.usuario.endereco if agend.usuario else ""
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

    path = save_upload_file(arquivo, db_sql)
    
    docs = load_concursos_docs()
    if concurso not in docs:
        docs[concurso] = {"regulamento": "", "termo": ""}
    docs[concurso][tipo_documento] = path.replace("\\", "/")
    
    save_concursos_docs(docs)
    
    return {"message": "Documento atualizado com sucesso!", "path": path}

@router.delete("/{agendamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_agendamento(agendamento_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Deleta um agendamento ou inscrição no concurso. Apenas o administrador geral."""
    from app.models.schema import LogAuditoria
    
    ag = db_sql.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
    if not ag:
        raise HTTPException(status_code=404, detail="Agendamento/Inscrição não encontrado.")
    
    protocolo = ag.protocolo
    tipo = ag.tipo
    
    db_sql.delete(ag)
    
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo="admin",
        acao="delete_agendamento",
        detalhes=f"Deletado {tipo} protocolo {protocolo}"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
