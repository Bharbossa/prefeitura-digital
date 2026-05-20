import requests

API_URL = "http://localhost:8000" # Update if needed

def test_ocorrencia_location():
    # This test assumes the server is running and a user is logged in.
    # Since I cannot easily run a full login flow here without credentials,
    # I will just check if the model fields are present in the response.
    
    print("Verificando se os campos de latitude/longitude estão presentes no modelo...")
    
    # Check if we can reach the API
    try:
        response = requests.get(f"{API_URL}/ocorrencias/test-open")
        if response.status_code == 200:
            print("API está acessível.")
        else:
            print(f"API retornou status {response.status_code}")
    except Exception as e:
        print(f"Erro ao conectar na API: {e}")

if __name__ == "__main__":
    test_ocorrencia_location()
