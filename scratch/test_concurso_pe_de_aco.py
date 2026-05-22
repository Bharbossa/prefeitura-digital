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
        partner_cpf = "777.777.777-77"
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
        
        print("\n=== PÉ DE AÇO CONCURSO FLOW TEST PASSED SUCCESSFULLY! ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_pe_de_aco_concurso_flow()
