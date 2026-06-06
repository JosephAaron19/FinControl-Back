import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fincontrol_backend.settings')
django.setup()

from django.utils import timezone
from api.models import Usuario, Asistencia, HistorialJornada, JornadaActividad
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
import json

def test_jornada_actividad_upload():
    print("=== STARTING JORNADA ACTIVIDAD UPLOAD TEST ===")
    
    # 1. Get an adviser
    user = Usuario.objects.filter(rol__nombre__icontains='asesor').first()
    if not user:
        print("[!] No adviser user found in database.")
        # Try any user
        user = Usuario.objects.first()
        if not user:
            print("[!] No users in the database at all.")
            return

    print(f"[*] Testing with user: {user.nombre_completo} (ID: {user.id}, Role: {user.rol.nombre if user.rol else 'None'})")
    
    # 2. Ensure Asistencia and HistorialJornada exist for today
    today = timezone.now().date()
    asistencia, created_asist = Asistencia.objects.get_or_create(
        usuario=user,
        fecha=today,
        defaults={
            'hora_entrada': timezone.now(),
            'estado': 'Válido',
        }
    )
    if not asistencia.hora_entrada:
        asistencia.hora_entrada = timezone.now()
        asistencia.save()
        
    historial, created_hist = HistorialJornada.objects.get_or_create(
        usuario=user,
        fecha=today,
        defaults={
            'asistencia': asistencia,
            'fecha': today,
        }
    )
    
    # Ensure no active activity in process
    JornadaActividad.objects.filter(usuario=user, estado_actividad='en_proceso').delete()
    
    # Minimal valid 1x1 GIF bytes
    gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    
    # 3. Create mock image file
    mock_image = SimpleUploadedFile(
        name='test_image.gif',
        content=gif_bytes,
        content_type='image/gif'
    )
    
    # 4. Use APIClient to call the viewset
    client = APIClient()
    client.force_authenticate(user=user)
    
    data = {
        'tipo_actividad': 'VISITA',
        'titulo': 'Test Activity with Photo',
        'descripcion': 'Testing activity upload from script',
        'cliente_nombre': 'Cliente de Prueba',
        'latitud_inicio': -12.046374,
        'longitud_inicio': -77.042793,
        'dispositivo_inicio': 'Python DRF Test Client',
        'evidencia_inicio_url': mock_image
    }
    
    print("[*] Sending POST request to /api/jornada-actividades/iniciar/ ...")
    try:
        response = client.post('/api/jornada-actividades/iniciar/', data=data, format='multipart')
        print(f"[*] Response Status Code: {response.status_code}")
        print(f"[*] Response Data: {response.content.decode('utf-8')}")
    except Exception as e:
        print("[ERROR] Exception raised during request:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_jornada_actividad_upload()
