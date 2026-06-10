import requests
import json

BASE_URL = "http://localhost:8001/api"
DNI = "43084696"  # Adviser DNI
PASSWORD = "123"

def test_prod_upload():
    print(f"=== TESTING PROD UPLOAD AT {BASE_URL} ===")
    
    # 1. Login
    print("[*] Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login/", json={"dni": DNI, "password": PASSWORD})
    if login_res.status_code != 200:
        print(f"[!] Login failed: {login_res.status_code} - {login_res.text}")
        return
        
    token = login_res.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Logged in successfully.")

    # 2. Prepare 1x1 GIF image bytes
    gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    
    files = {
        'evidencia_inicio_url': ('test_image.gif', gif_bytes, 'image/gif')
    }
    
    data = {
        'tipo_actividad': 'VISITA',
        'titulo': 'Test Prod Upload with Photo',
        'descripcion': 'Testing activity upload from script to prod',
        'cliente_nombre': 'Cliente de Prueba',
        'latitud_inicio': -12.046374,
        'longitud_inicio': -77.042793,
        'dispositivo_inicio': 'Python Request Script'
    }
    
    print("[*] Sending POST to iniciar activity with photo...")
    res = requests.post(f"{BASE_URL}/jornada-actividades/iniciar/", headers=headers, data=data, files=files)
    print(f"[*] Response Status Code: {res.status_code}")
    print(f"[*] Response Body: {res.text[:1000]}") # truncate to 1000 chars

if __name__ == '__main__':
    test_prod_upload()
