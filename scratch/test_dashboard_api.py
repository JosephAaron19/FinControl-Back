import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://localhost:8001/api"
DNI = "admin"
PASSWORD = "123456"

def test_dashboard():
    print(f"=== TESTING DASHBOARD API AT {BASE_URL} ===")
    
    # 1. Login
    login_url = f"{BASE_URL}/auth/login/"
    login_data = json.dumps({"dni": DNI, "password": PASSWORD}).encode('utf-8')
    req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        token = res_data['access']
        
    # 2. Get dashboard summary
    dashboard_url = f"{BASE_URL}/dashboard/resumen/?rango=hoy"
    req = urllib.request.Request(
        dashboard_url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )
    
    print("[*] Fetching dashboard...")
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        
    print("[OK] Verification:")
    
    # Validate activities properties
    act_data = res_data.get('actividades', {})
    print(" - activities payload:", act_data)
    assert 'total_actividades' in act_data, "Missing total_actividades"
    assert 'actividades_pendientes' in act_data, "Missing actividades_pendientes"
    
    # Validate trend chart data
    trend_data = res_data.get('graficos', {}).get('asistencia_por_dia_semana', [])
    print(f" - Trend chart days count: {len(trend_data)}")
    assert len(trend_data) >= 7, f"Trend chart should have at least 7 days of data when range is 'hoy'. Found: {len(trend_data)}"
    
    print("[SUCCESS] All assertions passed!")

if __name__ == '__main__':
    test_dashboard()
