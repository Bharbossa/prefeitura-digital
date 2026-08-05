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
    sec_id = getattr(current_user, 'secretaria_id', None)
    
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
        
    # Ratings calculations
    # Avg from ocorrencias
    o_avg = q_ocorrencias.filter(Ocorrencia.avaliacao_nota != None).with_entities(func.avg(Ocorrencia.avaliacao_nota)).scalar()
    # Avg from agendamentos
    a_avg = q_agendamentos.filter(Agendamento.avaliacao_nota != None).with_entities(func.avg(Agendamento.avaliacao_nota)).scalar()
    
    o_avg = float(o_avg) if o_avg else 0.0
    a_avg = float(a_avg) if a_avg else 0.0
    
    if o_avg and a_avg:
        total_avg = (o_avg + a_avg) / 2.0
    else:
        total_avg = o_avg or a_avg or 0.0
    
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
        "usuarios": users_stats,
        "satisfacao": {
            "media_geral": round(total_avg, 1)
        }
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
    
    sec_id = getattr(current_user, 'secretaria_id', None)
    
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
        
        # Add Panic Button authorization requests to Secretaria da Mulher and Guarda Municipal
        nome_sec_upper = (s.nome or "").upper()
        if s.id in (16, 17) or "MULHER" in nome_sec_upper or "GUARDA MUNICIPAL" in nome_sec_upper:
            from ..models.schema import Usuario
            panico_pendentes = db_sql.query(Usuario).filter(Usuario.botao_panico_autorizado == 2).count()
            panico_resolvidas = db_sql.query(Usuario).filter(Usuario.botao_panico_autorizado == 1).count()
            
            oc_pendentes += panico_pendentes
            oc_resolvidas += panico_resolvidas
            oc_total += (panico_pendentes + panico_resolvidas)
        
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

@router.get("/heatmap")
def get_heatmap_data(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Retorna coordenadas das ocorrências para o mapa de calor."""
    from ..models.schema import Ocorrencia
    
    # Busca apenas ocorrências que tenham latitude e longitude
    ocorrencias = db_sql.query(Ocorrencia.latitude, Ocorrencia.longitude).filter(
        Ocorrencia.latitude.isnot(None), 
        Ocorrencia.longitude.isnot(None)
    ).all()
    
    return [{"lat": o.latitude, "lng": o.longitude, "weight": 1} for o in ocorrencias]

import re

def _title_case(s: str) -> str:
    if not s:
        return ""
    words = s.strip().split()
    lowercase_words = {'de', 'da', 'do', 'dos', 'das', 'e', 'em'}
    result = []
    for i, w in enumerate(words):
        w_lower = w.lower()
        if i > 0 and w_lower in lowercase_words:
            result.append(w_lower)
        else:
            result.append(w.capitalize())
    return " ".join(result)

def _parse_address(raw_address: str):
    if not raw_address or not raw_address.strip():
        return "Não Informado", "Não Informado"
    
    clean = raw_address.strip()
    parts = [p.strip() for p in re.split(r'[,/\-–—]', clean) if p.strip()]
    
    street_prefixes = (
        'rua', 'r.', 'r ', 'av', 'av.', 'avenida', 'praça', 'praca', 'pça', 
        'travessa', 'trv', 'trv.', 'alameda', 'alm.', 'rodovia', 'rod.', 
        'estrada', 'est.', 'loteamento', 'lot.', 'servidao', 'servidão', 'quadra', 'qd'
    )
    
    if len(parts) >= 2:
        p0, p1 = parts[0], parts[1]
        if any(p0.lower().startswith(pref) for pref in street_prefixes):
            rua = _title_case(p0)
            bairro = _title_case(p1)
        elif any(p1.lower().startswith(pref) for pref in street_prefixes):
            rua = _title_case(p1)
            bairro = _title_case(p0)
        else:
            rua = _title_case(p0)
            bairro = _title_case(p1)
        return bairro, rua
    
    single = _title_case(clean)
    if any(single.lower().startswith(pref) for pref in street_prefixes):
        return "Não Informado", single
    else:
        return single, single

def _get_all_users(db_sql: Session):
    """Retorna lista de dicionários com todos os campos cadastrais dos usuários (Firestore e SQL)."""
    from ..core.firebase_config import db, DB_MODE
    from ..models.schema import Usuario
    
    users = []
    seen_ids = set()
    
    # Busca usuários no Firestore se disponível
    if db is not None:
        try:
            docs = db.collection("usuarios").stream()
            for doc in docs:
                data = doc.to_dict()
                u_id = doc.id
                addr = data.get("endereco") or data.get("rua") or data.get("bairro") or ""
                seen_ids.add(str(u_id))
                users.append({
                    "id": str(u_id),
                    "nome": data.get("nome", "Não informado"),
                    "cpf": data.get("cpf", "Não informado"),
                    "email": data.get("email", "Não informado"),
                    "telefone": data.get("telefone", "Não informado"),
                    "whatsapp": data.get("whatsapp", "Não informado"),
                    "genero": data.get("genero", "Não informado"),
                    "endereco": addr
                })
        except Exception as e:
            pass
            
    # Busca usuários no SQL (MySQL/SQLite/PostgreSQL)
    try:
        sql_users = db_sql.query(Usuario).all()
        for u in sql_users:
            if str(u.id) not in seen_ids:
                seen_ids.add(str(u.id))
                users.append({
                    "id": str(u.id),
                    "nome": u.nome or "Não informado",
                    "cpf": u.cpf or "Não informado",
                    "email": u.email or "Não informado",
                    "telefone": u.telefone or "Não informado",
                    "whatsapp": u.whatsapp or "Não informado",
                    "genero": u.genero or "Não informado",
                    "endereco": u.endereco or ""
                })
    except Exception as e:
        pass
        
    return users

@router.get("/users-bairro")
def get_users_bairro(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Agrupa os usuários normalizando e contabilizando por Bairro e por Rua."""
    usuarios = _get_all_users(db_sql)
    
    bairros_count = {}
    ruas_count = {}
    
    for u in usuarios:
        bairro, rua = _parse_address(u["endereco"])
        
        if bairro:
            bairros_count[bairro] = bairros_count.get(bairro, 0) + 1
        if rua:
            ruas_count[rua] = ruas_count.get(rua, 0) + 1
        
    bairros_sorted = [
        {"endereco": k, "total": v}
        for k, v in sorted(bairros_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    ruas_items = sorted(ruas_count.items(), key=lambda x: x[1], reverse=True)
    ruas_sorted = [
        {"endereco": k, "total": v}
        for k, v in ruas_items if k != "Não Informado"
    ]
    if not ruas_sorted:
        ruas_sorted = [{"endereco": k, "total": v} for k, v in ruas_items]
    
    return {
        "bairros": bairros_sorted,
        "ruas": ruas_sorted
    }

@router.get("/users-heatmap")
def get_users_heatmap(current_admin = Depends(get_general_admin), db_sql: Session = Depends(get_db)):
    """Retorna dados de localização, mapa de calor e detalhes individuais de todos os cidadãos cadastrados."""
    from ..models.schema import Ocorrencia
    import hashlib
    
    usuarios = _get_all_users(db_sql)
    
    ocorrencias_user = []
    try:
        ocorrencias_user = db_sql.query(
            Ocorrencia.usuario_id, Ocorrencia.latitude, Ocorrencia.longitude
        ).filter(Ocorrencia.latitude.isnot(None), Ocorrencia.longitude.isnot(None)).all()
    except Exception:
        pass
    
    user_coords = {}
    for oc in ocorrencias_user:
        if oc.usuario_id and str(oc.usuario_id) not in user_coords:
            user_coords[str(oc.usuario_id)] = (oc.latitude, oc.longitude)
            
    base_coords = {
        # Real OpenStreetMap Nominatim Street Coordinates for Colônia Leopoldina - AL
        "Padre Francisco": (-8.9101631, -35.7196767),
        "Severino Ferreira": (-8.9119878, -35.7183578),
        "Genival Rodrigues": (-8.9116736, -35.7226213),
        "Mário Lima": (-8.9121909, -35.7221742),
        "Mario Lima": (-8.9121909, -35.7221742),
        "7 de Setembro": (-8.9129721, -35.7229025),
        "Setembro": (-8.9129721, -35.7229025),
        "Manoel Ataíde": (-8.9134105, -35.7222470),
        "Manoel Ataide": (-8.9134105, -35.7222470),
        "Mário de Gusmão": (-8.9139014, -35.7209606),
        "Mario de Gusmao": (-8.9139014, -35.7209606),
        "Artur Ferreira": (-8.9091807, -35.7177514),
        "Filomena Freitas": (-8.9116689, -35.7156993),
        "José Francisco Xavier": (-8.9118923, -35.7140726),
        "José Gomes": (-8.9121455, -35.7148886),
        "Genildo Loureiro": (-8.9118782, -35.7143524),
        "José Maria Ramos": (-8.9106410, -35.7156470),
        "José Maria Quirino": (-8.9115000, -35.7155000),
        "Maria Quirino": (-8.9115000, -35.7155000),
        "Quirino": (-8.9115000, -35.7155000),
        "Teódulo Augusto": (-8.9118238, -35.7257887),
        "Teodulo Augusto": (-8.9118238, -35.7257887),
        "Teofilo Augusto": (-8.9118238, -35.7257887),
        "Durval Gonçalves": (-8.9116432, -35.7252109),
        "Durval Goncalves": (-8.9116432, -35.7252109),
        "Manoel Lino": (-8.9121762, -35.7243278),
        "José Inácio": (-8.9114035, -35.7178309),
        "Jose Inacio": (-8.9114035, -35.7178309),
        "Pedro II": (-8.9107666, -35.7240646),
        "16 de Julho": (-8.9109060, -35.7249840),
        "Padre Cícero": (-8.9111747, -35.7266912),
        "Padre Cicero": (-8.9111747, -35.7266912),
        "Gustavo Fitipaldi": (-8.9102588, -35.7251056),
        "Boa Vista": (-8.9125343, -35.7253001),
        "Vila Nova": (-8.9069634, -35.7247413),
        "Belo Jardim": (-8.9106093, -35.7201824),
        "Loteamento Belo Jardim": (-8.9106093, -35.7201824),
        "Centro": (-8.9113702, -35.7208226),
    }
    
    city_center_lat, city_center_lng = -8.9113702, -35.7208226
    
    def _clamp(lat, lng):
        c_lat = max(-8.9150, min(-8.9065, lat))
        c_lng = max(-35.7270, min(-35.7135, lng))
        return c_lat, c_lng

    localidades_map = {}
    heat_points = []
    cidadaos = []
    
    for u in usuarios:
        full_addr = u["endereco"] or ""
        bairro, rua = _parse_address(full_addr)
        
        matched_coord = None
        for key, coord in base_coords.items():
            k_low = key.lower()
            if k_low in full_addr.lower() or k_low in rua.lower() or k_low in bairro.lower():
                matched_coord = coord
                break
                
        if not matched_coord:
            h = int(hashlib.md5(full_addr.encode('utf-8')).hexdigest(), 16)
            lat_offset = ((h % 100) - 50) * 0.00001
            lng_offset = (((h // 100) % 100) - 50) * 0.00001
            matched_coord = (city_center_lat + lat_offset, city_center_lng + lng_offset)
            
        m_lat, m_lng = _clamp(matched_coord[0], matched_coord[1])
        loc_name = bairro if (bairro != "Não Informado" and not bairro.isdigit() and not bairro.startswith("N")) else (rua if rua != "Não Informado" else "Centro")
        
        if loc_name not in localidades_map:
            localidades_map[loc_name] = {
                "name": loc_name,
                "lat": m_lat,
                "lng": m_lng,
                "total": 0
            }
            
        localidades_map[loc_name]["total"] += 1
        
        u_id_str = str(u["id"])
        if u_id_str in user_coords:
            u_lat, u_lng = _clamp(user_coords[u_id_str][0], user_coords[u_id_str][1])
        else:
            h_u = int(hashlib.md5(f"{u_id_str}_{full_addr}".encode('utf-8')).hexdigest(), 16)
            j_lat = ((h_u % 50) - 25) * 0.000008
            j_lng = (((h_u // 50) % 50) - 25) * 0.000008
            u_lat, u_lng = _clamp(m_lat + j_lat, m_lng + j_lng)
            
        heat_points.append({"lat": u_lat, "lng": u_lng, "weight": 1})
        cidadaos.append({
            "id": u["id"],
            "nome": u["nome"],
            "cpf": u["cpf"],
            "email": u["email"],
            "telefone": u["telefone"],
            "whatsapp": u["whatsapp"],
            "genero": u["genero"],
            "endereco": u["endereco"],
            "lat": u_lat,
            "lng": u_lng
        })
        
    localidades_list = sorted(localidades_map.values(), key=lambda x: x["total"], reverse=True)
    
    return {
        "localidades": localidades_list,
        "heat_points": heat_points,
        "cidadaos": cidadaos,
        "total_cadastrados": len(usuarios)
    }
