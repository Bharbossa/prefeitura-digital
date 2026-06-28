import sys
import os

# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.schema import Usuario, AdminSecretaria
from app.utils.sms_service import send_status_sms
import time

def send_bulk_messages():
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        subadmins = db.query(AdminSecretaria).all()
        
        all_users = users + subadmins
        unique_phones = set()
        
        message = "Bom Domingo! Colônia Digital"
        
        print(f"Encontrados {len(all_users)} usuários totais no banco.")
        
        sent_count = 0
        for u in all_users:
            phone = getattr(u, 'telefone', None)
            if phone and len(''.join(filter(str.isdigit, phone))) >= 10:
                clean_phone = "".join(filter(str.isdigit, phone))
                if clean_phone not in unique_phones:
                    unique_phones.add(clean_phone)
                    print(f"Enviando para {clean_phone}...")
                    success = send_status_sms(clean_phone, message)
                    if success:
                        sent_count += 1
                    # Espera 1 segundo para evitar bloqueio por spam da API
                    time.sleep(1)
        
        print(f"\n--- RESUMO ---")
        print(f"Mensagem disparada com sucesso para {sent_count} números únicos.")
    finally:
        db.close()

if __name__ == "__main__":
    send_bulk_messages()
