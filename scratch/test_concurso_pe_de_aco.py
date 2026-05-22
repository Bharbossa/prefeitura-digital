import sys
import os
import uuid
import io
from fastapi.testclient import TestClient

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.main import app
from app.database import SessionLocal
from app.models.schema import AdminSecretaria, Secretaria, Agendamento, Usuario

client = TestClient(app)

def test_pe_de_aco_concurso_flow():
    db = SessionLocal()
    try:
        # 1. Setup a unique citizen
        unique_id = uuid.uuid4().hex[:8]
        citizen_email = f"cidadao_pe_de_aco_{unique_id}@teste.com"
        citizen_cpf = f"888.000.{unique_id[:3]}-00"
        citizen_password = "123"
        
        # Register citizen
        reg_payload = {
            "nome": "Cidadão Pé de Aço Teste",
            "cpf": citizen_cpf,
            "email": citizen_email,
            "senha": citizen_password,
            "telefone": "1199999999",
            "endereco": "Rua Pé de Aço, 456",
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
            sec = Secretaria(nome="SECRETARIA MUNICIPAL DE CULTURA E ESPORTE")
            db.add(sec)
            db.commit()
            db.refresh(sec)
        
        sec_id = sec.id
        print(f"\nSecretaria ID for Cultura e Esporte: {sec_id}")
        
        # 3. Create mock files for upload (Foto, PDF, and Partner Voter Card Photo)
        photo_file = ("foto.png", io.BytesIO(b"fake photo content"), "image/png")
        pdf_file = ("doc.pdf", io.BytesIO(b"fake pdf content"), "application/pdf")
        voter_photo_file = ("titulo_parceiro.png", io.BytesIO(b"fake voter card photo content"), "image/png")
        
        # Partner details
        partner_name = "Parceira Pé de Aço"
        partner_rg = "9876543-SSP/AL"
        partner_cpf = f"777.000.{unique_id[:3]}-00"
        partner_titulo = "987654321012"
        
        assunto_pe_de_aco = f"[Concurso: Pé de Aço] Camisa: G | Título: 123456789012 | Parceiro: {partner_name} | Camisa Parceiro: M"
        motivo_pe_de_aco = f"RG Parceiro(a): {partner_rg}\nCPF Parceiro(a): {partner_cpf}\nTítulo Parceiro(a): {partner_titulo}"
        
        # Post multipart form for concurso with the three files
        form_data = {
            "secretaria_id": (None, str(sec_id)),
            "tipo": (None, "Concurso"),
            "assunto": (None, assunto_pe_de_aco),
            "motivo": (None, motivo_pe_de_aco)
        }
        files = {
            "foto": photo_file,
            "pdf": pdf_file,
            "foto_titulo": voter_photo_file
        }
        
        res_concurso = client.post(
            "/api/agendamentos/concurso",
            headers={"Authorization": f"Bearer {citizen_token}"},
            data=form_data,
            files=files
        )
        assert res_concurso.status_code == 200, f"Concurso inscription failed: {res_concurso.text}"
        
        concurso_data = res_concurso.json()
        print("\nCreated Pé de Aço Inscription details:")
        print(f"Protocolo: {concurso_data.get('protocolo')}")
        print(f"Senha: {concurso_data.get('senha')}")
        print(f"Tipo: {concurso_data.get('tipo')}")
        print(f"Anexos (should have 3 paths): {concurso_data.get('anexo')}")
        
        assert concurso_data.get("tipo") == "Concurso"
        assert concurso_data.get("senha").startswith("INS-")
        
        anexos = concurso_data.get("anexo").split(",")
        print(f"Total files uploaded: {len(anexos)}")
        assert len(anexos) == 3, f"Expected 3 attachments (foto, pdf, foto_titulo), found {len(anexos)}"
        
        agendamento_id = concurso_data.get("id")
        
        # 4. Verify as citizen
        res_list = client.get("/api/agendamentos", headers=citizen_headers)
        assert res_list.status_code == 200
        agendamentos_list = res_list.json()
        
        found = False
        for a in agendamentos_list:
            if a["id"] == agendamento_id:
                found = True
                assert a["usuario_nome"] == "Cidadão Pé de Aço Teste"
                assert "Pé de Aço" in a["assunto"]
                assert "RG Parceiro(a)" in a["motivo"]
                assert "CPF Parceiro(a)" in a["motivo"]
                assert "Título Parceiro(a)" in a["motivo"]
                break
        assert found, "Inscription not visible in citizen list"
        
        # 5. TEST CONFLICTS (Uniqueness Checks)
        # Attempt to register again as same citizen (Cidadão A)
        print("\nTesting: Duplicate citizen registration...")
        res_dup_cit = client.post(
            "/api/agendamentos/concurso",
            headers=citizen_headers,
            data={
                "secretaria_id": str(sec_id),
                "tipo": "Concurso",
                "assunto": f"[Concurso: Pé de Aço] Camisa: M | Título: 888888888888 | Parceiro: Novo Parceiro | Camisa Parceiro: P",
                "motivo": "RG Parceiro(a): 11111\nCPF Parceiro(a): 111.111.111-11\nTítulo Parceiro(a): 111111111111"
            }
        )
        assert res_dup_cit.status_code == 400, f"Expected 400 for duplicate citizen, got: {res_dup_cit.text}"
        assert "Seu CPF já está inscrito" in res_dup_cit.json()["detail"]
        print("Success: Duplicate citizen registration blocked correctly!")

        # Attempt to register as a new citizen (Cidadão C) but with same partner CPF (Partner B)
        # Register citizen 2
        print("\nTesting: Duplicate partner registration...")
        unique_id2 = uuid.uuid4().hex[:8]
        citizen2_email = f"cidadao_pe_de_aco2_{unique_id2}@teste.com"
        citizen2_cpf = f"888.222.{unique_id2[:3]}-00"
        
        reg_payload2 = {
            "nome": "Cidadão Pé de Aço 2 Teste",
            "cpf": citizen2_cpf,
            "email": citizen2_email,
            "senha": "123",
            "telefone": "1199999999",
            "endereco": "Rua Pé de Aço, 789",
            "whatsapp": "1199999999"
        }
        res2 = client.post("/api/auth/register", json=reg_payload2)
        assert res2.status_code == 200
        
        # Login citizen 2
        login_res2 = client.post("/api/auth/login", data={"username": citizen2_email, "password": "123"})
        assert login_res2.status_code == 200
        citizen2_token = login_res2.json()["access_token"]
        citizen2_headers = {"Authorization": f"Bearer {citizen2_token}"}

        # Attempt registration with duplicate partner CPF
        res_dup_part = client.post(
            "/api/agendamentos/concurso",
            headers=citizen2_headers,
            data={
                "secretaria_id": str(sec_id),
                "tipo": "Concurso",
                "assunto": f"[Concurso: Pé de Aço] Camisa: M | Título: 888888888888 | Parceiro: Parceira Pé de Aço | Camisa Parceiro: P",
                "motivo": f"RG Parceiro(a): 9876543-SSP/AL\nCPF Parceiro(a): {partner_cpf}\nTítulo Parceiro(a): 987654321012"
            }
        )
        assert res_dup_part.status_code == 400, f"Expected 400 for duplicate partner, got: {res_dup_part.text}"
        assert "CPF do seu parceiro já está inscrito" in res_dup_part.json()["detail"]
        print("Success: Duplicate partner registration blocked correctly!")

        # 6. TEST LIBERATION AFTER CANCELATION
        print("\nTesting: CPF liberation after cancellation...")
        first_registration = db.query(Agendamento).filter(Agendamento.id == agendamento_id).first()
        first_registration.status = "Cancelado"
        db.commit()

        # Try to register again as Cidadão Pé de Aço Teste (now that their registration is cancelled)
        res_liberated = client.post(
            "/api/agendamentos/concurso",
            headers=citizen_headers,
            data={
                "secretaria_id": str(sec_id),
                "tipo": "Concurso",
                "assunto": f"[Concurso: Pé de Aço] Camisa: G | Título: 123456789012 | Parceiro: Parceira Pé de Aço | Camisa Parceiro: M",
                "motivo": f"RG Parceiro(a): 9876543-SSP/AL\nCPF Parceiro(a): {partner_cpf}\nTítulo Parceiro(a): 987654321012"
            }
        )
        assert res_liberated.status_code == 200, f"Registration should succeed after cancellation, but failed: {res_liberated.text}"
        print("Success: CPFs liberated and new registration succeeded after previous registration was cancelled!")

        print("\n=== PÉ DE AÇO CONCURSO FLOW TEST PASSED SUCCESSFULLY! ===")
        
    finally:
        # Clean up all created test users and agendamentos to keep the DB clean
        try:
            u1 = db.query(Usuario).filter(Usuario.email == citizen_email).first()
            u2 = db.query(Usuario).filter(Usuario.email == citizen2_email).first() if 'citizen2_email' in locals() else None
            
            user_ids = []
            if u1: user_ids.append(u1.id)
            if u2: user_ids.append(u2.id)
            
            if user_ids:
                db.query(Agendamento).filter(Agendamento.usuario_id.in_(user_ids)).delete(synchronize_session=False)
                if u1: db.delete(u1)
                if u2: db.delete(u2)
                db.commit()
                print("Temporary test records cleaned up from database successfully!")
        except Exception as ex:
            print(f"Error during cleanup: {ex}")
        db.close()

if __name__ == "__main__":
    test_pe_de_aco_concurso_flow()
