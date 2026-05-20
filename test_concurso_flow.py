import sys
import os
import uuid
# import pytest
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.main import app
from app.database import SessionLocal
from app.models.schema import AdminSecretaria, Secretaria, Agendamento, Usuario, TipoUsuario
from app.core.security import get_password_hash

client = TestClient(app)

def test_full_concurso_flow():
    db = SessionLocal()
    try:
        # 1. Setup a unique citizen
        unique_id = uuid.uuid4().hex[:8]
        citizen_email = f"cidadao_concurso_{unique_id}@teste.com"
        citizen_cpf = f"999.000.{unique_id[:3]}-00"
        citizen_password = "123"
        
        # Register citizen
        reg_payload = {
            "nome": "Cidadão Teste Concurso",
            "cpf": citizen_cpf,
            "email": citizen_email,
            "senha": citizen_password,
            "telefone": "1199999999",
            "endereco": "Rua do Concurso, 123",
            "whatsapp": "1199999999"
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 200, f"Register failed: {res.text}"
        
        # Login citizen
        login_res = client.post("/api/auth/login", data={"username": citizen_email, "password": citizen_password})
        assert login_res.status_code == 200, f"Login failed: {res.text}"
        citizen_token = login_res.json()["access_token"]
        citizen_headers = {"Authorization": f"Bearer {citizen_token}"}
        
        # 2. Get Cultura e Esporte secretariat ID
        sec = db.query(Secretaria).filter(Secretaria.nome.like("%CULTURA%")).first()
        if not sec:
            # Seed if not found
            sec = Secretaria(nome="SECRETARIA MUNICIPAL DE CULTURA E ESPORTE")
            db.add(sec)
            db.commit()
            db.refresh(sec)
        
        sec_id = sec.id
        print(f"\nSecretaria ID for Cultura e Esporte: {sec_id}")
        
        # 3. Create mock files for upload
        import io
        photo_file = ( "photo.png", io.BytesIO(b"fake image content"), "image/png" )
        pdf_file = ( "regulamento.pdf", io.BytesIO(b"fake pdf content"), "application/pdf" )
        
        # Post multipart form for concurso
        form_data = {
            "secretaria_id": (None, str(sec_id)),
            "tipo": (None, "Concurso"),
            "assunto": (None, f"[Concurso: Papa-Cuscuz] Nome: Cidadão Teste Concurso | CPF: {citizen_cpf}"),
            "motivo": (None, "")
        }
        files = {
            "foto": photo_file,
            "pdf": pdf_file
        }
        
        res_concurso = client.post(
            "/api/agendamentos/concurso",
            headers={"Authorization": f"Bearer {citizen_token}"},
            data=form_data,
            files=files
        )
        assert res_concurso.status_code == 200, f"Concurso inscription failed: {res_concurso.text}"
        
        concurso_data = res_concurso.json()
        print("\nCreated Inscription details:")
        print(f"Protocolo: {concurso_data.get('protocolo')}")
        print(f"Senha (sequencial): {concurso_data.get('senha')}")
        print(f"Tipo: {concurso_data.get('tipo')}")
        print(f"Anexo paths: {concurso_data.get('anexo')}")
        
        assert concurso_data.get("tipo") == "Concurso"
        assert concurso_data.get("senha").startswith("INS-")
        assert concurso_data.get("anexo") is not None
        assert "," in concurso_data.get("anexo") # contains both photo and pdf separated by comma
        
        agendamento_id = concurso_data.get("id")
        
        # 4. Get subadmin for Cultura e Esporte
        subadmin_email = "jefftenocava@gmail.com"
        subadmin = db.query(AdminSecretaria).filter(AdminSecretaria.email == subadmin_email).first()
        if not subadmin:
            # Create subadmin if not exists
            subadmin = AdminSecretaria(
                nome="Jeff Cultura",
                email=subadmin_email,
                cpf="12345678912",
                senha_hash=get_password_hash("123456"),
                secretaria_id=sec_id
            )
            db.add(subadmin)
            db.commit()
            db.refresh(subadmin)
        else:
            # Make sure password is known
            subadmin.senha_hash = get_password_hash("123456")
            subadmin.secretaria_id = sec_id
            db.commit()
            
        # Login subadmin
        subadmin_login = client.post("/api/auth/login", data={"username": subadmin_email, "password": "123456"})
        assert subadmin_login.status_code == 200, f"Subadmin login failed: {subadmin_login.text}"
        subadmin_token = subadmin_login.json()["access_token"]
        subadmin_headers = {"Authorization": f"Bearer {subadmin_token}"}
        
        # List agendamentos as subadmin
        res_list = client.get("/api/agendamentos", headers=subadmin_headers)
        assert res_list.status_code == 200
        agendamentos_list = res_list.json()
        
        # Verify our inscription is present
        found = False
        for a in agendamentos_list:
            if a["id"] == agendamento_id:
                found = True
                assert a["senha"] == concurso_data["senha"]
                assert a["tipo"] == "Concurso"
                break
        assert found, "Inscription not visible to the secretariat subadmin"
        print("\nSuccessfully verified that subadmin sees the inscription!")
        
        # 5. Confirm the inscription
        confirm_res = client.patch(
            f"/api/agendamentos/{agendamento_id}/status?status=Confirmado",
            headers=subadmin_headers
        )
        assert confirm_res.status_code == 200, f"Confirmation failed: {confirm_res.text}"
        print("Successfully confirmed inscription!")
        
        # 6. Verify as citizen
        res_citizen_list = client.get("/api/agendamentos", headers=citizen_headers)
        assert res_citizen_list.status_code == 200
        for a in res_citizen_list.json():
            if a["id"] == agendamento_id:
                assert a["status"] == "Confirmado"
                break
        print("Citizen successfully sees the inscription as 'Confirmado'!")
        
        print("\n=== ALL FLOW TESTS PASSED SUCCESSFULLY! ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_full_concurso_flow()
