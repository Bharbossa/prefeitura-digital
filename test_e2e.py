import requests
import json
import uuid

BASE_URL = "https://prefeitura-digital.onrender.com/api"

def run_tests():
    print("=== Iniciando Testes E2E (Colônia Digital) ===")
    unique_id = uuid.uuid4().hex[:8]
    email = f"cidadon_{unique_id}@teste.com"
    cpf = "111222333" + unique_id[:2]
    
    # 1. Registrar Cidadão
    print(f"\n1. Registrando cidadão: {email}")
    reg_data = {
        "nome": "Cidadão Teste E2E",
        "cpf": cpf,
        "email": email,
        "senha": "123",
        "telefone": "1199999999"
    }
    r = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    if r.status_code != 200:
        print(f"FAILED (Register): {r.status_code} - {r.text}")
        return False
    print("SUCCESS")
    
    # 2. Login
    print("\n2. Login")
    login_data = {"username": email, "password": "123"}
    r = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if r.status_code != 200:
        print(f"FAILED (Login): {r.status_code} - {r.text}")
        return False
    print("SUCCESS")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 3. Listar Secretarias
    print("\n3. Listar Secretarias")
    r = requests.get(f"{BASE_URL}/secretarias")
    if r.status_code != 200:
        print(f"FAILED (Secretarias): {r.status_code} - {r.text}")
        return False
    secretarias = r.json()
    print(f"SUCCESS - {len(secretarias)} secretarias recebidas")
    
    saude_id = next((s['id'] for s in secretarias if "SAÚDE" in s['nome'].upper()), 15)
    
    # 4. Criar Ocorrência
    print("\n4. Criar Ocorrência")
    oco_data = {
        "secretaria_id": str(saude_id),
        "titulo": "Buraco na rua principal",
        "descricao": "Teste automatizado end-to-end"
    }
    r = requests.post(f"{BASE_URL}/ocorrencias", data=oco_data, headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        print(f"FAILED (Criar Ocorrência): {r.status_code} - {r.text}")
        return False
    print("SUCCESS")
    
    # 5. Listar Ocorrências do Usuário (revisitado erro antigo)
    print("\n5. Listar Minhas Ocorrências")
    r = requests.get(f"{BASE_URL}/ocorrencias", headers=headers)
    if r.status_code != 200:
        print(f"FAILED (Listar Ocorrências): {r.status_code} - {r.text}")
        return False
    print(f"SUCCESS - {len(r.json())} recebidas")
    
    # 6. Criar Agendamento
    print("\n6. Criar Agendamento")
    ag_data = {
        "secretaria_id": int(saude_id),
        "tipo": "Consulta Presencial",
        "assunto": "Teste Consulta E2E",
        "motivo": None,
        "acompanhante": None,
        "data_hora": "2026-03-31T12:00:00.000Z",
        "cartao_sus": "12345678901234567890"
    }
    r = requests.post(f"{BASE_URL}/agendamentos", json=ag_data, headers=headers)
    if r.status_code != 200:
        print(f"FAILED (Criar Agendamento): {r.status_code} - {r.text}")
        return False
    print("SUCCESS")
    
    # 7. Listar Agendamentos do Usuário
    print("\n7. Listar Meus Agendamentos")
    r = requests.get(f"{BASE_URL}/agendamentos", headers=headers)
    if r.status_code != 200:
        print(f"FAILED (Listar Agendamentos): {r.status_code} - {r.text}")
        return False
    print(f"SUCCESS - {len(r.json())} recebidos")
    
    print("\n=== TODOS OS TESTES PASSARAM COM SUCESSO! ===")
    return True

if __name__ == "__main__":
    run_tests()
