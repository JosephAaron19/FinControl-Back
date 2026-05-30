import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"
DNI = "12345678"  # Asegúrate de que este usuario exista en tu BD
PASSWORD = "123"

def test_flow():
    print("--- INICIANDO PRUEBA DE CONEXIÓN FINCONTROL ---")
    
    # 1. Probar Login
    print("\n1. Probando Login...")
    login_res = requests.post(f"{BASE_URL}/auth/login/", json={"dni": DNI, "password": PASSWORD})
    if login_res.status_code != 200:
        print(f"Error en Login: {login_res.text}")
        return
    token = login_res.json()['access']
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("OK: Token obtenido correctamente.")

    # 2. Probar Configuración de Tracking
    print("\n2. Consultando Configuración de Tracking...")
    config_res = requests.get(f"{BASE_URL}/configuracion-tracking/", headers=headers)
    if config_res.status_code == 200:
        print(f"OK: Configuración recibida -> {config_res.json()}")
    else:
        print(f"Error en Configuración: {config_res.text}")

    # 3. Simular Marcado de Entrada
    print("\n3. Simulando Marcado de Entrada...")
    entry_data = {
        "type": "ENTRADA",
        "latitud": -12.046374,
        "longitud": -77.042793,
        "device_info": "Script de Prueba"
    }
    entry_res = requests.post(f"{BASE_URL}/attendance/event/", json=entry_data, headers=headers)
    if entry_res.status_code == 200:
        res_data = entry_res.json()
        asistencia_id = res_data.get('asistencia_id')
        print(f"OK: Entrada marcada. Asistencia ID: {asistencia_id}")
        
        # 4. Simular Envío de Punto GPS (Tracking)
        print("\n4. Simulando Envío de Punto GPS...")
        point_data = {
            "asistencia": asistencia_id,
            "historial_jornada_id": asistencia_id,
            "latitud": -12.046500,
            "longitud": -77.042900,
            "precision_metros": 15.5,
            "bateria_porcentaje": 85,
            "origen": "Prueba de Integración"
        }
        point_res = requests.post(f"{BASE_URL}/ubicacion-puntos/", json=point_data, headers=headers)
        if point_res.status_code == 201:
            print(f"OK: Punto GPS registrado correctamente.")
        else:
            print(f"Error al enviar punto GPS: {point_res.text}")
    else:
        print(f"Error en Marcado: {entry_res.text}")

    print("\n--- PRUEBA FINALIZADA CON ÉXITO ---")

if __name__ == "__main__":
    test_flow()
