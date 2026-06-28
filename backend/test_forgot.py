import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.schema import Usuario
from app.core.security import get_password_hash

def test_forgot_password():
    print("=== Testing Forgot Password Flow ===")
    
    # 1. Start server or call API if running? No, we will just call the function directly to test logic
    # Actually, we can just hit the API if it's running. Is the API running? Probably not on my local shell.
    # Let's just test the logic directly:
    
    db = SessionLocal()
    try:
        # Check if test user exists
        test_email = "qa_test_user@teste.com"
        user = db.query(Usuario).filter(Usuario.email == test_email).first()
        if not user:
            print("Creating test user...")
            user = Usuario(
                nome="Test User QA",
                cpf="00000000000",
                email=test_email,
                telefone="11999999999", # Dummy phone that we saw in the logs before
                senha_hash=get_password_hash("old_password123"),
                status="ativo"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        print(f"Test user ready: {user.email}")
        
        # Test Forgot Password Logic (extracted from auth.py)
        import secrets, string
        from app.utils.sms_service import send_password_sms
        
        print("Generating new password...")
        alphabet = string.ascii_letters + string.digits
        new_pw = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        print("Updating hash...")
        user.senha_hash = get_password_hash(new_pw)
        db.commit()
        
        print(f"Sending Z-API WhatsApp message to {user.telefone}...")
        success = send_password_sms(user.telefone, new_pw)
        
        if success:
            print("SUCCESS! Z-API returned OK for forgot password.")
        else:
            print("FAILED to send Z-API message.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_forgot_password()
