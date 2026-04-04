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
