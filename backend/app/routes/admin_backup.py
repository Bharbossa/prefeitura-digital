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
    Retorna o histórico diário de backups do banco de dados para o relatório do Administrador Geral.
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

    return {
        "total_backups": total_backups,
        "ultimo_backup": ultimo_dict,
        "agendamento_automatico": "Ativo (Diariamente às 03:00 da madrugada)",
        "notificacao_sms": "Ativa (Enviada a todos os Administradores Gerais)"
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
