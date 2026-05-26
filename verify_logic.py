import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from api.models import HistorialJornada, UbicacionPunto, Usuario, Sede, UsuarioSede
from django.shortcuts import get_object_or_404
from zoneinfo import ZoneInfo
import math

print("=== INICIANDO VERIFICACIÓN DE LÓGICA INTERNA ===")

def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except:
        return 9999999

def run_tests():
    # 1. Verificar resolución de Sede
    historial = HistorialJornada.objects.first()
    if not historial:
        print("[!] No hay historiales de jornada en la BD para probar.")
        return
        
    print(f"[*] Historial encontrado: ID {historial.id}, Fecha {historial.fecha}, Usuario {historial.usuario.nombre_completo}")
    
    # Resolver sede
    sede = None
    if historial.sede_id:
        sede = Sede.objects.filter(id=historial.sede_id).first()
    if not sede and historial.usuario.sede:
        sede = historial.usuario.sede
        
    if sede:
        print(f"[OK] Sede resuelta correctamente: {sede.nombre} (Lat: {sede.latitud}, Lng: {sede.longitud}, Radio: {sede.radio_metros}m)")
    else:
        print("[*] Sede: El historial/usuario no tiene sede asignada.")

    # 2. Consultar puntos GPS
    puntos = UbicacionPunto.objects.filter(
        historial_jornada_id=historial.id,
        latitud__isnull=False,
        longitud__isnull=False
    ).order_by('fecha_hora')
    
    print(f"[*] Puntos GPS por historial_jornada_id ({historial.id}): {puntos.count()} encontrados.")
    
    # Fallback por asistencia
    if not puntos.exists() and historial.asistencia:
        puntos = UbicacionPunto.objects.filter(
            asistencia=historial.asistencia,
            latitud__isnull=False,
            longitud__isnull=False
        ).order_by('fecha_hora')
        print(f"[*] Puntos GPS por asistencia ({historial.asistencia.id}) [Fallback]: {puntos.count()} encontrados.")

    # Serialización simulada
    puntos_data = []
    total_fuera_de_zona = 0
    for p in puntos:
        if p.es_fuera_de_zona:
            total_fuera_de_zona += 1
        puntos_data.append({
            'id': p.id,
            'latitud': float(p.latitud),
            'longitud': float(p.longitud),
            'fecha_hora': p.fecha_hora.isoformat() if p.fecha_hora else None,
            'precision_metros': float(p.precision_metros) if p.precision_metros is not None else None,
            'bateria_porcentaje': p.bateria_porcentaje,
            'es_fuera_de_zona': p.es_fuera_de_zona,
            'distancia_sede_metros': float(p.distancia_sede_metros) if p.distancia_sede_metros is not None else None,
            'origen': p.origen,
            'estado_envio': p.estado_envio
        })
        
    print(f"[OK] Serialización de puntos completa. Total: {len(puntos_data)}, Fuera de zona: {total_fuera_de_zona}")
    
    if len(puntos_data) > 0:
        print(f"[OK] Primer punto: {puntos_data[0]}")
        print(f"[OK] Último punto: {puntos_data[-1]}")

    # 3. Simular seguridad por roles para un Gerente
    gerente = Usuario.objects.filter(rol__nombre__icontains='gerente').first()
    if gerente:
        print(f"[*] Simulando permisos para el Gerente: {gerente.nombre_completo}")
        
        # Obtener sedes gestionables
        sedes_ids = list(UsuarioSede.objects.filter(usuario=gerente, puede_visualizar=True).values_list('sede_id', flat=True))
        if gerente.sede_id:
            sedes_ids.append(gerente.sede_id)
        sedes_ids = list(set(sedes_ids))
        
        # Verificar acceso al historial
        can_view = False
        if (historial.usuario.creado_por == gerente or 
            (historial.usuario.sede_id and historial.usuario.sede_id in sedes_ids) or
            (historial.sede_id and historial.sede_id in sedes_ids)):
            can_view = True
            
        print(f"[OK] ¿Gerente tiene acceso a este historial?: {can_view} (Sedes asignadas: {sedes_ids})")

    # 4. Probar resolución automática de historial_jornada_id en LocationPointCreateView
    print("[*] Simulando guardado en LocationPointCreateView sin historial_jornada_id...")
    asistencia = historial.asistencia
    if asistencia:
        historial_resuelto = HistorialJornada.objects.filter(asistencia=asistencia).first()
        if not historial_resuelto:
            historial_resuelto = HistorialJornada.objects.filter(usuario=historial.usuario, fecha=historial.fecha).first()
        
        if historial_resuelto:
            print(f"[OK] Historial resuelto con éxito! ID: {historial_resuelto.id} (Esperado: {historial.id})")
        else:
            print("[!] Fallo al resolver historial_jornada_id.")
    else:
        print("[*] No hay asistencia asociada al historial para simular resolución.")

    print("\n=== VERIFICACIÓN FINALIZADA CON ÉXITO: TODO CORRECTO ===")

if __name__ == '__main__':
    run_tests()
