from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models.schema import Ocorrencia, Agendamento, Usuario, StatusUsuario, StatusOcorrencia
from ..core.auth_deps import get_current_admin, get_general_admin
from datetime import timedelta
from ..core.utils import get_brasilia_time

router = APIRouter()

@router.get("/summary")
def get_admin_summary(current_user = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    role = current_user.tipo_usuario_verificado
    sec_id = current_user.secretaria_id
    
    # Base queries
    q_ocorrencias = db_sql.query(Ocorrencia)
    q_agendamentos = db_sql.query(Agendamento)
    
    if role == "subadmin" and sec_id:
        q_ocorrencias = q_ocorrencias.filter(Ocorrencia.secretaria_id == sec_id)
        q_agendamentos = q_agendamentos.filter(Agendamento.secretaria_id == sec_id)
    
    # Totals
    total_ocorrencias = q_ocorrencias.count()
    pendentes_ocorrencias = q_ocorrencias.filter(Ocorrencia.status == StatusOcorrencia.pendente).count()
    resolvidas_ocorrencias = q_ocorrencias.filter(Ocorrencia.status == StatusOcorrencia.resolvido).count()
    
    total_agendamentos = q_agendamentos.count()
    pendentes_agendamentos = q_agendamentos.filter(Agendamento.status == "Pendente").count()
    confirmados_agendamentos = q_agendamentos.filter(Agendamento.status == "Confirmado").count()
    
    # User metrics (Admin only or limited for subadmin?)
    # Requirement: General Admin has full dashboard, Subadmin has intermediate.
    # We'll share some basic user counts if beneficial.
    users_stats = {}
    if role == "admin":
        users_stats = {
            "total_usuarios": db_sql.query(Usuario).count(),
            "usuarios_pendentes": db_sql.query(Usuario).filter(Usuario.status == StatusUsuario.pendente).count()
        }
    
    return {
        "ocorrencias": {
            "total": total_ocorrencias,
            "pendentes": pendentes_ocorrencias,
            "resolvidas": resolvidas_ocorrencias
        },
        "agendamentos": {
            "total": total_agendamentos,
            "pendentes": pendentes_agendamentos,
            "confirmados": confirmados_agendamentos
        },
        "usuarios": users_stats
    }

@router.get("/logs")
def get_audit_logs(limit: int = 50, current_user = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    from ..models.schema import LogAuditoria
    logs = db_sql.query(LogAuditoria).order_by(LogAuditoria.data.desc()).limit(limit).all()
    return logs


@router.get("/secretaria-breakdown")
def get_secretaria_breakdown(current_user = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    from ..models.schema import Secretaria
    secretarias = db_sql.query(Secretaria).all()
    
    results = []
    for s in secretarias:
        results.append({
            "nome": s.nome,
            "ocorrencias": db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == s.id).count(),
            "agendamentos": db_sql.query(Agendamento).filter(Agendamento.secretaria_id == s.id).count()
        })
    return results

@router.get("/chart-data")
def get_chart_data(current_user = Depends(get_current_admin), db_sql: Session = Depends(get_db)):

    # Simple last 7 days metrics
    today = get_brasilia_time().replace(tzinfo=None)
    last_week = today - timedelta(days=7)
    
    sec_id = current_user.secretaria_id
    
    q = db_sql.query(
        func.date(Ocorrencia.data).label('day'),
        func.count(Ocorrencia.id).label('count')
    ).filter(Ocorrencia.data >= last_week)
    
    if sec_id:
        q = q.filter(Ocorrencia.secretaria_id == sec_id)
    
    data = q.group_by(func.date(Ocorrencia.data)).order_by(func.date(Ocorrencia.data)).all()
    
    return [{"day": str(d.day), "count": d.count} for d in data]

@router.post("/reset-system")
def reset_system(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Zera todos os dados operacionais do sistema. Mantém usuários, admins e secretarias."""
    from ..models.schema import Resposta, Ocorrencia, Agendamento, ChatIA, LogAuditoria
    
    # Ordem importa por causa das foreign keys
    deleted_respostas = db_sql.query(Resposta).delete()
    deleted_ocorrencias = db_sql.query(Ocorrencia).delete()
    deleted_agendamentos = db_sql.query(Agendamento).delete()
    deleted_chat = db_sql.query(ChatIA).delete()
    deleted_logs = db_sql.query(LogAuditoria).delete()
    
    # Registrar que o reset aconteceu (novo log após limpar)
    log = LogAuditoria(
        usuario_id=current_admin.id,
        usuario_tipo="admin",
        acao="reset_system",
        detalhes=f"Sistema zerado: {deleted_ocorrencias} ocorrências, {deleted_agendamentos} agendamentos, {deleted_respostas} respostas, {deleted_chat} chats, {deleted_logs} logs removidos"
    )
    db_sql.add(log)
    db_sql.commit()
    
    return {
        "message": "Sistema zerado com sucesso!",
        "removidos": {
            "ocorrencias": deleted_ocorrencias,
            "agendamentos": deleted_agendamentos,
            "respostas": deleted_respostas,
            "chats": deleted_chat,
            "logs_auditoria": deleted_logs
        }
    }

@router.get("/secretaria-performance")
def get_secretaria_performance(current_admin = Depends(get_current_admin), db_sql: Session = Depends(get_db)):
    """Contabilidade em tempo real de todos os serviços de cada secretaria."""
    from ..models.schema import Secretaria, Agendamento
    
    secretarias = db_sql.query(Secretaria).all()
    
    results = []
    for s in secretarias:
        # Ocorrências por status
        oc_total = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == s.id).count()
        oc_pendentes = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == s.id, Ocorrencia.status == "pendente").count()
        oc_em_atendimento = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == s.id, Ocorrencia.status == "em_atendimento").count()
        oc_resolvidas = db_sql.query(Ocorrencia).filter(Ocorrencia.secretaria_id == s.id, Ocorrencia.status == "resolvido").count()
        
        # Agendamentos por status
        ag_total = db_sql.query(Agendamento).filter(Agendamento.secretaria_id == s.id).count()
        ag_pendentes = db_sql.query(Agendamento).filter(Agendamento.secretaria_id == s.id, Agendamento.status == "Pendente").count()
        ag_confirmados = db_sql.query(Agendamento).filter(Agendamento.secretaria_id == s.id, Agendamento.status == "Confirmado").count()
        ag_cancelados = db_sql.query(Agendamento).filter(Agendamento.secretaria_id == s.id, Agendamento.status == "Cancelado").count()
        
        # Taxa de resolução
        taxa_resolucao = round((oc_resolvidas / oc_total * 100), 1) if oc_total > 0 else 0
        
        results.append({
            "id": s.id,
            "nome": s.nome,
            "ocorrencias": {
                "total": oc_total,
                "pendentes": oc_pendentes,
                "em_atendimento": oc_em_atendimento,
                "resolvidas": oc_resolvidas,
                "taxa_resolucao": taxa_resolucao
            },
            "agendamentos": {
                "total": ag_total,
                "pendentes": ag_pendentes,
                "confirmados": ag_confirmados,
                "cancelados": ag_cancelados
            },
            "total_servicos": oc_total + ag_total
        })
    
    # Ordenar pela secretaria com mais serviços
    results.sort(key=lambda x: x["total_servicos"], reverse=True)
    
    return results
