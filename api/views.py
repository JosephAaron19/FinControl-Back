from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia, UsuarioSede
from .serializers import (
    SedeSerializer, UsuarioSerializer, UsuarioCreateUpdateSerializer, AsistenciaSerializer, 
    IncidenciaSerializer, CustomTokenObtainPairSerializer,
    ConfiguracionTrackingSerializer, UbicacionPuntoSerializer,
    RolSerializer, TipoIncidenciaSerializer, JornadaConfiguracionSerializer
)
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AttendanceEventView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AsistenciaSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        event_type = request.data.get('type')  # 'ENTRADA', 'SALIDA', 'INICIO_BREAK', 'FIN_BREAK'
        lat = request.data.get('latitud')
        lon = request.data.get('longitud')
        device_info = request.data.get('device_info', '')

        if not all([event_type, lat, lon]):
            return Response({'error': 'Faltan datos obligatorios (type, latitud, longitud)'}, status=status.HTTP_400_BAD_REQUEST)

        # Validar ubicación
        sede = user.sede
        if not sede:
            return Response({'error': 'El usuario no tiene una sede asignada'}, status=status.HTTP_400_BAD_REQUEST)

        distance = calculate_distance(lat, lon, sede.latitud, sede.longitud)
        is_in_zone = distance <= sede.radio_metros
        
        today = timezone.now().date()
        
        asistencia_hoy = Asistencia.objects.filter(usuario=user, fecha=today).first()

        # Validaciones de Estado
        if event_type == 'ENTRADA':
            if asistencia_hoy and asistencia_hoy.hora_entrada:
                return Response({'error': 'Ya tiene una entrada registrada para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            
            from .models import JornadaConfiguracion
            now = timezone.localtime(timezone.now())
            dias_map = {
                0: 'lunes', 1: 'martes', 2: 'miercoles', 
                3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'
            }
            day_str = dias_map[now.weekday()]
            
            config = JornadaConfiguracion.objects.filter(sede=sede, dia_semana=day_str, activo=True).first()
            
            if not config:
                return Response({'error': f'No hay una jornada configurada o activa para el día {day_str} en esta sede.'}, status=status.HTTP_400_BAD_REQUEST)
                
            current_time = now.time()
            if not (config.hora_inicio_marcacion <= current_time <= config.hora_fin_marcacion):
                return Response({'error': f'Fuera de horario permitido. El horario de marcación es de {config.hora_inicio_marcacion} a {config.hora_fin_marcacion}.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'INICIO_BREAK':
            if not asistencia_hoy or not asistencia_hoy.hora_entrada:
                return Response({'error': 'No puede iniciar break sin haber marcado entrada.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_inicio_break:
                return Response({'error': 'Ya tiene un break registrado para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'No puede iniciar break si ya marcó salida.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'FIN_BREAK':
            if not asistencia_hoy or not asistencia_hoy.hora_inicio_break:
                return Response({'error': 'No puede finalizar break sin haberlo iniciado.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_fin_break:
                return Response({'error': 'Ya finalizó el break de hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'No puede finalizar break si ya marcó salida.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'SALIDA':
            if not asistencia_hoy or not asistencia_hoy.hora_entrada:
                return Response({'error': 'No puede marcar salida sin haber marcado entrada.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'Ya marcó salida para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_inicio_break and not asistencia_hoy.hora_fin_break:
                return Response({'error': 'No puede marcar salida con un break activo. Finalice el break primero.'}, status=status.HTTP_400_BAD_REQUEST)

        asistencia, created = Asistencia.objects.get_or_create(usuario=user, fecha=today)

        from .models import HistorialJornada
        historial, h_created = HistorialJornada.objects.get_or_create(
            asistencia=asistencia,
            defaults={
                'usuario': user,
                'fecha': today,
                'sede_id': sede.id if sede else None
            }
        )

        now = timezone.now()
        
        if event_type == 'ENTRADA':
            asistencia.hora_entrada = now
            asistencia.latitud_entrada = lat
            asistencia.longitud_entrada = lon
            
            historial.hora_entrada = now
            historial.latitud_entrada = lat
            historial.longitud_entrada = lon
            historial.entrada_fuera_de_zona = not is_in_zone
            historial.distancia_entrada_metros = distance
            historial.dispositivo_entrada = device_info
            historial.estado_jornada = 'en_proceso'
            
        elif event_type == 'SALIDA':
            asistencia.hora_salida = now
            asistencia.latitud_salida = lat
            asistencia.longitud_salida = lon
            
            historial.hora_salida = now
            historial.latitud_salida = lat
            historial.longitud_salida = lon
            historial.salida_fuera_de_zona = not is_in_zone
            historial.distancia_salida_metros = distance
            historial.dispositivo_salida = device_info
            historial.estado_jornada = 'cerrada'
            historial.cerrado = True
            historial.cerrado_at = now
            
        elif event_type == 'INICIO_BREAK':
            asistencia.hora_inicio_break = now
            
            historial.hora_inicio_break = now
            historial.latitud_inicio_break = lat
            historial.longitud_inicio_break = lon
            historial.inicio_break_fuera_de_zona = not is_in_zone
            historial.distancia_inicio_break_metros = distance
            historial.dispositivo_inicio_break = device_info
            historial.estado_jornada = 'en_break'
            
        elif event_type == 'FIN_BREAK':
            asistencia.hora_fin_break = now
            
            historial.hora_fin_break = now
            historial.latitud_fin_break = lat
            historial.longitud_fin_break = lon
            historial.fin_break_fuera_de_zona = not is_in_zone
            historial.distancia_fin_break_metros = distance
            historial.dispositivo_fin_break = device_info
            historial.estado_jornada = 'en_proceso'
        else:
            return Response({'error': 'Tipo de evento inválido'}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar estado si está fuera de zona
        if not is_in_zone:
            asistencia.estado = 'Observado'
        elif asistencia.estado == 'Sin Marcar':
            asistencia.estado = 'Válido'

        asistencia.dispositivo_info = device_info
        asistencia.save()
        
        historial.asistencia = asistencia
        historial.cantidad_marcaciones += 1
        historial.save()

        # Registrar el evento detallado en la nueva tabla
        AsistenciaEvento.objects.create(
            asistencia=asistencia,
            usuario=user,
            sede_id=sede.id if sede else None,
            tipo_evento=event_type,
            latitud=lat,
            longitud=lon,
            dispositivo_info=device_info,
            es_fuera_de_zona=not is_in_zone,
            distancia_sede_metros=distance
        )

        # Registrar el punto geográfico para que aparezca en la ruta/mapa de seguimiento
        from .models import UbicacionPunto
        UbicacionPunto.objects.create(
            usuario=user,
            asistencia=asistencia,
            historial_jornada_id=historial.id,
            latitud=lat,
            longitud=lon,
            es_fuera_de_zona=not is_in_zone,
            distancia_sede_metros=distance,
            origen='manual',
            dispositivo_info=device_info
        )

        return Response({
            'asistencia_id': asistencia.id,
            'historial_jornada_id': historial.id, 
            'message': f'Evento {event_type} registrado correctamente',
            'is_in_zone': is_in_zone,
            'distance_meters': round(distance, 2),
            'status': asistencia.estado,
            'detener_tracking': event_type == 'SALIDA'
        }, status=status.HTTP_200_OK)

class AttendanceHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AsistenciaSerializer

    def get_queryset(self):
        return Asistencia.objects.filter(usuario=self.request.user).order_by('-fecha')

class IncidentCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IncidenciaSerializer

    def perform_create(self, serializer):
        # Obtener la asistencia del día actual para vincular la incidencia si existe
        today = timezone.now().date()
        asistencia = Asistencia.objects.filter(usuario=self.request.user, fecha=today).first()
        serializer.save(usuario=self.request.user, asistencia=asistencia)

class TrackingConfigView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ConfiguracionTrackingSerializer

    def get_object(self):
        config, _ = ConfiguracionTracking.objects.get_or_create(id=1)
        return config

class LocationPointCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UbicacionPuntoSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        
        # Obtener IDs del request
        asistencia_id = request.data.get('asistencia')
        historial_jornada_id = request.data.get('historial_jornada_id')

        # Buscar asistencia: Por ID enviado o por usuario+fecha
        asistencia = None
        if asistencia_id:
            asistencia = Asistencia.objects.filter(id=asistencia_id, usuario=user).first()
        
        if not asistencia:
            asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()

        # Validar si tiene jornada activa
        if not asistencia or not asistencia.hora_entrada or asistencia.hora_salida:
            return Response({'error': 'No hay jornada activa para este usuario', 'detener_tracking': True}, status=status.HTTP_400_BAD_REQUEST)

        lat = request.data.get('latitud')
        lon = request.data.get('longitud')
        
        # Calcular distancia
        sede = user.sede
        distance = 0
        is_outside = False
        if sede and lat and lon:
            distance = calculate_distance(lat, lon, sede.latitud, sede.longitud)
            is_outside = distance > sede.radio_metros

        # Validar origen contra check constraint de la BD
        origen = request.data.get('origen', 'servicio_background')
        valid_origenes = ['app_movil', 'segundo_plano', 'servicio_background', 'manual']
        if origen not in valid_origenes:
            origen = 'servicio_background'

        # Guardar punto
        punto = UbicacionPunto.objects.create(
            usuario=user,
            asistencia=asistencia,
            historial_jornada_id=historial_jornada_id,
            latitud=lat,
            longitud=lon,
            precision_metros=request.data.get('precision_metros'),
            bateria_porcentaje=request.data.get('bateria_porcentaje'),
            es_fuera_de_zona=is_outside,
            distancia_sede_metros=distance,
            origen=origen,
            dispositivo_info=request.data.get('dispositivo_info')
        )

        return Response({
            'status': 'Punto registrado',
            'es_fuera_de_zona': is_outside,
            'distance_meters': round(distance, 2),
            'detener_tracking': False
        }, status=status.HTTP_201_CREATED)

class JourneyTrackingHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UbicacionPuntoSerializer

    def get_queryset(self):
        asistencia_id = self.kwargs.get('asistencia_id')
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = UbicacionPunto.objects.filter(asistencia_id=asistencia_id).order_by('fecha_hora')
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        # Validar si puede ver la asistencia
        asistencia = Asistencia.objects.filter(id=asistencia_id).first()
        if not asistencia:
            return UbicacionPunto.objects.none()
            
        target_user = asistencia.usuario
        
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_asignadas = UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True)
            if target_user.creado_por == user or target_user.sede_id in sedes_asignadas:
                return queryset
            return UbicacionPunto.objects.none()
        elif 'operador' in rol_nombre:
            if target_user == user:
                return queryset
            return UbicacionPunto.objects.none()
            
        return UbicacionPunto.objects.none()

class UserProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user

# Web Dashboard Views
class RolListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Rol.objects.all()
    serializer_class = RolSerializer

class TipoIncidenciaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = TipoIncidencia.objects.all()
    serializer_class = TipoIncidenciaSerializer

class SedeListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SedeSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Sede.objects.all()
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            return queryset
        elif 'operador' in rol_nombre:
            if user.sede_id:
                return queryset.filter(id=user.sede_id)
            return Sede.objects.none()
            
        return Sede.objects.none()

class SedeDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SedeSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Sede.objects.all()
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            return queryset
        elif 'operador' in rol_nombre:
            if user.sede_id:
                return queryset.filter(id=user.sede_id)
            return Sede.objects.none()
            
        return Sede.objects.none()

class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Usuario.objects.all().order_by('-creado_at')
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            # Gerente ve solo operadores de sus sedes asignadas
            sedes_asignadas = UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True)
            return queryset.filter(
                rol__nombre__icontains='operador',
                sede_id__in=sedes_asignadas
            )
        elif 'operador' in rol_nombre:
            return queryset.filter(id=user.id)
            
        return queryset.filter(id=user.id)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UsuarioCreateUpdateSerializer
        return UsuarioSerializer

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        usuario = self.get_object()
        new_password = request.data.get('password')
        if not new_password:
            return Response({'error': 'La contraseña es requerida.'}, status=status.HTTP_400_BAD_REQUEST)
        
        usuario.set_password(new_password)
        usuario.debe_cambiar_password = request.data.get('debe_cambiar_password', True)
        usuario.save()
        return Response({'status': 'Contraseña actualizada correctamente.'})

class IncidenciaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IncidenciaSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Incidencia.objects.all().order_by('-fecha_hora_reporte')
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_asignadas = UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True)
            return queryset.filter(usuario__sede_id__in=sedes_asignadas)
        elif 'operador' in rol_nombre:
            return queryset.filter(usuario=user)
            
        return queryset.filter(usuario=user)

class AsistenciaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AsistenciaSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Asistencia.objects.all().order_by('-fecha')
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return queryset
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_asignadas = UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True)
            return queryset.filter(usuario__sede_id__in=sedes_asignadas)
        elif 'operador' in rol_nombre:
            return queryset.filter(usuario=user)
            
        return queryset.filter(usuario=user)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from django.utils.dateparse import parse_datetime

class SyncStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        last_sync_str = request.query_params.get('last_sync')
        
        # Obtenemos los actualizado_at
        user_ts = user.actualizado_at
        
        config = ConfiguracionTracking.objects.first()
        config_ts = config.actualizado_at if config else None
        
        today = timezone.now().date()
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        asistencia_ts = asistencia.actualizado_at if asistencia else None
        
        # Encontramos el máximo de los timestamps válidos
        timestamps = [ts for ts in [user_ts, config_ts, asistencia_ts] if ts is not None]
        max_ts = max(timestamps) if timestamps else timezone.now()
        
        has_changes = False
        if last_sync_str:
            last_sync_dt = parse_datetime(last_sync_str)
            if last_sync_dt:
                # Comparamos datetimes de forma robusta
                if max_ts > last_sync_dt:
                    has_changes = True
            else:
                # Fallback seguro si la fecha no es válida
                if max_ts.isoformat() > last_sync_str:
                    has_changes = True
        else:
            has_changes = True
            
        return Response({
            'has_changes': has_changes,
            'timestamp': max_ts.isoformat()
        })

class JornadaEstadoMarcacionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        sede = user.sede
        
        if not sede:
            return Response({'error': 'El usuario no tiene una sede asignada'}, status=status.HTTP_400_BAD_REQUEST)
            
        now = timezone.localtime(timezone.now())
        today = now.date()
        
        # Mapeo de días de la semana a español (según DB)
        dias_map = {
            0: 'lunes',
            1: 'martes',
            2: 'miercoles',
            3: 'jueves',
            4: 'viernes',
            5: 'sabado',
            6: 'domingo'
        }
        day_str = dias_map[now.weekday()]
        
        # Importar modelo localmente
        from .models import JornadaConfiguracion, HistorialJornada, Asistencia
        
        # 3. Buscar configuración activa para la sede y el día
        config = JornadaConfiguracion.objects.filter(sede=sede, dia_semana=day_str, activo=True).first()
        
        response_data = {
            'hora_servidor': now.strftime('%H:%M:%S'),
            'dia_servidor': day_str
        }
        
        if not config:
            response_data.update({
                'puede_marcar_entrada': False,
                'mensaje': f'No hay una jornada configurada o activa para el día {day_str} en esta sede.'
            })
            return Response(response_data, status=status.HTTP_200_OK)
            
        current_time = now.time()
        
        # 4. Validar si la hora actual está en el rango
        within_hours = config.hora_inicio_marcacion <= current_time <= config.hora_fin_marcacion
        
        # 5. Validar si ya tiene asistencia o jornada creada
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        historial = HistorialJornada.objects.filter(usuario=user, fecha=today).first()
        
        # 8. Si ya marcó entrada
        if asistencia and asistencia.hora_entrada:
            # 9. Si ya marcó salida y está cerrada
            if asistencia.hora_salida or (historial and historial.cerrado):
                response_data.update({
                    'puede_marcar_entrada': False,
                    'estado_jornada': 'cerrada',
                    'mensaje': 'Ya completó su jornada de hoy.'
                })
            else:
                response_data.update({
                    'puede_marcar_entrada': False,
                    'estado_jornada': historial.estado_jornada if historial else 'en_proceso',
                    'mensaje': 'Ya marcó entrada. Su jornada está en curso.'
                })
            return Response(response_data, status=status.HTTP_200_OK)
            
        # 6. Si no tiene jornada y está dentro del horario
        if within_hours:
            response_data.update({
                'puede_marcar_entrada': True,
                'estado_jornada': 'no_iniciada',
                'mensaje': 'Puede marcar entrada.'
            })
        else:
            # 7. Si está fuera del horario
            response_data.update({
                'puede_marcar_entrada': False,
                'estado_jornada': 'no_iniciada',
                'mensaje': f'Fuera de horario permitido. El horario de marcación es de {config.hora_inicio_marcacion} a {config.hora_fin_marcacion}.'
            })
            
        return Response(response_data, status=status.HTTP_200_OK)


class ActividadHoyView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        
        current_user = request.user
        rol_nombre = current_user.rol.nombre.lower() if current_user.rol else ''
        
        # Base query: solo operadores activos
        usuarios = Usuario.objects.filter(activo=True, rol__nombre__icontains='operador').select_related('sede', 'rol')
        
        # Aplicar restricciones por rol
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            # Gerente ve solo operadores de sus sedes asignadas
            sedes_asignadas = UsuarioSede.objects.filter(usuario=current_user, puede_visualizar=True).values_list('sede_id', flat=True)
            usuarios = usuarios.filter(sede_id__in=sedes_asignadas)
        elif 'operador' in rol_nombre:
            # Operador solo se ve a sí mismo
            usuarios = usuarios.filter(id=current_user.id)
        else:
            # Administradores y Superadmins ven todos los operadores activos
            pass
        
        data = []
        
        for user in usuarios:
            # Asistencia de hoy
            asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
            
            # Incidencias de hoy
            incidencias_count = Incidencia.objects.filter(usuario=user, fecha_hora_reporte__date=today).count()
            
            # Puntos GPS de hoy
            puntos_gps = UbicacionPunto.objects.filter(usuario=user, fecha=today)
            puntos_count = puntos_gps.count()
            ultimo_punto = puntos_gps.order_by('-fecha_hora').first()
            
            # Determinar estado
            estado = 'Sin Marcar'
            if asistencia:
                if asistencia.hora_salida:
                    estado = 'Salida'
                elif asistencia.hora_fin_break:
                    estado = 'Presente'
                elif asistencia.hora_inicio_break:
                    estado = 'En Break'
                elif asistencia.hora_entrada:
                    estado = 'Presente'
                
                if asistencia.estado == 'Observado':
                    estado = 'Observado'
                    
            # Fuera de zona flag
            fuera_de_zona = False
            if ultimo_punto:
                fuera_de_zona = ultimo_punto.es_fuera_de_zona
            elif asistencia and asistencia.estado == 'Observado':
                fuera_de_zona = True
                
            data.append({
                'id': user.id,
                'dni': user.dni,
                'nombre_completo': user.nombre_completo,
                'sede': user.sede.nombre if user.sede else '-',
                'cargo': user.cargo,
                'rol': user.rol.nombre if user.rol else '-',
                'estado': estado,
                'hora_entrada': asistencia.hora_entrada if asistencia else None,
                'hora_inicio_break': asistencia.hora_inicio_break if asistencia else None,
                'hora_fin_break': asistencia.hora_fin_break if asistencia else None,
                'hora_salida': asistencia.hora_salida if asistencia else None,
                'incidencias': incidencias_count,
                'puntos_gps': puntos_count,
                'fuera_de_zona': fuera_de_zona,
                'ultima_ubicacion': {
                    'latitud': ultimo_punto.latitud if ultimo_punto else None,
                    'longitud': ultimo_punto.longitud if ultimo_punto else None,
                    'distancia': ultimo_punto.distancia_sede_metros if ultimo_punto else None
                } if ultimo_punto else None
            })
            
        return Response(data)

class ActividadDetalleUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        today = timezone.now().date()
        user = Usuario.objects.filter(id=pk).first()
        
        if not user:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
        # Validar permisos
        current_user = request.user
        rol_nombre = current_user.rol.nombre.lower() if current_user.rol else ''
        
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            # Validar si puede ver este usuario
            sedes_asignadas = UsuarioSede.objects.filter(usuario=current_user, puede_visualizar=True).values_list('sede_id', flat=True)
            if user.creado_por != current_user and user.sede_id not in sedes_asignadas:
                return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        elif 'operador' in rol_nombre and current_user.id != user.id:
            return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
            
        # Asistencia de hoy
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        
        # Incidencias de hoy
        incidencias = Incidencia.objects.filter(usuario=user, fecha_hora_reporte__date=today).order_by('-fecha_hora_reporte')
        
        # Puntos GPS de hoy
        puntos_gps = UbicacionPunto.objects.filter(usuario=user, fecha=today).order_by('fecha_hora')
        
        puntos_data = []
        for p in puntos_gps:
            puntos_data.append({
                'id': p.id,
                'latitud': p.latitud,
                'longitud': p.longitud,
                'precision_metros': p.precision_metros,
                'bateria_porcentaje': p.bateria_porcentaje,
                'es_fuera_de_zona': p.es_fuera_de_zona,
                'distancia_sede_metros': p.distancia_sede_metros,
                'origen': p.origen,
                'estado_envio': p.estado_envio,
                'fecha_hora': p.fecha_hora,
                'dispositivo_info': p.dispositivo_info
            })
            
        incidencias_data = []
        for inc in incidencias:
            incidencias_data.append({
                'id': inc.id,
                'tipo': inc.tipo_incidencia_0.nombre if inc.tipo_incidencia_0 else inc.tipo_incidencia,
                'descripcion': inc.descripcion,
                'fecha_hora_reporte': inc.fecha_hora_reporte,
                'estado': inc.estado_revision
            })
            
        ultimo_punto = puntos_gps.last()
        
        data = {
            'usuario': {
                'id': user.id,
                'dni': user.dni,
                'nombre_completo': user.nombre_completo,
                'sede': user.sede.nombre if user.sede else '-',
                'cargo': user.cargo
            },
            'asistencia': {
                'hora_entrada': asistencia.hora_entrada if asistencia else None,
                'hora_inicio_break': asistencia.hora_inicio_break if asistencia else None,
                'hora_fin_break': asistencia.hora_fin_break if asistencia else None,
                'hora_salida': asistencia.hora_salida if asistencia else None,
                'estado': asistencia.estado if asistencia else 'Sin Marcar'
            },
            'resumen_gps': {
                'total_puntos': puntos_gps.count(),
                'puntos_fuera_zona': puntos_gps.filter(es_fuera_de_zona=True).count(),
                'ultima_hora': ultimo_punto.fecha_hora if ultimo_punto else None,
                'ultima_bateria': ultimo_punto.bateria_porcentaje if ultimo_punto else None,
                'ultima_precision': ultimo_punto.precision_metros if ultimo_punto else None,
                'es_fuera_de_zona': ultimo_punto.es_fuera_de_zona if ultimo_punto else False
            },
            'puntos_gps': puntos_data,
            'incidencias': incidencias_data
        }
        
        return Response(data)

class JornadaConfiguracionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JornadaConfiguracionSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        from .models import JornadaConfiguracion, UsuarioSede
        
        if 'admin' in rol_nombre or 'superadmin' in rol_nombre:
            return JornadaConfiguracion.objects.all()
            
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_asignadas = UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True)
            return JornadaConfiguracion.objects.filter(sede_id__in=sedes_asignadas)
            
        return JornadaConfiguracion.objects.none()

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(actualizado_por=self.request.user)

