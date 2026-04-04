
import requests

def test_global_visibility():
    base_url = "https://prefeitura-digital.onrender.com/api"
    login_payload = {"username": "super@teste.com", "password": "123"}
    
    print("Logando como Super Admin...")
    res = requests.post(f"{base_url}/auth/login", data=login_payload)
    if res.status_code != 200:
        print(f"Erro no login: {res.text}")
        return
    
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Buscando Ocorrências...")
    res_oc = requests.get(f"{base_url}/ocorrencias", headers=headers)
    print(f"Status /ocorrencias: {res_oc.status_code}")
    if res_oc.status_code == 200:
        data = res_oc.json()
        print(f"Total de ocorrências recebidas: {len(data)}")
        if len(data) > 0:
            print(f"Exemplo: ID {data[0]['id']} - Título: {data[0]['titulo']} - Secretaria: {data[0].get('secretaria_nome', 'N/A')}")
    else:
        print(f"Erro: {res_oc.text}")

if __name__ == "__main__":
    test_global_visibility()
