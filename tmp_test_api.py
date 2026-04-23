import requests
import json
import time

BASE_URL = "https://prefeitura-digital.onrender.com/api"
TEST_ACCOUNT = {
    "nome": "Test Bug Hunter",
    "cpf": f"999.000.{int(time.time()) % 1000:03}-00",
    "email": f"test_debug_{int(time.time())}@teste.com",
    "senha": "password123"
}

def test_flow():
    print(f"--- Testing Production API at {BASE_URL} ---")
    
    # 1. Register
    print(f"Registering {TEST_ACCOUNT['email']}...")
    res = requests.post(f"{BASE_URL}/auth/register", json=TEST_ACCOUNT, verify=False)
    print(f"Register status: {res.status_code}")
    print(f"Register response: {res.text}")
    
    if res.status_code != 200:
        # Check if already exists
        print("Registration failed, trying login with alexandregilberto1994@gmail.com...")
        TEST_ACCOUNT['email'] = "alexandregilberto1994@gmail.com"
        TEST_ACCOUNT['senha'] = "123456"

    # 2. Login
    print(f"Logging in with {TEST_ACCOUNT['email']}...")
    login_data = {
        "username": TEST_ACCOUNT['email'],
        "password": TEST_ACCOUNT['senha']
    }
    res = requests.post(f"{BASE_URL}/auth/login", data=login_data, verify=False)
    print(f"Login status: {res.status_code}")
    if res.status_code != 200:
        print(f"Login FAILED: {res.text}")
        return
    
    token = res.json()["access_token"]
    print(f"Token acquired. Length: {len(token)}")
    
    # 3. Access Ocorrencias
    print("Accessing /api/ocorrencias (GET)...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/ocorrencias", headers=headers, verify=False)
    print(f"Ocorrencias GET status: {res.status_code}")
    
    # 4. Create Ocorrencia
    print("Creating Ocorrencia (POST)...")
    oc_data = {
        "titulo": "Teste Antigravity Prod",
        "descricao": "Descricao de teste via script automatizado",
        "secretaria_id": 1,
        "rua": "Rua de Teste",
        "ponto_referencia": "Perto do Debug"
    }
    # Create multipart/form-data manually since API uses Form(...)
    res = requests.post(f"{BASE_URL}/ocorrencias", headers=headers, data=oc_data, verify=False)
    print(f"Ocorrencias POST status: {res.status_code}")
    print(f"Ocorrencias POST response: {res.text}")

    # 5. Check Logs
    print("Reading debug logs...")
    res = requests.get(f"{BASE_URL}/auth/debug-logs-view", verify=False)
    print(f"Logs: {res.json().get('logs', 'No logs found')}")

def test_subadmin():
    print(f"\n--- Testing Subadmin Login ---")
    login_data = {
        "username": "infra@teste.com",
        "password": "password123"
    }
    res = requests.post(f"{BASE_URL}/auth/login", data=login_data, verify=False)
    print(f"Subadmin Login status: {res.status_code}")
    if res.status_code == 200:
        token = res.json()["access_token"]
        print("Subadmin Token acquired.")
        # Access admin-only endpoint
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(f"{BASE_URL}/secretarias/minha", headers=headers, verify=False)
        print(f"Secretaria ID status: {res.status_code}")
    else:
        print(f"Subadmin Login FAILED: {res.text}")

if __name__ == "__main__":
    test_flow()
    test_subadmin()
