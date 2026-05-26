import os
import sys
from datetime import date, time

sys.path.append('d:/Joseph/FinControl/FinControl-Back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')

import django
django.setup()

from api.models import Sede, Usuario, Horario, HorarioDetalle, UsuarioHorario
from api.views import check_usuario_horario_overlap, deactivate_dependent_relations
from django.db import transaction

def run_tests():
    print("Iniciando pruebas de validación de horarios...")
    
    # Usar una transacción para no guardar basura en la BD real
    with transaction.atomic():
        # 1. Obtener o crear una sede y un usuario de prueba
        sede, _ = Sede.objects.get_or_create(nombre="Sede Pruebas", defaults={"latitud": -12.04318, "longitud": -77.02824})
        usuario, _ = Usuario.objects.get_or_create(
            dni="99999999", 
            defaults={
                "email": "test_operador@fincontrol.com", 
                "nombre_completo": "Test Operador",
                "sede": sede
            }
        )
        
        # 2. Crear Horario A: Lunes 08:00 a 17:00
        horario_a = Horario.objects.create(nombre="Horario A (Lunes 08-17)", sede=sede, tipo_configuracion="general_unico", activo=True)
        HorarioDetalle.objects.create(
            horario=horario_a,
            dia_semana="lunes",
            hora_inicio_entrada=time(8, 0),
            hora_fin_entrada=time(9, 0),
            hora_inicio_salida=time(16, 0),
            hora_fin_salida=time(17, 0),
            activo=True
        )
        
        # 3. Crear Horario B (Se cruza): Lunes 10:00 a 19:00
        horario_b = Horario.objects.create(nombre="Horario B (Lunes 10-19)", sede=sede, tipo_configuracion="general_unico", activo=True)
        HorarioDetalle.objects.create(
            horario=horario_b,
            dia_semana="lunes",
            hora_inicio_entrada=time(10, 0),
            hora_fin_entrada=time(11, 0),
            hora_inicio_salida=time(18, 0),
            hora_fin_salida=time(19, 0),
            activo=True
        )
        
        # 4. Crear Horario C (Toca límite pero no se cruza): Lunes 17:00 a 22:00
        horario_c = Horario.objects.create(nombre="Horario C (Lunes 17-22)", sede=sede, tipo_configuracion="general_unico", activo=True)
        HorarioDetalle.objects.create(
            horario=horario_c,
            dia_semana="lunes",
            hora_inicio_entrada=time(17, 0),
            hora_fin_entrada=time(18, 0),
            hora_inicio_salida=time(21, 0),
            hora_fin_salida=time(22, 0),
            activo=True
        )

        # 5. Crear Horario D (Otro día): Martes 08:00 a 17:00
        horario_d = Horario.objects.create(nombre="Horario D (Martes 08-17)", sede=sede, tipo_configuracion="general_unico", activo=True)
        HorarioDetalle.objects.create(
            horario=horario_d,
            dia_semana="martes",
            hora_inicio_entrada=time(8, 0),
            hora_fin_entrada=time(9, 0),
            hora_inicio_salida=time(16, 0),
            hora_fin_salida=time(17, 0),
            activo=True
        )

        # Asignar Horario A al usuario
        uh_a = UsuarioHorario.objects.create(
            usuario=usuario,
            horario=horario_a,
            sede=sede,
            vigente_desde=date(2026, 5, 25),
            vigente_hasta=None,
            es_principal=True,
            activo=True
        )
        print("-> Horario A asignado correctamente al usuario.")

        # Test A: Validar que Horario B se cruza
        print("Test 1: Comprobando si Horario B (Lunes 10-19) se cruza...")
        overlap_b = check_usuario_horario_overlap(usuario.id, horario_b.id, date(2026, 5, 25), None)
        assert overlap_b == True, "ERROR: Debió detectar que Horario B se cruza con Horario A."
        print("OK: Cruce detectado correctamente para Horario B.")

        # Test B: Validar que Horario C no se cruza (solo toca límite en 17:00)
        print("Test 2: Comprobando si Horario C (Lunes 17-22) se cruza...")
        overlap_c = check_usuario_horario_overlap(usuario.id, horario_c.id, date(2026, 5, 25), None)
        assert overlap_c == False, "ERROR: Horario C no debió cruzarse (toca en 17:00)."
        print("OK: No se detectó cruce para Horario C (límite limpio).")

        # Test C: Validar que Horario D no se cruza (es otro día)
        print("Test 3: Comprobando si Horario D (Martes 08-17) se cruza...")
        overlap_d = check_usuario_horario_overlap(usuario.id, horario_d.id, date(2026, 5, 25), None)
        assert overlap_d == False, "ERROR: Horario D no debió cruzarse (es martes, A es lunes)."
        print("OK: No se detectó cruce para Horario D.")

        # Test D: Desactivación lógica (baja lógica de Horario A)
        print("Test 4: Comprobando baja lógica en cascada...")
        horario_a.activo = False
        horario_a.save()
        deactivate_dependent_relations(horario_a)
        
        # Verificar estados
        assert HorarioDetalle.objects.filter(horario=horario_a, activo=True).exists() == False, "ERROR: Los detalles de Horario A debieron desactivarse."
        assert UsuarioHorario.objects.filter(horario=horario_a, activo=True).exists() == False, "ERROR: Las asignaciones de Horario A debieron desactivarse."
        print("OK: Baja lógica en cascada desactivó todas las dependencias correctamente.")

        # Forzar rollback para que no quede data en la BD de desarrollo
        transaction.set_rollback(True)
        print("\nTodas las pruebas del Backend pasaron exitosamente! (Transacción revertida)")

if __name__ == "__main__":
    run_tests()
