import sys
import os
import uuid
import io
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.main import app
from app.database import SessionLocal
from app.models.schema import AdminSecretaria, Secretaria, Usuario, TipoUsuario
from app.core.security import get_password_hash

client = TestClient(app)

def test_concurso_docs_endpoints():
    db = SessionLocal()
    try:
        # 1. Setup Cultura e Esporte secretariat ID
        sec_cultura = db.query(Secretaria).filter(Secretaria.nome.like("%CULTURA%ESPORTE%")).first()
        if not sec_cultura:
            sec_cultura = Secretaria(nome="SECRETARIA MUNICIPAL DE CULTURA E ESPORTE")
            db.add(sec_cultura)
            db.commit()
            db.refresh(sec_cultura)
        
        # 2. Setup Saúde secretariat ID (which is unauthorized)
        sec_saude = db.query(Secretaria).filter(Secretaria.nome.like("%SAÚDE%")).first()
        if not sec_saude:
            sec_saude = Secretaria(nome="SECRETARIA MUNICIPAL DE SAÚDE")
            db.add(sec_saude)
            db.commit()
            db.refresh(sec_saude)

        # 3. Create subadmins
        sub_cultura_email = f"jeff_cultura_{uuid.uuid4().hex[:4]}@teste.com"
        sub_cultura = AdminSecretaria(
            nome="Jeff Cultura",
            email=sub_cultura_email,
            cpf=f"123{uuid.uuid4().hex[:8]}"[:11],
            senha_hash=get_password_hash("123456"),
            secretaria_id=sec_cultura.id
        )
        db.add(sub_cultura)

        sub_saude_email = f"bob_saude_{uuid.uuid4().hex[:4]}@teste.com"
        sub_saude = AdminSecretaria(
            nome="Bob Saude",
            email=sub_saude_email,
            cpf=f"987{uuid.uuid4().hex[:8]}"[:11],
            senha_hash=get_password_hash("123456"),
            secretaria_id=sec_saude.id
        )
        db.add(sub_saude)

        # General Admin
        admin_email = f"admin_geral_{uuid.uuid4().hex[:4]}@teste.com"
        admin_user = Usuario(
            nome="Admin Geral",
            email=admin_email,
            cpf=f"111.111.{uuid.uuid4().hex[:3]}-11"[:14],
            senha_hash=get_password_hash("123456"),
            tipo_usuario="admin",
            status="ativo"
        )
        db.add(admin_user)
        db.commit()

        # Logins
        res = client.post("/api/auth/login", data={"username": sub_cultura_email, "password": "123456"})
        assert res.status_code == 200
        token_cultura = res.json()["access_token"]

        res = client.post("/api/auth/login", data={"username": sub_saude_email, "password": "123456"})
        assert res.status_code == 200
        token_saude = res.json()["access_token"]

        res = client.post("/api/auth/login", data={"username": admin_email, "password": "123456"})
        assert res.status_code == 200
        token_admin = res.json()["access_token"]

        # 4. Try upload with bob_saude (Unauthorized Subadmin) -> Expect 403
        fake_file = ("rules.pdf", io.BytesIO(b"dummy pdf content"), "application/pdf")
        res_upload = client.post(
            "/api/agendamentos/concursos/documentos",
            headers={"Authorization": f"Bearer {token_saude}"},
            data={"concurso": "Papa-Cuscuz", "tipo_documento": "regulamento"},
            files={"arquivo": fake_file}
        )
        assert res_upload.status_code == 403, f"Expected 403, got {res_upload.status_code}: {res_upload.text}"
        print("Successfully verified: Bob from Saúde is forbidden to upload rules!")

        # 5. Try upload with jeff_cultura (Authorized Subadmin) -> Expect 200
        fake_file = ("rules.pdf", io.BytesIO(b"dummy pdf content"), "application/pdf")
        res_upload = client.post(
            "/api/agendamentos/concursos/documentos",
            headers={"Authorization": f"Bearer {token_cultura}"},
            data={"concurso": "Papa-Cuscuz", "tipo_documento": "regulamento"},
            files={"arquivo": fake_file}
        )
        assert res_upload.status_code == 200, f"Expected 200, got {res_upload.status_code}: {res_upload.text}"
        path_cultura = res_upload.json()["path"]
        print(f"Successfully verified: Jeff from Cultura uploaded rules to: {path_cultura}")

        # 6. Try upload with admin_geral (Authorized Admin) -> Expect 200
        fake_waiver = ("waiver.txt", io.BytesIO(b"dummy waiver content"), "text/plain")
        res_upload = client.post(
            "/api/agendamentos/concursos/documentos",
            headers={"Authorization": f"Bearer {token_admin}"},
            data={"concurso": "Papa-Cuscuz", "tipo_documento": "termo"},
            files={"arquivo": fake_waiver}
        )
        assert res_upload.status_code == 200, f"Expected 200, got {res_upload.status_code}: {res_upload.text}"
        path_admin = res_upload.json()["path"]
        print(f"Successfully verified: Admin Geral uploaded waiver to: {path_admin}")

        # 7. GET list of documents -> Expect both to be present
        res_get = client.get("/api/agendamentos/concursos/documentos")
        assert res_get.status_code == 200
        docs = res_get.json()
        assert docs["Papa-Cuscuz"]["regulamento"] == path_cultura.replace("\\", "/")
        assert docs["Papa-Cuscuz"]["termo"] == path_admin.replace("\\", "/")
        print("Successfully verified: GET /api/agendamentos/concursos/documentos yields correct custom paths!")

        print("\n=== ALL TEST CONCURSO DOCS ENDPOINTS PASSED SUCCESSFULLY! ===")

    finally:
        try:
            # Clean up mock users
            if 'sub_cultura' in locals():
                db.delete(sub_cultura)
            if 'sub_saude' in locals():
                db.delete(sub_saude)
            if 'admin_user' in locals():
                db.delete(admin_user)
            db.commit()
            print("Temporary users cleaned up from database successfully!")
        except Exception as cleanup_err:
            print("Error during cleanup:", cleanup_err)
            db.rollback()
        db.close()

if __name__ == "__main__":
    test_concurso_docs_endpoints()
