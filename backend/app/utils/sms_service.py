# sms_service.py
import logging
import os
import time
from dotenv import load_dotenv
load_dotenv()

# Configure logging to see SMS simulation in terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMS_SERVICE")

# Z-API Configuration Variables are retrieved dynamically in the function

def send_status_sms(phone: str, message: str):
    """
    Sends an SMS using Twilio.
    """
    if not phone:
        logger.warning("Tentativa de envio de SMS sem número de telefone.")
        return False
    
    # Clean phone number
    clean_phone = "".join(filter(str.isdigit, phone))
    if clean_phone.startswith("0"):
        clean_phone = clean_phone.lstrip("0")
    if len(clean_phone) < 10:
        logger.warning(f"Tentativa de envio para telefone inválido: {phone}")
        return False
    if len(clean_phone) in (10, 11):
        clean_phone = "55" + clean_phone
    elif not clean_phone.startswith("55") and len(clean_phone) < 13:
        clean_phone = "55" + clean_phone
    formatted_phone = "+" + clean_phone
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message_twilio = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            logger.info(f"SMS enviado para {formatted_phone} via Twilio (SID: {message_twilio.sid})")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar via Twilio para {formatted_phone}: {str(e)}")
            return False
            
    logger.error(f"--- ERRO: TWILIO NÃO CONFIGURADO. MENSAGEM SIMULADA NÃO ENVIADA ---")
    logger.error(f"PARA: {formatted_phone}")
    logger.error(f"MENSAGEM: {message}")
    logger.error(f"--------------------")
    
    return False

def make_voice_call(phone: str, message_text: str):
    """
    Initiates a Twilio Voice Call to play an automated message.
    """
    if not phone:
        logger.warning("Tentativa de chamada de voz sem número de telefone.")
        return False
        
    clean_phone = "".join(filter(str.isdigit, phone))
    if clean_phone.startswith("0"):
        clean_phone = clean_phone.lstrip("0")
    if len(clean_phone) < 10:
        logger.warning(f"Tentativa de chamada para telefone inválido: {phone}")
        return False
    if len(clean_phone) in (10, 11):
        clean_phone = "55" + clean_phone
    elif not clean_phone.startswith("55") and len(clean_phone) < 13:
        clean_phone = "55" + clean_phone
    formatted_phone = "+" + clean_phone
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
            # Use TwiML to speak the message in Portuguese
            twiml = f"<Response><Say language=\"pt-BR\" voice=\"Polly.Vitoria-Neural\">{message_text}</Say></Response>"
            
            call = client.calls.create(
                twiml=twiml,
                to=formatted_phone,
                from_=TWILIO_PHONE_NUMBER
            )
            logger.info(f"Chamada de voz iniciada para {formatted_phone} via Twilio (SID: {call.sid})")
            return True
        except Exception as e:
            logger.error(f"Erro ao iniciar chamada de voz via Twilio para {formatted_phone}: {str(e)}")
            return False
            
    logger.error(f"--- ERRO: TWILIO NÃO CONFIGURADO. CHAMADA DE VOZ NÃO INICIADA ---")
    logger.error(f"PARA: {formatted_phone}")
    logger.error(f"MENSAGEM: {message_text}")
    logger.error(f"--------------------")
    return False

def get_resolved_message(titulo: str):
    return "OBRIGADO POR USAR O COLÔNIA DIGITAL. SUA SOLICITAÇÃO FOI FINALIZADA!"

def get_progress_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) está EM ANDAMENTO e sendo analisada pela nossa equipe."

def get_cancelled_message(titulo: str):
    return f"COLÔNIA DIGITAL: Sua solicitação ({titulo}) foi CANCELADA."

def get_confirmed_message(assunto: str, data_hora: str, is_garagem: bool = False):
    if is_garagem:
        return f"ATENÇÃO - CONFIRMAÇÃO DE VIAGEM OBRIGATÓRIA\nO CIDADÃO DEVE COMPARECER À GARAGEM MUNICIPAL PARA CONFIRMAR SUA VIAGEM!"
    return f"COLÔNIA DIGITAL: Seu agendamento ({assunto}) para {data_hora} foi CONFIRMADO."

def send_password_sms(phone: str, password: str):
    """
    Sends an SMS using Twilio for new password requests.
    """
    message = f"COLÔNIA DIGITAL: Sua nova senha e: {password}. Recomendamos altera-la apos o login."
    
    if not phone:
        logger.warning("Tentativa de envio de senha sem número de telefone.")
        return False
        
    clean_phone = "".join(filter(str.isdigit, phone))
    
    if not clean_phone.startswith("55"):
        clean_phone = "55" + clean_phone
    formatted_phone = "+" + clean_phone
    
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message_twilio = client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=formatted_phone
            )
            logger.info(f"Senha enviada para {formatted_phone} via Twilio (SID: {message_twilio.sid})")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar senha via Twilio para {formatted_phone}: {str(e)}")
            return False
            
    logger.error(f"--- ERRO: TWILIO NÃO CONFIGURADO. MENSAGEM DE SENHA NÃO ENVIADA ---")
    logger.error(f"PARA: {formatted_phone}")
    logger.error(f"MENSAGEM: {message}")
    logger.error(f"--------------------")
    
    return False

def get_subadmins_and_admins(db, secretaria_id: int = None, extra_context: str = None):
    """
    Retorna o conjunto de telefones de:
    1. Sub-administradores da secretaria especificada (AdminSecretaria)
    2. Administradores Gerais do sistema (Usuario onde tipo_usuario == admin)
    3. Para Guarda Municipal / Patrulha / Mulher, subadmins específicos de GCM
    4. Para Saúde, se o agendamento for de um posto específico (PSF / Hospital), o coordenador responsável
    """
    from app.models.schema import AdminSecretaria, Secretaria, Usuario, TipoUsuario
    from sqlalchemy import or_, func

    dest_phones = set()

    is_gcm = False
    if secretaria_id in [16, 17]:
        is_gcm = True
    elif secretaria_id:
        sec = db.query(Secretaria).filter(Secretaria.id == secretaria_id).first()
        if sec and any(k in (sec.nome or "").lower() for k in ["guarda", "patrulha", "mulher", "seguran"]):
            is_gcm = True

    gcm_allowed_emails = [
        "patrulhamariadapenha.gcm.clp@gmail.com",
        "guardamunicipalcolonia@gmail.com",
        "daniel.carlos16@hotmail.com",
        "wilsongleidson@hotmail.com",
        "gameprf88@gmail.com",
        "ezequias_fernandes@outlook.com.br"
    ]

    if is_gcm:
        subadmins = db.query(AdminSecretaria).outerjoin(Secretaria).filter(
            or_(
                AdminSecretaria.secretaria_id.in_([16, 17]),
                func.lower(Secretaria.nome).like("%guarda%"),
                func.lower(Secretaria.nome).like("%patrulha%"),
                func.lower(Secretaria.nome).like("%mulher%"),
                func.lower(Secretaria.nome).like("%seguran%"),
                func.lower(AdminSecretaria.email).in_([e.lower() for e in gcm_allowed_emails])
            )
        ).all()
    elif secretaria_id:
        subadmins = db.query(AdminSecretaria).filter(AdminSecretaria.secretaria_id == secretaria_id).all()
    else:
        subadmins = []

    for sa in subadmins:
        if sa.telefone:
            dest_phones.add(sa.telefone)

    # Suporte a PSF / Postos de Saúde específicos se for agendamento de saúde
    if extra_context and (secretaria_id == 15 or any(k in (extra_context or "").lower() for k in ["saude", "saúde", "hospital", "posto", "consulta", "emergência", "emergencia"])):
        ctx_lower = extra_context.lower()
        psf_map = {
            'denilmalucass@gmail.com': ['hospital maria loureiro', 'maria loureiro', 'emergência', 'emergencia'],
            'vivianlmk@hotmail.com': ['josé luiz lessa', 'jose luiz lessa', 'luiz lessa', 'psf 01', 'psf 1'],
            'vanuzasoares667@gmail.com': ['posto centro', 'psf 02', 'psf 2'],
            'ketlinandrade01@icloud.com': ['vila nova', 'psf 03', 'psf 3'],
            'cassianub12@icloud.com': ['daniel monteiro', 'psf 04', 'psf 4'],
            'trajanojuliana17@gmail.com': ['usina taquara', 'taquara', 'psf 05', 'psf 5'],
            'ana.gabriela_2@hotmail.com': ['belo jardim', 'psf 06', 'psf 6'],
            'flaviadanielly381@gmail.com': ['josé adamor', 'jose adamor', 'adamor', 'psf 07', 'psf 7'],
            'arianacarater@gmail.com': ['josé acioly', 'jose acioly', 'acioly', 'psf 08', 'psf 8']
        }
        matched_emails = []
        for email, keywords in psf_map.items():
            if any(k in ctx_lower for k in keywords):
                matched_emails.append(email)
        if matched_emails:
            psf_users = db.query(Usuario).filter(func.lower(Usuario.email).in_(matched_emails)).all()
            for pu in psf_users:
                if pu.telefone:
                    dest_phones.add(pu.telefone)

    # Suporte a Garagem Municipal / Marcação de Viagem (inclui João Lucas e responsáveis da Garagem)
    is_viagem_context = (secretaria_id == 24) or (extra_context and any(k in (extra_context or "").lower() for k in ["viagem", "garagem"]))
    if is_viagem_context:
        garagem_admins = db.query(AdminSecretaria).filter(
            or_(
                AdminSecretaria.secretaria_id == 24,
                func.lower(AdminSecretaria.email) == 'sbarros.joaolucas@gmail.com'
            )
        ).all()
        for ga in garagem_admins:
            if ga.telefone:
                dest_phones.add(ga.telefone)

    # SEMPRE incluir os Administradores Gerais do sistema (Usuario onde tipo_usuario == admin)
    global_admins = db.query(Usuario).filter(
        or_(
            Usuario.tipo_usuario == TipoUsuario.admin,
            Usuario.tipo_usuario == "admin"
        )
    ).all()
    for ga in global_admins:
        if ga.telefone:
            dest_phones.add(ga.telefone)
        if getattr(ga, 'whatsapp', None):
            dest_phones.add(ga.whatsapp)

    return dest_phones

# Alias para manter compatibilidade com códigos legados
get_gcm_subadmins_and_admins = get_subadmins_and_admins

def notify_subadmins_background(secretaria_id: int, message: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        if message:
            custom_msg = message
        elif secretaria_id == 22:
            custom_msg = "COLÔNIA DIGITAL: Assistência Social / Cadastro Único! Existe uma nova solicitação de serviço!"
        else:
            custom_msg = "COLÔNIA DIGITAL: Nova solicitação de serviço registrada! Verifique o painel."
            
        dest_phones = get_subadmins_and_admins(db, secretaria_id, extra_context=message)
        for phone in sorted(list(dest_phones)):
            send_status_sms(phone, custom_msg)
            time.sleep(0.3)
    except Exception as e:
        logger.error(f"Erro em notify_subadmins_background: {e}")
    finally:
        db.close()

def notify_subadmins_voice_background(secretaria_id: int, message: str):
    """
    Sends a voice call in the background to all subadmins of Guarda Municipal / Patrulha / Segurança AND General Administrator.
    """
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        dest_phones = get_gcm_subadmins_and_admins(db, secretaria_id)
        for phone in sorted(list(dest_phones)):
            make_voice_call(phone, message)
            time.sleep(0.5)
    except Exception as e:
        logger.error(f"Erro em notify_subadmins_voice_background: {e}")
    finally:
        db.close()

def notify_all_users_background(alert_message: str, aviso_id: int = None):
    from app.database import SessionLocal
    from app.models.schema import Usuario, Aviso, AdminSecretaria
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        subadmins = db.query(AdminSecretaria).all()
        
        unique_phones = set()
        sucessos = 0
        
        # Helper to process a phone
        def process_phone(user_name, phone, tipo):
            nonlocal sucessos
            if phone and len(''.join(filter(str.isdigit, phone))) >= 10:
                clean_phone = "".join(filter(str.isdigit, phone))
                if clean_phone not in unique_phones:
                    unique_phones.add(clean_phone)
                    success = send_status_sms(clean_phone, alert_message)
                    if success:
                        sucessos += 1
                        
                    if aviso_id:
                        from app.models.schema import LogAvisoEnvio
                        log = LogAvisoEnvio(
                            aviso_id=aviso_id,
                            nome_destinatario=user_name,
                            telefone=clean_phone,
                            tipo_usuario=tipo,
                            sucesso=1 if success else 0
                        )
                        db.add(log)
                    
                    time.sleep(1) # Sleep to avoid rate limits

        for u in users:
            process_phone(u.nome, getattr(u, 'telefone', None), "cidadao")
            
        for sa in subadmins:
            process_phone(sa.nome, getattr(sa, 'telefone', None), "subadmin")

        if aviso_id:
            aviso = db.query(Aviso).filter(Aviso.id == aviso_id).first()
            if aviso:
                aviso.destinatarios_alcancados = sucessos
                db.commit()
    except Exception as e:
        logger.error(f"Erro em notify_all_users_background: {e}")
    finally:
        db.close()

def notify_custom_message_background(message: str):
    from app.database import SessionLocal
    from app.models.schema import Usuario
    db = SessionLocal()
    try:
        users = db.query(Usuario).all()
        unique_phones = set()
        sucessos = 0
        for u in users:
            phone = getattr(u, 'telefone', None)
            if phone and len(''.join(filter(str.isdigit, phone))) >= 10:
                clean_phone = "".join(filter(str.isdigit, phone))
                if clean_phone not in unique_phones:
                    unique_phones.add(clean_phone)
                    if send_status_sms(clean_phone, message):
                        sucessos += 1
                    time.sleep(1) # Sleep to avoid rate limits
        logger.info(f"Mensagem customizada enviada com sucesso para {sucessos} destinatarios.")
    except Exception as e:
        logger.error(f"Erro em notify_custom_message_background: {e}")
    finally:
        db.close()

def notify_admin_security_alert_background(tipo_ataque: str, ip_origem: str, detalhes: str):
    """
    Envia SMS de ALERTA DE INVASÃO imediato aos Administradores Gerais do sistema.
    """
    from app.database import SessionLocal, Base
    from app.models.schema import Usuario, LogInvasaoSeguranca
    db = SessionLocal()
    try:
        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception: pass

        # Registrar no banco de dados primeiro
        try:
            log_seg = LogInvasaoSeguranca(
                tipo_ataque=tipo_ataque,
                ip_origem=ip_origem,
                detalhes=detalhes,
                bloqueado=1
            )
            db.add(log_seg)
            db.commit()
        except Exception as e_log:
            db.rollback()
            logger.error(f"Erro ao salvar log de invasao: {e_log}")

        # Buscar todos os usuários e filtrar Administradores Gerais (suportando Enum ou String)
        all_users = db.query(Usuario).all()
        admins = [
            u for u in all_users 
            if str(getattr(u, 'tipo_usuario', '')).split('.')[-1].lower() == 'admin'
        ]
        
        admin_phones = set()
        for a in admins:
            tel = getattr(a, 'telefone', None)
            wsp = getattr(a, 'whatsapp', None)
            if tel:
                admin_phones.add(tel)
            if wsp:
                admin_phones.add(wsp)
                
        sms_body = f"⚠️ ALERTA DE SEGURANÇA - COLÔNIA DIGITAL: Tentativa de invasão bloqueada! Tipo: {tipo_ataque} | IP: {ip_origem}. Verifique o painel!"
        
        for phone in admin_phones:
            if phone and len("".join(filter(str.isdigit, phone))) >= 8:
                send_status_sms(phone, sms_body)
            
        logger.warning(f"🚨 ALERTA DE SEGURANÇA REGISTRADO E NOTIFICADO VIA SMS ({len(admin_phones)} telefones): {tipo_ataque} a partir do IP {ip_origem}")
    except Exception as e:
        logger.error(f"Erro ao notificar invasão por SMS: {e}")
    finally:
        db.close()

def notify_user_account_blocked_reset_password_background(user_id: int, nova_senha: str, is_admin: bool = False):
    """
    Envia SMS ao usuário avisando que a conta foi bloqueada por 3 tentativas falhas de login
    e fornece uma nova senha gerada automaticamente pelo sistema.
    """
    from app.database import SessionLocal
    from app.models.schema import Usuario, AdminSecretaria, LogRecuperacaoSenha
    db = SessionLocal()
    try:
        if is_admin:
            usuario = db.query(AdminSecretaria).filter(AdminSecretaria.id == user_id).first()
            user_type = "subadmin"
        else:
            usuario = db.query(Usuario).filter(Usuario.id == user_id).first()
            user_type = "cidadao"

        if not usuario:
            return

        phone = getattr(usuario, 'telefone', None) or getattr(usuario, 'whatsapp', None)
        if not phone:
            logger.warning(f"Usuário {usuario.email} não possui telefone cadastrado para aviso de bloqueio.")
            return

        sms_body = (
            f"COLÔNIA DIGITAL: Sua conta foi bloqueada apos 3 erros de senha. "
            f"Sua nova senha temporaria e: {nova_senha}"
        )
        success = send_status_sms(phone, sms_body)
        
        # Registrar no Log de Recuperação
        try:
            novo_log = LogRecuperacaoSenha(
                usuario_nome=usuario.nome,
                usuario_tipo=user_type,
                metodo="sms",
                sucesso=1 if success else 0
            )
            db.add(novo_log)
            db.commit()
        except Exception as e_log:
            logger.error(f"Erro ao salvar log de recuperacao: {e_log}")

        if success:
            logger.info(f"SMS de bloqueio e redefinição de senha enviado para {usuario.email} ({phone})")
        else:
            logger.error(f"Falha ao enviar SMS de redefinição de senha para {usuario.email}")
    except Exception as e:
        logger.error(f"Erro em notify_user_account_blocked_reset_password_background: {e}")
    finally:
        db.close()




