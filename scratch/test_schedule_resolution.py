import os
import sys
import django
from datetime import datetime, date, time

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import Sede, Usuario, Rol, Horario, HorarioDetalle, UsuarioHorario, IntercambioHorario, JornadaConfiguracion
from api.views import resolve_usuario_horario_para_fecha, get_active_horario_detalle

def test_resolution():
    print("==================================================")
    print("TESTING USER SCHEDULE RESOLUTION PRIORITY LOGIC")
    print("==================================================")
    
    # 1. Fetch/Create test structures
    # We will look up a real user and sede to avoid database contamination or constraints issues,
    # or run in dry-run/transaction block.
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # Get a test user (operator or asesor)
            user = Usuario.objects.filter(rol__nombre__iregex=r'(operador|asesor)', is_active=True).first()
            if not user:
                print("No active Operator/Asesor user found in DB to perform live mock test.")
                return
            
            sede = user.sede
            print(f"Test User: {user.nombre_completo} (ID: {user.id})")
            print(f"Test Sede: {sede.nombre} (ID: {sede.id})")
            
            test_date = date(2026, 6, 1) # A Monday
            print(f"Test Date: {test_date} (lunes)")
            
            # --- PHASE A: Sin Horario ---
            print("\n--- Phase A: Expect 'sin_horario' ---")
            # Deactivate any active schedules or swaps for this date temporarily
            UsuarioHorario.objects.filter(usuario=user).update(activo=False)
            IntercambioHorario.objects.filter(usuario_solicitante=user).update(activo=False)
            IntercambioHorario.objects.filter(usuario_reemplazo=user).update(activo=False)
            JornadaConfiguracion.objects.filter(sede=sede, dia_semana='lunes').update(activo=False)
            
            horario_info = get_active_horario_detalle(user, test_date)
            print(f"Resolved Name: {horario_info['nombre']}")
            print(f"Resolved Origen: {horario_info['origen']}")
            assert horario_info['origen'] == 'sin_horario', "Failed Phase A: should be 'sin_horario'"
            
            # --- PHASE B: Sede Respaldo (Fallback) ---
            print("\n--- Phase B: Expect 'sede_respaldo' (fallback) ---")
            JornadaConfiguracion.objects.update_or_create(
                sede=sede,
                dia_semana='lunes',
                defaults={
                    'hora_inicio_marcacion': time(8, 0),
                    'hora_fin_marcacion': time(9, 0),
                    'hora_inicio_salida': time(17, 0),
                    'hora_fin_salida': time(19, 0),
                    'activo': True
                }
            )
            horario_info = get_active_horario_detalle(user, test_date)
            print(f"Resolved Name: {horario_info['nombre']}")
            print(f"Resolved Origen: {horario_info['origen']}")
            assert horario_info['origen'] == 'sede_respaldo', "Failed Phase B: should be 'sede_respaldo'"
            
            # --- PHASE C: Horario Asignado (Usuario) ---
            print("\n--- Phase C: Expect 'usuario' (Schedule overrides backup) ---")
            horario = Horario.objects.create(
                sede=sede,
                nombre="Test Horario Especial Lunes",
                activo=True
            )
            HorarioDetalle.objects.create(
                horario=horario,
                dia_semana='lunes',
                hora_inicio_entrada=time(9, 0),
                hora_fin_entrada=time(10, 0),
                hora_inicio_salida=time(18, 0),
                hora_fin_salida=time(20, 0),
                activo=True
            )
            UsuarioHorario.objects.create(
                usuario=user,
                horario=horario,
                sede=sede,
                vigente_desde=test_date,
                es_principal=True,
                activo=True
            )
            horario_info = get_active_horario_detalle(user, test_date)
            print(f"Resolved Name: {horario_info['nombre']}")
            print(f"Resolved Origen: {horario_info['origen']}")
            print(f"Resolved Entrada Rango: {horario_info['hora_inicio_entrada']} a {horario_info['hora_fin_entrada']}")
            assert horario_info['origen'] == 'usuario', "Failed Phase C: should be 'usuario'"
            assert horario_info['hora_inicio_entrada'] == time(9, 0), "Failed Phase C: entrada mismatch"
            
            # --- PHASE D: Intercambio Aprobado ---
            print("\n--- Phase D: Expect 'intercambio' (Approved swap overrides user schedule) ---")
            # Create another user and schedule to swap with
            another_user = Usuario.objects.filter(rol__nombre__iregex=r'(operador|asesor)', is_active=True).exclude(id=user.id).first()
            if another_user:
                horario_another = Horario.objects.create(
                    sede=sede,
                    nombre="Test Turno Tarde",
                    activo=True
                )
                HorarioDetalle.objects.create(
                    horario=horario_another,
                    dia_semana='lunes',
                    hora_inicio_entrada=time(14, 0),
                    hora_fin_entrada=time(15, 0),
                    hora_inicio_salida=time(22, 0),
                    hora_fin_salida=time(23, 0),
                    activo=True
                )
                
                # Register exchange (user swaps with another_user)
                # user (solicitante) original is 'horario'
                # another_user (reemplazo) original is 'horario_another'
                # Approved swap assigns the replacement's original to the solicitor
                IntercambioHorario.objects.create(
                    sede=sede,
                    usuario_solicitante=user,
                    usuario_reemplazo=another_user,
                    fecha_intercambio=test_date,
                    horario_solicitante_original=horario,
                    horario_reemplazo_original=horario_another,
                    estado='aprobado',
                    activo=True
                )
                
                horario_info = get_active_horario_detalle(user, test_date)
                print(f"Resolved Name: {horario_info['nombre']}")
                print(f"Resolved Origen: {horario_info['origen']}")
                print(f"Resolved Entrada Rango: {horario_info['hora_inicio_entrada']} a {horario_info['hora_fin_entrada']}")
                
                assert horario_info['origen'] == 'intercambio', "Failed Phase D: should be 'intercambio'"
                assert horario_info['hora_inicio_entrada'] == time(14, 0), "Failed Phase D: swap schedule mismatch"
                print("\nSwap logic verified successfully!")
            else:
                print("Skipping Phase D: not enough operators in DB to register swap.")

            print("\n==================================================")
            print("ALL PRIORITY RESOLUTION TESTS PASSED SUCCESSFULLY!")
            print("==================================================")
            
            # Rollback transaction to avoid database pollution
            raise Exception("Force rollback of test transaction")
            
    except Exception as e:
        if str(e) == "Force rollback of test transaction":
            print("\nDatabase changes rolled back successfully. Environment clean.")
        else:
            print(f"\nTEST FAILED: {e}")

if __name__ == '__main__':
    test_resolution()
