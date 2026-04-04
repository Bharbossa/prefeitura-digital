
import requests
import json
import time

def wait_for_deploy():
    url = "https://prefeitura-digital.onrender.com/api/test-debug"
    print(f"Monitoring {url} for new version...")
    
    for i in range(15):
        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                if "debug_logs" in data:
                    print(f"SUCCESS: New version deployed! Logs found: {len(data['debug_logs'])} bytes")
                    return True
                else:
                    print(f"[{i}] Still old version (no debug_logs)...")
            else:
                print(f"[{i}] Error: {res.status_code}")
        except Exception as e:
            print(f"[{i}] Connection Error: {e}")
        
        time.sleep(15)
    return False

if __name__ == "__main__":
    wait_for_deploy()
