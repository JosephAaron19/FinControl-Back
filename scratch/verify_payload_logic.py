import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from api.models import Sede, Horario, HorarioDetalle, UsuarioHorario
from api.views import HorarioViewSet

def run_payload_tests():
    print("=== INICIANDO PRUEBA DE PAYLOADS DE HORARIO ===")
    
    # Setup test Sede
    sede, _ = Sede.objects.get_or_create(
        nombre="Sede Payloads Test",
        defaults={"latitud": -12.046374, "longitud": -77.042793, "radio_metros": 100}
    )
    
    # Setup test User
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.filter(rol__nombre__icontains='admin').first()
    if not admin_user:
        admin_user = User.objects.create_superuser(
            dni="77777777",
            nombre_completo="Admin Payload Test",
            password="testpassword"
        )
        
    operator_user, _ = User.objects.get_or_create(
        dni="66666666",
        defaults={
            "nombre_completo": "Operator Payload Test",
            "sede": sede,
            "activo": True
        }
    )
    
    print(f"[*] Admin user: {admin_user.nombre_completo}")
    print(f"[*] Operator user: {operator_user.nombre_completo} (ID: {operator_user.id})")
    
    factory = APIRequestFactory()
    view = HorarioViewSet.as_view({'post': 'create'})
    
    # Limpiar asignaciones previas
    UsuarioHorario.objects.filter(usuario=operator_user).delete()
    
    # ----------------------------------------------------
    # TEST 1: Horario General Único
    # ----------------------------------------------------
    payload_general = {
        "modo": "general_unico",
        "sede_id": sede.id,
        "nombre": "Turno Mañana General Test",
        "descripcion": "Horario general de lunes a viernes",
        "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"],
        "hora_inicio_entrada": "08:00:00",
        "hora_fin_entrada": "09:00:00",
        "hora_inicio_salida": "17:00:00",
        "hora_fin_salida": "19:00:00",
        "usuarios_ids": [operator_user.id],
        "vigente_desde": "",
        "vigente_hasta": ""
    }
    
    request = factory.post('/api/horarios/', payload_general, format='json')
    force_authenticate(request, user=admin_user)
    response = view(request)
    
    print(f"[*] Test 1 Response Status: {response.status_code}")
    assert response.status_code == 201, f"Error: {response.data}"
    
    horario_id = response.data['id']
    horario_db = Horario.objects.get(id=horario_id)
    print(f"[OK] Horario General creado con ID: {horario_db.id}")
    assert horario_db.tipo_configuracion == 'general_unico'
    
    detalles = HorarioDetalle.objects.filter(horario=horario_db)
    print(f"[OK] Detalles del horario creados: {detalles.count()} (Esperado: 5)")
    assert detalles.count() == 5
    for det in detalles:
        assert str(det.hora_inicio_entrada) == "08:00:00"
        assert str(det.hora_fin_salida) == "19:00:00"
        
    uh_count = UsuarioHorario.objects.filter(horario=horario_db, usuario=operator_user, activo=True).count()
    print(f"[OK] Asignación de usuario creada: {uh_count} (Esperado: 1)")
    assert uh_count == 1
    
    # ----------------------------------------------------
    # TEST 2: Personalizado por Días
    # ----------------------------------------------------
    payload_personalizado = {
        "modo": "personalizado_por_dias",
        "sede_id": sede.id,
        "nombre": "Horario Personalizado Test",
        "descripcion": "Horario por día personalizado",
        "dias": [
            {
                "dia_semana": "lunes",
                "hora_inicio_entrada": "08:00:00",
                "hora_fin_entrada": "09:00:00",
                "hora_inicio_salida": "17:00:00",
                "hora_fin_salida": "19:00:00"
            },
            {
                "dia_semana": "martes",
                "hora_inicio_entrada": "10:00:00",
                "hora_fin_entrada": "11:00:00",
                "hora_inicio_salida": "20:00:00",
                "hora_fin_salida": "22:00:00"
            }
        ],
        "usuarios_ids": [operator_user.id]
    }
    
    request = factory.post('/api/horarios/', payload_personalizado, format='json')
    force_authenticate(request, user=admin_user)
    response = view(request)
    
    print(f"[*] Test 2 Response Status: {response.status_code}")
    assert response.status_code == 201, f"Error: {response.data}"
    
    horario_p_id = response.data['id']
    horario_p_db = Horario.objects.get(id=horario_p_id)
    print(f"[OK] Horario Personalizado creado con ID: {horario_p_db.id}")
    assert horario_p_db.tipo_configuracion == 'personalizado_por_dias'
    
    detalles_p = HorarioDetalle.objects.filter(horario=horario_p_db).order_by('dia_semana')
    print(f"[OK] Detalles personalizados creados: {detalles_p.count()} (Esperado: 2)")
    assert detalles_p.count() == 2
    
    lunes_det = detalles_p.get(dia_semana='lunes')
    assert str(lunes_det.hora_inicio_entrada) == "08:00:00"
    
    martes_det = detalles_p.get(dia_semana='martes')
    assert str(martes_det.hora_inicio_entrada) == "10:00:00"
    assert str(martes_det.hora_fin_salida) == "22:00:00"
    
    uh_p_count = UsuarioHorario.objects.filter(horario=horario_p_db, usuario=operator_user, activo=True).count()
    uh_old_count = UsuarioHorario.objects.filter(horario=horario_db, usuario=operator_user, activo=True).count()
    print(f"[OK] Nueva asignación activa: {uh_p_count} (Esperado: 1), Antigua asignación activa: {uh_old_count} (Esperado: 0)")
    assert uh_p_count == 1
    assert uh_old_count == 0
    
    # Cleanup database records
    UsuarioHorario.objects.filter(usuario=operator_user).delete()
    HorarioDetalle.objects.filter(horario__in=[horario_db, horario_p_db]).delete()
    horario_db.delete()
    horario_p_db.delete()
    sede.delete()
    
    print("\n=== PRUEBA DE PAYLOADS COMPLETA Y EXITOSA ===")

if __name__ == '__main__':
    run_payload_tests()
