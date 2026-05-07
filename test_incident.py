from api.models import Usuario, Incidencia
from api.serializers import IncidenciaSerializer
try:
    user = Usuario.objects.get(dni='12345678')
    data = {
        'tipo_incidencia': 'PRUEBA', 
        'descripcion': 'Todo ok', 
        'latitud': -12.0463, 
        'longitud': -77.0427, 
        'dispositivo_info': 'Server Test'
    }
    serializer = IncidenciaSerializer(data=data)
    if serializer.is_valid():
        serializer.save(usuario=user)
        print('GUARDADO EXITOSO')
    else:
        print(f'ERRORES: {serializer.errors}')
except Exception as e:
    print(f'EXCEPCION: {e}')
