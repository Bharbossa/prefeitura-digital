import json
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.schema import BackupBanco, FileStorage, LogAuditoria
from ..core.auth_deps import get_general_admin
from ..services.backup_service import executar_backup_banco
from ..core.utils import get_brasilia_time

router = APIRouter(prefix="/admin/backups", tags=["Admin Backups"])

@router.get("")
def listar_backups(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """
    Retorna o histórico semanal de backups do banco de dados para o relatório do Administrador Geral.
    """
    backups = db_sql.query(BackupBanco).order_by(BackupBanco.id.desc()).limit(100).all()
    resultado = []
    for b in backups:
        detalhes_dict = {}
        if b.detalhes:
            try:
                detalhes_dict = json.loads(b.detalhes)
            except:
                detalhes_dict = {"detalhes": b.detalhes}

        resultado.append({
            "id": b.id,
            "arquivo_nome": b.arquivo_nome,
            "file_storage_id": b.file_storage_id,
            "status": b.status,
            "total_registros": b.total_registros,
            "tamanho_kb": b.tamanho_kb,
            "detalhes": detalhes_dict,
            "sms_enviado": b.sms_enviado,
            "sms_status": b.sms_status,
            "tipo_execucao": b.tipo_execucao,
            "criado_em": b.criado_em.strftime("%d/%m/%Y às %H:%M:%S") if b.criado_em else ""
        })
    return resultado

@router.get("/estatisticas")
def obter_estatisticas_backup(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """
    Retorna resumo para os cards de status do relatório de backup.
    """
    total_backups = db_sql.query(BackupBanco).count()
    ultimo_backup = db_sql.query(BackupBanco).order_by(BackupBanco.id.desc()).first()
    
    ultimo_dict = None
    if ultimo_backup:
        detalhes_dict = {}
        if ultimo_backup.detalhes:
            try:
                detalhes_dict = json.loads(ultimo_backup.detalhes)
            except:
                pass
        ultimo_dict = {
            "id": ultimo_backup.id,
            "data": ultimo_backup.criado_em.strftime("%d/%m/%Y às %H:%M:%S") if ultimo_backup.criado_em else "Nenhum",
            "status": ultimo_backup.status,
            "total_registros": ultimo_backup.total_registros,
            "tamanho_kb": ultimo_backup.tamanho_kb,
            "sms_enviado": ultimo_backup.sms_enviado,
            "sms_status": ultimo_backup.sms_status,
            "tipo": ultimo_backup.tipo_execucao,
            "detalhes": detalhes_dict
        }

    from datetime import timedelta
    from ..models.schema import Ocorrencia, Agendamento, LogAuditoria, LogInvasaoSeguranca, AdminSecretaria, Usuario, Secretaria, Aviso
    from ..core.utils import get_brasilia_time

    agora = get_brasilia_time()
    sete_dias = agora - timedelta(days=7)

    # 1. Módulo Gestão de Cidadãos
    total_cidadaos = db_sql.query(Usuario).count()
    novos_cidadaos_7d = db_sql.query(Usuario).filter(Usuario.last_login >= sete_dias).count()
    cidadaos_bloqueados = db_sql.query(Usuario).filter(Usuario.tentativas_login_falhas >= 3).count()

    # 2. Módulo de Ocorrências & Solicitações dos Cidadãos
    total_ocorrencias = db_sql.query(Ocorrencia).count()
    novas_ocorrencias_7d = db_sql.query(Ocorrencia).filter(Ocorrencia.data >= sete_dias).count()
    ocorrencias_pendentes = db_sql.query(Ocorrencia).filter(Ocorrencia.status == "pendente").count()
    ocorrencias_resolvidas = db_sql.query(Ocorrencia).filter(Ocorrencia.status == "resolvido").count()

    # 3. Módulo de Agendamentos (Bolsa Família, Consultas, Garagem)
    total_agendamentos = db_sql.query(Agendamento).count()
    novos_agendamentos_7d = db_sql.query(Agendamento).filter(Agendamento.criado_em >= sete_dias).count()
    agendamentos_pendentes = db_sql.query(Agendamento).filter(Agendamento.status == "Pendente").count()
    agendamentos_confirmados = db_sql.query(Agendamento).filter(Agendamento.status == "Confirmado").count()

    # 4. Módulo Botão do Pânico (Socorro & Patrulha Maria da Penha)
    total_autorizados_panico = db_sql.query(Usuario).filter(Usuario.botao_panico_autorizado == 1).count()
    solicitacoes_panico_pendentes = db_sql.query(Usuario).filter(Usuario.botao_panico_autorizado == 2).count()
    alertas_panico_7d = db_sql.query(LogAuditoria).filter(
        LogAuditoria.acao.ilike("%panico%"),
        LogAuditoria.usuario_tipo == "cidadao",
        LogAuditoria.data >= sete_dias
    ).count()

    # 5. Módulo Equipe de Sub-Administradores & Secretarias
    total_secretarias = db_sql.query(Secretaria).count()
    total_subadmins = db_sql.query(AdminSecretaria).count()
    subadmins_bloqueados = db_sql.query(AdminSecretaria).filter(
        AdminSecretaria.tentativas_login_falhas >= 3
    ).count()

    # 6. Monitor de Segurança, WAF e Auditoria
    ataques_bloqueados_7d = db_sql.query(LogInvasaoSeguranca).filter(
        LogInvasaoSeguranca.data_hora >= sete_dias
    ).count()
    logs_auditoria_7d = db_sql.query(LogAuditoria).filter(LogAuditoria.data >= sete_dias).count()

    # Varredura minuciosa por erros/falhas no sistema:
    falhas_lista = []
    if ocorrencias_pendentes > 10:
        falhas_lista.append({"modulo": "Ocorrências de Cidadãos", "descricao": f"{ocorrencias_pendentes} solicitações aguardando resposta das secretarias."})
    if agendamentos_pendentes > 10:
        falhas_lista.append({"modulo": "Agendamentos Presenciais", "descricao": f"{agendamentos_pendentes} agendamentos pendentes de confirmação."})
    if solicitacoes_panico_pendentes > 0:
        falhas_lista.append({"modulo": "Botão do Pânico (Análise)", "descricao": f"{solicitacoes_panico_pendentes} munícipes aguardando autorização de acesso da Guarda Municipal."})
    if alertas_panico_7d > 0:
        falhas_lista.append({"modulo": "Botão do Pânico (Disparos)", "descricao": f"{alertas_panico_7d} alertas de emergência/socorro acionados nesta semana."})
    if subadmins_bloqueados > 0:
        falhas_lista.append({"modulo": "Equipe de Sub-Admins", "descricao": f"{subadmins_bloqueados} sub-administradores com acesso bloqueado por erros de senha."})
    if cidadaos_bloqueados > 0:
        falhas_lista.append({"modulo": "Gestão de Cidadãos", "descricao": f"{cidadaos_bloqueados} contas de cidadãos temporariamente bloqueadas por tentativas de login."})
    if ataques_bloqueados_7d > 5:
        falhas_lista.append({"modulo": "Segurança WAF & Firewall", "descricao": f"{ataques_bloqueados_7d} tentativas de invasão interceptadas pelo agente de segurança."})

    status_sistema = "⚠️ REQUER ATENÇÃO DA GESTÃO" if falhas_lista else "✅ 100% OPERACIONAL E ÍNTEGRO"

    return {
        "total_backups": total_backups,
        "ultimo_backup": ultimo_dict,
        "agendamento_automatico": "Ativo (Semanalmente aos domingos às 03:00 da madrugada)",
        "notificacao_sms": "Ativa (Enviada exclusivamente ao Administrador Geral)",
        "diagnostico_sistema": {
            "status_geral": status_sistema,
            "falhas_detectadas": falhas_lista,
            "metricas_modulos": {
                "cidadaos": {"total": total_cidadaos, "bloqueados": cidadaos_bloqueados},
                "ocorrencias": {"total": total_ocorrencias, "novas_7d": novas_ocorrencias_7d, "pendentes": ocorrencias_pendentes, "resolvidas": ocorrencias_resolvidas},
                "agendamentos": {"total": total_agendamentos, "novos_7d": novos_agendamentos_7d, "pendentes": agendamentos_pendentes, "confirmados": agendamentos_confirmados},
                "panico": {"autorizados": total_autorizados_panico, "pendentes_analise": solicitacoes_panico_pendentes, "alertas_7d": alertas_panico_7d},
                "subadmins": {"secretarias": total_secretarias, "total_subadmins": total_subadmins, "bloqueados": subadmins_bloqueados},
                "seguranca": {"ataques_bloqueados_7d": ataques_bloqueados_7d, "auditoria_7d": logs_auditoria_7d}
            }
        }
    }

@router.post("/executar")
def acionar_backup_manual(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """
    Aciona um backup imediato a partir do painel do Administrador Geral e envia SMS.
    """
    admin_nome = getattr(current_admin, "nome", "Administrador Geral")
    try:
        resultado = executar_backup_banco(tipo_execucao="manual", admin_executor=admin_nome)
        
        # Registra na auditoria
        log = LogAuditoria(
            usuario_id=current_admin.id,
            usuario_tipo="admin",
            acao="BACKUP_MANUAL_BANCO",
            detalhes=f"Backup manual executado com sucesso: {resultado['arquivo_nome']} ({resultado['total_registros']} registros, {resultado['tamanho_kb']} KB). SMS notificado.",
            data=get_brasilia_time()
        )
        db_sql.add(log)
        db_sql.commit()

        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar o backup: {str(e)}"
        )

@router.get("/{backup_id}/download")
def download_backup(backup_id: int, current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """
    Faz o download do arquivo JSON do backup.
    """
    backup = db_sql.query(BackupBanco).filter(BackupBanco.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup não encontrado.")

    if not backup.file_storage_id:
        raise HTTPException(status_code=404, detail="Arquivo de backup não encontrado no armazenamento.")

    file_record = db_sql.query(FileStorage).filter(FileStorage.id == backup.file_storage_id).first()
    if not file_record or not file_record.data:
        raise HTTPException(status_code=404, detail="Conteúdo do arquivo não localizado.")

    headers = {
        "Content-Disposition": f'attachment; filename="{backup.arquivo_nome}"',
        "Content-Type": "application/json; charset=utf-8"
    }

    return Response(content=file_record.data, media_type="application/json", headers=headers)
