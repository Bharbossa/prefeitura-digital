import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Login as a citizen
login_data = {"username": "12345678901", "password": "password123"}
res = client.post("/api/auth/login", data=login_data)
if res.status_code != 200:
    # Register first
    client.post("/api/auth/register", json={
        "nome": "Cidadao Teste",
        "cpf": "12345678901",
        "email": "cid@test.com",
        "telefone": "11999999999",
        "endereco": "Rua Teste",
        "senha": "password123",
        "data_nascimento": "1990-01-01"
    })
    res = client.post("/api/auth/login", data=login_data)

token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create dummy images
dummy_img = b"fake image content"

form_data = {
    "secretaria_id": "21",  # Cultura e Esporte
    "tipo": "Concurso",
    "assunto": "[Concurso: P\u00e9 de A\u00e7o] | Camisa: G | T\u00edtulo: 0976809769 | Parceiro: Teste Parceiro | Camisa Parceiro: G",
    "motivo": "Idade: 30\nIdade Parceiro(a): 42\nRG: 1234\nCPF: 1234\nRG Parceiro(a): 4321\nCPF Parceiro(a): 4321\nT\u00edtulo Parceiro(a): 9999"
}

files = {
    "cidadao_rg": ("rg.jpg", dummy_img, "image/jpeg"),
    "cidadao_cpf": ("cpf.jpg", dummy_img, "image/jpeg"),
    "cidadao_titulo": ("titulo.jpg", dummy_img, "image/jpeg"),
    "parceiro_rg_foto": ("prg.jpg", dummy_img, "image/jpeg"),
    "parceiro_cpf_foto": ("pcpf.jpg", dummy_img, "image/jpeg"),
    "parceiro_titulo_foto": ("ptitulo.jpg", dummy_img, "image/jpeg"),
}

res_concurso = client.post("/api/agendamentos/concurso", headers=headers, data=form_data, files=files)
print(res_concurso.status_code, res_concurso.text)

