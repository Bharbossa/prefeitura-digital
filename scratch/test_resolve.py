import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.database import SessionLocal
from app.models.schema import Ocorrencia
from app.utils.sms_service import send_status_sms, get_resolved_message

db = SessionLocal()
ocorrencia = db.query(Ocorrencia).order_by(Ocorrencia.id.desc()).first()
if ocorrencia and ocorrencia.usuario:
    print(f"User: {ocorrencia.usuario.nome}, Phone: {ocorrencia.usuario.whatsapp} or {ocorrencia.usuario.telefone}")
    phone = ocorrencia.usuario.whatsapp or ocorrencia.usuario.telefone
    msg = get_resolved_message(ocorrencia.titulo)
    print(f"Sending msg: {msg} to {phone}")
    res = send_status_sms(phone, msg)
    print(f"Result: {res}")
else:
    print("No ocorrencia or user found")
