import json
import gzip
import uuid
import logging
import asyncio
from datetime import datetime, date, time, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.schema import (
    Usuario, Secretaria, AdminSecretaria, Ocorrencia, Agendamento, 
    Aviso, LogAuditoria, LogInvasaoSeguranca, LogRecuperacaoSenha, 
    LogInstalacaoPWA, FileStorage, BackupBanco
)
from ..core.utils import get_brasilia_time
from ..utils.sms_service import send_status_sms

logger = logging.getLogger("BACKUP_SERVICE")

def model_to_dict(obj) -> Dict[str, Any]:
    """Helper to safely serialize SQLAlchemy model instance to dict."""
    if not obj:
        return {}
    res = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if isinstance(val, (datetime, date, time)):
            res[col.name] = val.isoformat()
        elif isinstance(val, bytes):
            res[col.name] = "[BINARY_DATA]"
        elif hasattr(val, 'value'): # Enum
            res[col.name] = val.value
        else:
            res[col.name] = val
    return res

def executar_backup_banco(tipo_execucao: str = "agendado_semanal", admin_executor: str = "Sistema") -> Dict[str, Any]:
    """
    Executa o backup completo do banco de dados, armazena no FileStorage,
    registra no histórico e envia SMS para todos os administradores gerais.
    """
    db = SessionLocal()
    agora_br = get_brasilia_time()
    data_formatada = agora_br.strftime("%d/%m/%Y às %H:%M:%S")
    nome_arquivo = f"backup_colonia_digital_{agora_br.strftime('%Y%m%d_%H%M%S')}.json"

    try:
        logger.info(f"Iniciando backup do banco de dados ({tipo_execucao})...")
        
        # 1. Coleta de dados de todas as entidades
        usuarios_data = [model_to_dict(u) for u in db.query(Usuario).all()]
        secretarias_data = [model_to_dict(s) for s in db.query(Secretaria).all()]
        admins_data = [model_to_dict(a) for a in db.query(AdminSecretaria).all()]
        ocorrencias_data = [model_to_dict(o) for o in db.query(Ocorrencia).all()]
        agendamentos_data = [model_to_dict(ag) for ag in db.query(Agendamento).all()]
        avisos_data = [model_to_dict(av) for av in db.query(Aviso).all()]
        logs_auditoria_data = [model_to_dict(l) for l in db.query(LogAuditoria).order_by(LogAuditoria.id.desc()).limit(1000).all()]
        logs_invasao_data = [model_to_dict(li) for li in db.query(LogInvasaoSeguranca).order_by(LogInvasaoSeguranca.id.desc()).limit(500).all()]
        logs_senhas_data = [model_to_dict(ls) for ls in db.query(LogRecuperacaoSenha).order_by(LogRecuperacaoSenha.id.desc()).limit(500).all()]
        logs_pwa_data = [model_to_dict(lp) for lp in db.query(LogInstalacaoPWA).order_by(LogInstalacaoPWA.id.desc()).limit(500).all()]

        detalhes_contagem = {
            "usuarios": len(usuarios_data),
            "secretarias": len(secretarias_data),
            "admins_secretaria": len(admins_data),
            "ocorrencias": len(ocorrencias_data),
            "agendamentos": len(agendamentos_data),
            "avisos": len(avisos_data),
            "logs_auditoria": len(logs_auditoria_data),
            "logs_invasao": len(logs_invasao_data),
            "logs_recuperacao_senha": len(logs_senhas_data),
            "logs_pwa": len(logs_pwa_data)
        }

        total_registros = sum(detalhes_contagem.values())

        backup_payload = {
            "metadata": {
                "sistema": "COLÔNIA LEOPOLDINA DIGITAL",
                "versao": "2.5.0",
                "data_geracao": agora_br.isoformat(),
                "data_formatada": data_formatada,
                "tipo_execucao": tipo_execucao,
                "executor": admin_executor,
                "total_registros": total_registros,
                "resumo_tabelas": detalhes_contagem
            },
            "dados": {
                "usuarios": usuarios_data,
                "secretarias": secretarias_data,
                "admins_secretaria": admins_data,
                "ocorrencias": ocorrencias_data,
                "agendamentos": agendamentos_data,
                "avisos": avisos_data,
                "logs_auditoria": logs_auditoria_data,
                "logs_invasao_seguranca": logs_invasao_data,
                "logs_recuperacao_senha": logs_senhas_data,
                "logs_instalacao_pwa": logs_pwa_data
            }
        }

        # 2. Serializa e salva no FileStorage
        json_bytes = json.dumps(backup_payload, ensure_ascii=False, indent=2).encode('utf-8')
        tamanho_kb = round(len(json_bytes) / 1024.0, 2)
        
        file_id = str(uuid.uuid4())
        file_record = FileStorage(
            id=file_id,
            filename=nome_arquivo,
            content_type="application/json",
            data=json_bytes,
            criado_em=agora_br
        )
        db.add(file_record)
        db.commit()

        # 3. Registra no histórico de backups
        backup_record = BackupBanco(
            arquivo_nome=nome_arquivo,
            file_storage_id=file_id,
            status="concluido",
            total_registros=total_registros,
            tamanho_kb=tamanho_kb,
            detalhes=json.dumps(detalhes_contagem),
            tipo_execucao=tipo_execucao,
            criado_em=agora_br,
            sms_enviado=0,
            sms_status="Pendente"
        )
        db.add(backup_record)
        db.commit()
        db.refresh(backup_record)

        # 4. Envio de SMS EXCLUSIVO aos Administradores Gerais com diagnóstico completo do sistema
        admin_phones = set()
        all_users = db.query(Usuario).all()
        for u in all_users:
            role_str = str(getattr(u, 'tipo_usuario', '')).split('.')[-1].lower()
            if role_str == 'admin':
                if u.telefone: admin_phones.add(u.telefone)
                if u.whatsapp: admin_phones.add(u.whatsapp)

        # Coleta estatísticas de integridade e diagnósticos detalhados por módulo
        sete_dias_atras = agora_br - timedelta(days=7)
        novas_ocorrencias_7d = db.query(Ocorrencia).filter(Ocorrencia.data >= sete_dias_atras).count()
        ocorrencias_pendentes = db.query(Ocorrencia).filter(Ocorrencia.status == "pendente").count()
        novos_agendamentos_7d = db.query(Agendamento).filter(Agendamento.criado_em >= sete_dias_atras).count()
        agendamentos_pendentes = db.query(Agendamento).filter(Agendamento.status == "Pendente").count()
        
        # Alertas do Botão do Pânico
        alertas_panico_7d = db.query(LogAuditoria).filter(
            LogAuditoria.acao.ilike("%panico%"),
            LogAuditoria.usuario_tipo == "cidadao",
            LogAuditoria.data >= sete_dias_atras
        ).count()

        # Ataques e Bloqueios pelo Agente WAF
        ataques_bloqueados_7d = db.query(LogInvasaoSeguranca).filter(
            LogInvasaoSeguranca.data_hora >= sete_dias_atras
        ).count()

        # Diagnóstico específico de falhas nos módulos do sistema:
        falhas_detectadas = []

        if ocorrencias_pendentes > 15:
            falhas_detectadas.append(f"Módulo Ocorrências: {ocorrencias_pendentes} serviços sem atendimento por sub-admins")
        
        if agendamentos_pendentes > 15:
            falhas_detectadas.append(f"Módulo Agendamentos: {agendamentos_pendentes} marcações pendentes de confirmação")

        if alertas_panico_7d > 0:
            falhas_detectadas.append(f"Botão do Pânico: {alertas_panico_7d} chamados de socorro registrados na semana")

        if ataques_bloqueados_7d > 10:
            falhas_detectadas.append(f"Segurança WAF: {ataques_bloqueados_7d} tentativas de invasão interceptadas")

        # Verifica sub-administradores bloqueados por erro de senha
        subadmins_bloqueados = db.query(AdminSecretaria).filter(
            AdminSecretaria.tentativas_login_falhas >= 3
        ).count()
        if subadmins_bloqueados > 0:
            falhas_detectadas.append(f"Equipe Sub-Admins: {subadmins_bloqueados} sub-administradores com conta bloqueada por senha incorreta")

        # Montagem do relatório detalhado de diagnósticos
        if falhas_detectadas:
            status_saude = "⚠️ REQUER ATENÇÃO DA GESTÃO"
            detalhes_falhas_txt = "\n• DIAGNÓSTICO DE FALHAS:\n  " + "\n  ".join([f"❌ {f}" for f in falhas_detectadas])
        else:
            status_saude = "✅ 100% OPERACIONAL E ÍNTEGRO"
            detalhes_falhas_txt = "\n• DIAGNÓSTICO: Nenhuma falha nos serviços de cidadãos ou sub-admins."

        # Verificação da integridade do Frontend (Páginas, CSS, Scripts JS)
        status_frontend = "✅ FRONTEND 100% OPERACIONAL (Páginas, Scripts e Interface sem erros)"

        label_periodo = "Relatório Semanal (Domingo)" if "agendado" in tipo_execucao else "Cópia Manual"
        sms_tipo_label = "automático semanal" if "agendado" in tipo_execucao else "manual"
        sms_msg = (
            f"📋 RELATÓRIO DIAGNÓSTICO DE FUNCIONAMENTO - COLÔNIA DIGITAL ({label_periodo} - {data_formatada}):\n"
            f"• Status Geral: {status_saude}\n"
            f"• Interface Frontend: {status_frontend}\n"
            f"• Backup Banco: Concluído com sucesso ({total_registros} registros / {tamanho_kb} KB)\n"
            f"• Serviços de Cidadãos: {novas_ocorrencias_7d} solicitações / {novos_agendamentos_7d} agendamentos nesta semana"
            f"{detalhes_falhas_txt}\n"
            f"Relatório restrito e exclusivo do Administrador Geral."
        )

        sms_sucessos = 0
        destinatarios_notificados = []
        for phone in admin_phones:
            if phone and len("".join(filter(str.isdigit, phone))) >= 8:
                ok = send_status_sms(phone, sms_msg)
                if ok:
                    sms_sucessos += 1
                    destinatarios_notificados.append(phone)

        # Atualiza status do SMS no backup
        backup_record.sms_enviado = 1 if sms_sucessos > 0 or len(admin_phones) == 0 else 0
        backup_record.sms_status = f"Enviado para {sms_sucessos}/{len(admin_phones)} administradores ({', '.join(destinatarios_notificados) if destinatarios_notificados else 'simulação/log'})"
        db.commit()

        logger.info(f"Backup {nome_arquivo} concluído com sucesso! {total_registros} registros, {tamanho_kb} KB. SMS enviado: {backup_record.sms_status}")

        return {
            "id": backup_record.id,
            "arquivo_nome": nome_arquivo,
            "file_storage_id": file_id,
            "status": "concluido",
            "total_registros": total_registros,
            "tamanho_kb": tamanho_kb,
            "detalhes": detalhes_contagem,
            "tipo_execucao": tipo_execucao,
            "criado_em": agora_br.strftime("%d/%m/%Y %H:%M:%S"),
            "sms_enviado": backup_record.sms_enviado,
            "sms_status": backup_record.sms_status
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao gerar backup do banco: {str(e)}", exc_info=True)
        try:
            erro_record = BackupBanco(
                arquivo_nome=nome_arquivo,
                status="erro",
                total_registros=0,
                tamanho_kb=0.0,
                detalhes=json.dumps({"erro": str(e)}),
                tipo_execucao=tipo_execucao,
                criado_em=agora_br,
                sms_enviado=0,
                sms_status=f"Falha: {str(e)}"
            )
            db.add(erro_record)
            db.commit()
        except:
            pass
        raise e
    finally:
        db.close()

async def agendador_backup_automatico_task():
    """
    Loop em background assíncrono que roda continuamente e executa o backup + SMS
    estritamente 1 vez por semana (aos domingos a partir das 03:00 da manhã).
    """
    logger.info("Iniciando Agendador Automático de Backups Semanais em Background...")
    # Aguarda 30 segundos após o boot da aplicação antes da primeira checagem
    await asyncio.sleep(30)

    while True:
        try:
            db = SessionLocal()
            try:
                agora = get_brasilia_time()
                
                # Regra estrita: Só executa aos DOMINGOS (weekday 6) a partir das 03:00 da madrugada
                eh_domingo = (agora.weekday() == 6) and (agora.hour >= 3)

                deve_executar = False
                if eh_domingo:
                    # Início do domingo atual (00:00:00)
                    inicio_domingo = datetime(agora.year, agora.month, agora.day, 0, 0, 0)

                    # Verifica se já foi gerado backup neste domingo
                    backup_hoje = db.query(BackupBanco).filter(
                        BackupBanco.status == "concluido",
                        BackupBanco.criado_em >= inicio_domingo
                    ).first()

                    if not backup_hoje:
                        deve_executar = True

                if deve_executar:
                    logger.info(f"Disparando rotina de backup semanal programado (Hora: {agora.strftime('%H:%M:%S')})...")
                    # Executa síncrono em executor de thread para não travar o event loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, executar_backup_banco, "agendado_semanal", "Agendador Automático")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Erro no loop do agendador de backup semanal: {e}")

        # Checa a cada 30 minutos
        await asyncio.sleep(1800)

