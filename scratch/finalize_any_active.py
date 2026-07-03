import requests
import json

BASE_URL = "http://localhost:8001/api"
DNI = "43084696"
PASSWORD = "123"

def finalize_active():
    print(f"=== FINALIZING ACTIVE ACTIVITY FOR {DNI} ===")
    
    # 1. Login
    login_res = requests.post(f"{BASE_URL}/auth/login/", json={"dni": DNI, "password": PASSWORD})
    if login_res.status_code != 200:
        print(f"[!] Login failed: {login_res.text}")
        return
        
    token = login_res.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get current activity
    print("[*] Fetching current activity...")
    act_res = requests.get(f"{BASE_URL}/jornada-actividades/actual/", headers=headers)
    if act_res.status_code == 204:
        print("[*] No active activity found.")
        return
    elif act_res.status_code != 200:
        print(f"[!] Fetch failed: {act_res.text}")
        return
        
    activity = act_res.json()
    act_id = activity['id']
    print(f"[OK] Found active activity: ID {act_id} - Title: {activity['titulo']}")
    
    # 3. Finalize it
    print("[*] Finalizing activity...")
    data = {
        'actividad_id': act_id,
        'resultado_actividad': 'EXITOSO',
        'observacion': 'Finalizado automáticamente por script de prueba',
        'latitud_fin': -12.046374,
        'longitud_fin': -77.042793,
        'dispositivo_fin': 'Python Finalize Script'
    }
    
    # Let's send it
    fin_res = requests.post(f"{BASE_URL}/jornada-actividades/finalizar/", headers=headers, data=data)
    print(f"[*] Finalize Response Code: {fin_res.status_code}")
    print(f"[*] Finalize Response Body: {fin_res.text}")

if __name__ == '__main__':
    finalize_active()
