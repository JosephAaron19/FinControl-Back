from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from zoneinfo import ZoneInfo
from django.db import transaction, models
from django.db.models import Q
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia, UsuarioSede, HistorialJornada, JornadaActividad
from .serializers import (
    SedeSerializer, UsuarioSerializer, UsuarioCreateUpdateSerializer, AsistenciaSerializer, 
    IncidenciaSerializer, CustomTokenObtainPairSerializer,
    ConfiguracionTrackingSerializer, UbicacionPuntoSerializer,
    RolSerializer, TipoIncidenciaSerializer, JornadaConfiguracionSerializer,
    HistorialJornadaSerializer, HistorialJornadaListSerializer, HistorialJornadaDetailSerializer,
    JornadaActividadSerializer
)
import math

# =============================================================================
# REGLA DE ORO DE SEGURIDAD (IMPORTANTE):
# Los Gerentes y Supervisores NUNCA deben ver datos de sedes que no tengan
# asignadas. Esta regla se aplica a Usuarios, Asistencias, Incidencias,
# Historiales y Configuración. NO ROMPER esta restricción en futuras vistas.
# =============================================================================

def get_authorized_sedes_ids(user):
    """Retorna lista de IDs de sedes que el usuario tiene permiso de ver/gestionar."""
    rol_nombre = user.rol.nombre.lower() if user.rol else ''
    if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
        return None # Admin ve todo
        
    sedes_ids = list(UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True))
    if user.sede_id:
        sedes_ids.append(user.sede_id)
    return list(set(sedes_ids))

def calculate_distance(lat1, lon1, lat2, lon2):
    try:
        # Haversine formula
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except (TypeError, ValueError, AttributeError):
        return 9999999  # Retornar una distancia muy grande si hay error de datos

class AttendanceEventView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AsistenciaSerializer

    @transaction.atomic
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

        if sede.latitud is None or sede.longitud is None:
            return Response({'error': 'La sede no tiene coordenadas configuradas. Por favor, contacte al administrador.'}, status=status.HTTP_400_BAD_REQUEST)

        distance = calculate_distance(lat, lon, sede.latitud, sede.longitud)
        is_in_zone = distance <= (sede.radio_metros or 100)
        
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now_local = datetime.now(ZoneInfo('America/Lima'))
        today = now_local.date()
        
        asistencia_hoy = Asistencia.objects.filter(usuario=user, fecha=today).first()

        # Validaciones de Estado
        from .models import JornadaConfiguracion
        dias_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
        day_name = dias_map[now_local.weekday()]
        config = JornadaConfiguracion.objects.filter(sede=sede, dia_semana=day_name, activo=True).first()

        if not config:
            return Response({'error': f'No hay una jornada configurada o activa para el día {day_name} en esta sede.'}, status=status.HTTP_400_BAD_REQUEST)

        current_time = now_local.time()

        if event_type == 'ENTRADA':
            if asistencia_hoy and asistencia_hoy.hora_entrada:
                return Response({'error': 'Ya tiene una entrada registrada para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if current_time < config.hora_inicio_marcacion:
                return Response({'error': f'Aún no puede marcar entrada. El horario de marcación inicia a las {config.hora_inicio_marcacion}.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'INICIO_BREAK':
            if not asistencia_hoy or not asistencia_hoy.hora_entrada:
                return Response({'error': 'Debe marcar entrada antes de iniciar su descanso.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if asistencia_hoy.hora_inicio_break:
                return Response({'error': 'Ya tiene un descanso registrado para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'No puede iniciar descanso si ya marcó salida.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'FIN_BREAK':
            if not asistencia_hoy or not asistencia_hoy.hora_inicio_break:
                return Response({'error': 'No puede finalizar descanso sin haberlo iniciado.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_fin_break:
                return Response({'error': 'Ya finalizó el descanso de hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'No puede finalizar descanso si ya marcó salida.'}, status=status.HTTP_400_BAD_REQUEST)
                
        elif event_type == 'SALIDA':
            if not asistencia_hoy or not asistencia_hoy.hora_entrada:
                return Response({'error': 'No puede marcar salida sin haber marcado entrada.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_salida:
                return Response({'error': 'Ya marcó salida para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
            if asistencia_hoy.hora_inicio_break and not asistencia_hoy.hora_fin_break:
                return Response({'error': 'Debe completar su descanso antes de marcar salida.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar si el asesor tiene una actividad en proceso
            if user.rol and user.rol.nombre.lower() == 'asesor':
                if JornadaActividad.objects.filter(usuario=user, estado_actividad='en_proceso').exists():
                    return Response({'error': 'Tienes una actividad en proceso. Finalízala antes de marcar salida.'}, status=status.HTTP_400_BAD_REQUEST)

            # Validar rango de salida si existe en la configuración
            if config.hora_inicio_salida:
                if current_time < config.hora_inicio_salida:
                    return Response({'error': f'Aún no puede marcar salida. El horario de salida inicia a las {config.hora_inicio_salida}.'}, status=status.HTTP_400_BAD_REQUEST)

        asistencia, created = Asistencia.objects.get_or_create(usuario=user, fecha=today)

        from .models import HistorialJornada
        historial, h_created = HistorialJornada.objects.get_or_create(
            usuario=user,
            fecha=today,
            defaults={
                'asistencia': asistencia,
                'sede_id': sede.id if sede else None
            }
        )
        if not h_created and not historial.asistencia:
            historial.asistencia = asistencia
            historial.save()

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
            
            # Determinar si es puntual o tardanza
            from zoneinfo import ZoneInfo
            now_local = now.astimezone(ZoneInfo('America/Lima'))
            current_time = now_local.time()
            
            # Determinar estado de puntualidad
            if current_time < config.hora_inicio_marcacion:
                asistencia.estado_puntualidad = 'temprano'
            elif current_time <= config.hora_fin_marcacion:
                asistencia.estado_puntualidad = 'puntual'
            else:
                asistencia.estado_puntualidad = 'tardanza'
            
            historial.estado_puntualidad = asistencia.estado_puntualidad
            asistencia.estado = asistencia.estado_puntualidad
            
            # Verificar si tiene una incidencia aprobada para hoy que justifique la tardanza
            from .models import Incidencia
            incidencia_aprobada = Incidencia.objects.filter(
                usuario=user, 
                fecha_hora_reporte__date=today,
                estado_revision='Aprobado'
            ).exists()
            
            if incidencia_aprobada:
                asistencia.estado = 'justificado'
                # Si está justificado, el estado de puntualidad sigue siendo tardanza?
                # El usuario no pidió 'justificado' en estado_puntualidad, así que lo dejamos como tardanza
                # pero el 'estado' general será 'justificado'.
            
            historial.estado_jornada = 'en_proceso'
            
            # Nuevo estado_asistencia
            asistencia.estado_asistencia = 'en_proceso'
            historial.estado_asistencia = 'en_proceso'
            
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
            
            # Nuevo estado_asistencia
            asistencia.estado_asistencia = 'completa'
            historial.estado_asistencia = 'completa'

            # Determinar estado de salida
            from zoneinfo import ZoneInfo
            now_local_exit = now.astimezone(ZoneInfo('America/Lima'))
            time_exit = now_local_exit.time()

            if config.hora_inicio_salida and time_exit < config.hora_inicio_salida:
                 asistencia.estado_salida = 'temprano'
            elif config.hora_fin_salida and time_exit > config.hora_fin_salida:
                 asistencia.estado_salida = 'tardanza'
            else:
                 asistencia.estado_salida = 'puntual'
            
            historial.estado_salida = asistencia.estado_salida
            
            # Calcular horas trabajadas (Entrada -> Salida)
            if historial.hora_entrada:
                historial.total_horas_trabajadas = now - historial.hora_entrada
            
        elif event_type == 'INICIO_BREAK':
            asistencia.hora_inicio_break = now
            
            # Si no había marcado entrada, marcar como tardanza o justificado
            if not asistencia.hora_entrada:
                asistencia.estado = 'tardanza'
                from .models import Incidencia
                if Incidencia.objects.filter(usuario=user, fecha_hora_reporte__date=today, estado_revision='Aprobado').exists():
                    asistencia.estado = 'justificado'
            
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
            
            # Calcular tiempo de break
            if historial.hora_inicio_break:
                historial.total_tiempo_break = now - historial.hora_inicio_break
        else:
            return Response({'error': 'Tipo de evento inválido'}, status=status.HTTP_400_BAD_REQUEST)

        # Actualizar estado si está fuera de zona (solo si no es ya Tardanza o similar que tenga prioridad?)
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

        # La notificación por WebSockets ahora se maneja automáticamente vía signals.py
        # (al guardar 'asistencia' y 'historial' se disparan los eventos correspondientes)

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

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        
        # Validar si el usuario ha marcado entrada y NO ha marcado salida
        if not asistencia or not asistencia.hora_entrada:
            return Response({
                'error': 'No puede enviar su reporte porque no ha iniciado su jornada (marcado entrada).'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if asistencia.hora_salida:
            return Response({
                'error': 'No puede enviar su reporte porque ya finalizó su jornada (marcado salida).'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Obtener la asistencia del día actual para vincular la incidencia
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
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        # Validar si puede ver la asistencia
        asistencia = Asistencia.objects.filter(id=asistencia_id).first()
        if not asistencia:
            return UbicacionPunto.objects.none()
            
        target_user = asistencia.usuario
        
        if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_asignadas = list(UsuarioSede.objects.filter(usuario=user, puede_visualizar=True).values_list('sede_id', flat=True))
            if user.sede_id:
                sedes_asignadas.append(user.sede_id)
            if target_user.creado_por == user or target_user.sede_id in sedes_asignadas:
                return queryset
            return UbicacionPunto.objects.none()
        elif 'operador' in rol_nombre or 'asesor' in rol_nombre:
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
    serializer_class = RolSerializer

    def get_queryset(self):
        # Aseguramos que devuelva todos los roles para llenar los combos del front
        return Rol.objects.all().order_by('id')

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
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(id__in=sedes_ids)
            
        if 'operador' in rol_nombre:
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
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'gerente', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(id__in=sedes_ids)
            
        if 'operador' in rol_nombre:
            if user.sede_id:
                return queryset.filter(id=user.sede_id)
            return Sede.objects.none()
            
        return Sede.objects.none()

class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        solo_operadores = self.request.query_params.get('solo_operadores') == 'true'
        
        queryset = Usuario.objects.all().order_by('-creado_at').select_related('sede', 'rol')
        
        # Si se solicita explícitamente solo personal operativo (ej. desde el historial)
        if solo_operadores:
            queryset = queryset.filter(rol__nombre__iregex=r'(operador|asesor)')
            
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            # Filtrar solo operadores/asesores estrictamente de sus sedes
            return queryset.filter(
                rol__nombre__iregex=r'(operador|asesor)',
                sede_id__in=sedes_ids
            ).exclude(id=user.id)
        elif 'operador' in rol_nombre or 'asesor' in rol_nombre:
            return queryset.filter(id=user.id)
            
        return queryset.filter(id=user.id)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UsuarioCreateUpdateSerializer
        return UsuarioSerializer

    def perform_create(self, serializer):
        try:
            user = self.request.user
            rol_nombre = user.rol.nombre.lower() if user.rol else ''
            
            if 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
                # Validar rol permitido
                target_rol_id = self.request.data.get('rol')
                target_rol = Rol.objects.filter(id=target_rol_id).first()
                if not target_rol or target_rol.nombre.lower() not in ['operador', 'asesor']:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'rol': 'Solo puede crear usuarios con rol Operador o Asesor.'})
                
                # Validar Sede: Solo puede asignar a su sede o sedes asignadas
                target_sede_id = self.request.data.get('sede')
                sedes_gestionables = get_authorized_sedes_ids(user)
                    
                try:
                        # Validar si la sede está en sus gestionables
                        if sedes_gestionables is not None and int(target_sede_id) not in sedes_gestionables:
                            from rest_framework.exceptions import ValidationError
                            raise ValidationError({'sede': 'No tiene permisos para asignar esta sede.'})
                except (ValueError, TypeError):
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'sede': 'Sede no válida.'})

            serializer.save(creado_por=user)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            raise e

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        usuario = self.get_object()
        new_password = self.request.data.get('password')
        if not new_password:
            return Response({'error': 'La contraseña es requerida.'}, status=status.HTTP_400_BAD_REQUEST)
        
        usuario.set_password(new_password)
        usuario.debe_cambiar_password = self.request.data.get('debe_cambiar_password', True)
        usuario.save()
        return Response({'status': 'Contraseña actualizada correctamente.'})

class IncidenciaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IncidenciaSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Incidencia.objects.all().order_by('-fecha_hora_reporte')
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(usuario__sede_id__in=sedes_ids)
            
        if 'operador' in rol_nombre or 'asesor' in rol_nombre:
            return queryset.filter(usuario=user)
            
        return queryset.filter(usuario=user)

class AsistenciaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AsistenciaSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = Asistencia.objects.all().order_by('-fecha')
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(usuario__sede_id__in=sedes_ids)
            
        if 'operador' in rol_nombre or 'asesor' in rol_nombre:
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
        
        # 4. Timestamp de la configuración de jornada de su sede
        from .models import JornadaConfiguracion
        dias_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
        day_name = dias_map[timezone.now().weekday()]
        j_config = JornadaConfiguracion.objects.filter(sede=user.sede, dia_semana=day_name).first()
        jornada_ts = j_config.actualizado_at if j_config else None
        
        # Encontramos el máximo de los timestamps válidos
        timestamps = [ts for ts in [user_ts, config_ts, asistencia_ts, jornada_ts] if ts is not None]
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
            
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo('America/Lima'))
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
        after_entrance_range = current_time > config.hora_fin_marcacion
        
        # 5. Validar si ya tiene asistencia o jornada creada
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        historial = HistorialJornada.objects.filter(usuario=user, fecha=today).first()
        
        puede_marcar_entrada = False
        puede_iniciar_descanso = False
        puede_finalizar_descanso = False
        puede_marcar_salida = False
        estado_jornada = 'no_iniciada'
        
        # Lógica de botones
        asistencia_estado = 'no_marco_entrada' # Default si no hay asistencia y terminó el rango
        
        if not asistencia or not asistencia.hora_entrada:
            if current_time >= config.hora_inicio_marcacion:
                puede_marcar_entrada = True
                estado_jornada = 'no_iniciada'
                
                if within_hours:
                    asistencia_estado = 'Sin Marcar'
                    mensaje = 'Puede marcar entrada puntual.'
                else:
                    asistencia_estado = 'no_marco_entrada'
                    mensaje = 'Rango de entrada finalizado. Puede marcar entrada (Tardanza).'
            else:
                # Antes del horario de inicio (ej. llega demasiado temprano)
                puede_marcar_entrada = False
                asistencia_estado = 'Sin Marcar'
                estado_jornada = 'no_iniciada'
                mensaje = f'Fuera de horario. El horario de marcación inicia a las {config.hora_inicio_marcacion}.'
        else:
            asistencia_estado = asistencia.estado
        
        # Si ya marcó entrada o ya está en flujo
        if asistencia:
            if asistencia.hora_salida or (historial and historial.cerrado):
                puede_marcar_entrada = False
                puede_iniciar_descanso = False
                puede_finalizar_descanso = False
                puede_marcar_salida = False
                estado_jornada = 'cerrada'
                mensaje = 'Ya completó su jornada de hoy.'
            else:
                # Jornada en curso
                estado_jornada = historial.estado_jornada if historial else 'en_proceso'
                # Lógica de descansos
                if not asistencia.hora_inicio_break:
                    puede_iniciar_descanso = True
                    mensaje = 'Jornada en curso. Puede iniciar descanso.'
                elif not asistencia.hora_fin_break:
                    puede_finalizar_descanso = True
                    mensaje = 'En descanso. Marque el fin del descanso para continuar.'

                # Lógica de salida (OBLIGATORIO haber completado el descanso si se inició)
                if not asistencia.hora_inicio_break or asistencia.hora_fin_break:
                    within_exit_range = True
                    if config.hora_inicio_salida:
                        within_exit_range = current_time >= config.hora_inicio_salida
                    
                    if within_exit_range:
                        puede_marcar_salida = True
                        # Si ya pasó la hora de fin, mostramos mensaje especial pero permitimos marcar
                        if config.hora_fin_salida and current_time > config.hora_fin_salida:
                            mensaje = 'Horario de salida finalizado. Marque su salida ahora.'
                        elif not puede_iniciar_descanso: # Si ya terminó el break o no hay break
                             mensaje = 'Puede marcar su salida.'
                    else:
                        # Si aún no es hora de salida y no estamos en break
                        if not puede_iniciar_descanso and not puede_finalizar_descanso:
                            puede_marcar_salida = False
                            mensaje = f'Aún no puede marcar salida. El horario de salida inicia a las {config.hora_inicio_salida}.'

        # Datos adicionales para Asesores
        puede_iniciar_actividad = False
        puede_finalizar_actividad = False
        actividad_en_proceso = None
        
        if user.rol and user.rol.nombre.lower() == 'asesor':
            if asistencia and asistencia.hora_entrada and not asistencia.hora_salida:
                actividad = JornadaActividad.objects.filter(usuario=user, estado_actividad='en_proceso').first()
                if actividad:
                    puede_finalizar_actividad = True
                    actividad_en_proceso = JornadaActividadSerializer(actividad).data
                else:
                    puede_iniciar_actividad = True

        response_data.update({
            'puede_marcar_entrada': puede_marcar_entrada,
            'puede_iniciar_descanso': puede_iniciar_descanso,
            'puede_finalizar_descanso': puede_finalizar_descanso,
            'puede_marcar_salida': puede_marcar_salida,
            'puede_iniciar_actividad': puede_iniciar_actividad,
            'puede_finalizar_actividad': puede_finalizar_actividad,
            'actividad_en_proceso': actividad_en_proceso,
            'estado_jornada': estado_jornada,
            'mensaje': mensaje,
            'asistencia_estado': asistencia_estado,
            'estado_puntualidad': asistencia.estado_puntualidad if asistencia else 'pendiente'
        })
            
        return Response(response_data, status=status.HTTP_200_OK)

from django.shortcuts import render, get_object_or_404
import json

class JourneyTrackingMapView(APIView):
    """
    Vista externa que renderiza un mapa con el tracking completo de una asistencia.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, asistencia_id):
        asistencia = get_object_or_404(Asistencia, id=asistencia_id)
        user = request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        # Validar permisos
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            if asistencia.usuario.sede_id not in sedes_ids:
                return Response({'error': 'No autorizado para ver este recorrido'}, status=status.HTTP_403_FORBIDDEN)
        elif asistencia.usuario != user:
             return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)

        puntos = UbicacionPunto.objects.filter(asistencia=asistencia).order_by('fecha_hora')
        
        puntos_json = []
        for p in puntos:
            puntos_json.append({
                'lat': float(p.latitud),
                'lng': float(p.longitud),
                'hora': p.fecha_hora.astimezone(ZoneInfo('America/Lima')).strftime('%H:%M:%S')
            })

        context = {
            'asistencia': asistencia,
            'usuario': asistencia.usuario,
            'fecha': asistencia.fecha,
            'puntos': puntos,
            'puntos_json': json.dumps(puntos_json)
        }
        
        return render(request, 'api/map_tracking.html', context)


class ActividadHoyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        current_user = request.user
        rol_nombre = current_user.rol.nombre.lower() if current_user.rol else ''
        
        # Sincronizar estados de jornada antes de consultar
        from .utils import sync_daily_attendance, close_expired_journeys
        sync_daily_attendance()
        close_expired_journeys()
        
        # Base query: todos los usuarios activos hoy EXCLUYENDO al propio gerente
        usuarios = Usuario.objects.filter(activo=True).exclude(id=current_user.id).select_related('sede', 'rol')
        
        # Aplicar restricciones por rol
        sedes_ids = get_authorized_sedes_ids(current_user)
        if sedes_ids is not None:
            # FILTRO ESTRICTO: Solo personal OPERATIVO (Operador/Asesor) estrictamente de sus sedes
            usuarios = usuarios.filter(
                rol__nombre__iregex=r'(operador|asesor)',
                sede_id__in=sedes_ids
            )
        elif 'operador' in rol_nombre or 'asesor' in rol_nombre:
            usuarios = usuarios.filter(id=current_user.id)
        else:
            # Para otros roles (admin), igual filtramos por personal operativo para este módulo
            usuarios = usuarios.filter(rol__nombre__iregex=r'(operador|asesor)')
        
        data = []
        # Optimizamos consultas: una sola pasada por los usuarios
        for user in usuarios:
            asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
            incidencias_count = Incidencia.objects.filter(usuario=user, fecha_hora_reporte__date=today).count()
            
            # Puntos GPS del día
            puntos_gps = UbicacionPunto.objects.filter(usuario=user, fecha=today)
            puntos_count = puntos_gps.count()
            ultimo_punto = puntos_gps.order_by('-fecha_hora').first()
            
            # Actividades de campo (si es asesor)
            actividades_hoy = JornadaActividad.objects.filter(usuario=user, hora_inicio_actividad__date=today)
            total_actividades = actividades_hoy.count()
            act_proceso = actividades_hoy.filter(estado_actividad='en_proceso').first()
            actividad_actual = JornadaActividadSerializer(act_proceso).data if act_proceso else None
            
            # Determinar estado de asistencia para el Dashboard
            estado_dashboard = 'Sin Marcar'
            if asistencia:
                if asistencia.hora_salida:
                    estado_dashboard = 'Salida'
                elif asistencia.hora_inicio_break and not asistencia.hora_fin_break:
                    estado_dashboard = 'En Break'
                else:
                    estado_dashboard = asistencia.estado.capitalize() if asistencia.estado else 'Presente'

            # Estructura de datos 100% compatible con el Dashboard React anterior
            item_data = {
                'id': user.id,
                'nombre_completo': user.nombre_completo,
                'dni': user.dni,
                'cargo': user.cargo,
                'sede': user.sede.nombre if user.sede else '-',
                'rol': user.rol.nombre if user.rol else '-',
                'email': user.email,
                'telefono': user.telefono,
                'rol_info': RolSerializer(user.rol).data if user.rol else None,
                'sede_info': SedeSerializer(user.sede).data if user.sede else None,
                'asistencia': {
                    'id': asistencia.id if asistencia else None,
                    'hora_entrada': asistencia.hora_entrada if asistencia else None,
                    'hora_inicio_break': asistencia.hora_inicio_break if asistencia else None,
                    'hora_fin_break': asistencia.hora_fin_break if asistencia else None,
                    'hora_salida': asistencia.hora_salida if asistencia else None,
                    'estado_asistencia': asistencia.estado_asistencia if asistencia else 'programada',
                    'estado_puntualidad': asistencia.estado_puntualidad if asistencia else 'pendiente',
                    'estado_salida': asistencia.estado_salida if asistencia else 'pendiente',
                    'estado': estado_dashboard,
                } if asistencia else None,
                'incidencias': incidencias_count,
                'puntos_gps': puntos_count,
                'ultima_ubicacion': {
                    'latitud': ultimo_punto.latitud if ultimo_punto else None,
                    'longitud': ultimo_punto.longitud if ultimo_punto else None,
                    'fecha_hora': ultimo_punto.fecha_hora if ultimo_punto else None,
                    'bateria': ultimo_punto.bateria_porcentaje if ultimo_punto else None,
                    'distancia': ultimo_punto.distancia_sede_metros if ultimo_punto else None
                } if ultimo_punto else None,
                'total_actividades': total_actividades,
                'actividad_actual': actividad_actual
            }
            data.append(item_data)
            
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
        
        sedes_ids = get_authorized_sedes_ids(current_user)
        if sedes_ids is not None:
            # Validar si puede ver este usuario (sedes asignadas o su propia sede)
            if user.sede_id not in sedes_ids:
                return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)
        elif ('operador' in rol_nombre or 'asesor' in rol_nombre) and current_user.id != user.id:
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
                'estado': inc.estado_revision,
                'foto': inc.foto_evidencia_url.url if inc.foto_evidencia_url else (inc.evidencia_url if inc.evidencia_url else None)
            })
            
        ultimo_punto = puntos_gps.last()
        
        # Determinar estado detallado para visualización
        estado_asistencia = 'Sin Marcar'
        if asistencia:
            estado_asistencia = asistencia.estado.capitalize() if asistencia.estado else 'Presente'
        else:
            # Verificar si ya pasó el rango de entrada sin marcar
            from .models import JornadaConfiguracion
            from zoneinfo import ZoneInfo
            dias_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
            day_name = dias_map[timezone.now().weekday()]
            config = JornadaConfiguracion.objects.filter(sede=user.sede, dia_semana=day_name, activo=True).first()
            current_time = timezone.now().astimezone(ZoneInfo('America/Lima')).time()
            if config and current_time > config.hora_fin_marcacion:
                estado_asistencia = 'No marcó entrada'

        data = {
            'usuario': {
                'id': user.id,
                'dni': user.dni,
                'nombre_completo': user.nombre_completo,
                'sede': user.sede.nombre if user.sede else '-',
                'cargo': user.cargo,
                'rol_codigo': user.rol.codigo if user.rol else None,
                'rol_nombre': user.rol.nombre if user.rol else None
            },
            'asistencia': {
                'hora_entrada': asistencia.hora_entrada if asistencia else None,
                'hora_inicio_break': asistencia.hora_inicio_break if asistencia else None,
                'hora_fin_break': asistencia.hora_fin_break if asistencia else None,
                'hora_salida': asistencia.hora_salida if asistencia else None,
                'estado': estado_asistencia
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
            'incidencias': incidencias_data,
            'actividades_campo': JornadaActividadSerializer(JornadaActividad.objects.filter(usuario=user, hora_inicio_actividad__date=today).order_by('hora_inicio_actividad'), many=True).data
        }
        
        return Response(data)

class JornadaConfiguracionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JornadaConfiguracionSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        from .models import JornadaConfiguracion, UsuarioSede
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return JornadaConfiguracion.objects.all()
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return JornadaConfiguracion.objects.filter(sede_id__in=sedes_ids)
        return JornadaConfiguracion.objects.all()
            
        return JornadaConfiguracion.objects.none()

class HistorialJornadaListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HistorialJornadaListSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        # Sincronizar estados antes de listar
        from .utils import sync_daily_attendance, close_expired_journeys
        sync_daily_attendance()
        close_expired_journeys()
        
        # Anotar conteos de incidencias y puntos GPS vinculados a la asistencia
        queryset = HistorialJornada.objects.select_related('usuario', 'asistencia').annotate(
            total_incidencias=models.Count('asistencia__incidencias_detalle', distinct=True),
            total_puntos_gps=models.Count('asistencia__puntos_gps', distinct=True)
        ).order_by('-fecha', '-hora_entrada')
        
        # Filtros por parámetros
        usuario_id = self.request.query_params.get('usuario_id') or self.request.query_params.get('usuario')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        sede_id = self.request.query_params.get('sede_id')
        estado_asistencia = self.request.query_params.get('estado_asistencia')

        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if sede_id:
            queryset = queryset.filter(usuario__sede_id=sede_id)
        if estado_asistencia:
            queryset = queryset.filter(estado_asistencia=estado_asistencia)

        # Reglas de Visibilidad
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            # FILTRO ESTRICTO: Solo historial de personal OPERATIVO estrictamente de sus sedes
            return queryset.filter(
                usuario__rol__nombre__iregex=r'(operador|asesor)',
                usuario__sede_id__in=sedes_ids
            ).exclude(usuario=user)
            
        elif 'operador' in rol_nombre or 'asesor' in rol_nombre:
            # Solo su propio historial
            return queryset.filter(usuario=user)
            
        # Admin ve todo, pero el usuario pidió que en estos módulos solo salgan operadores y asesores
        return queryset.filter(usuario__rol__nombre__iregex=r'(operador|asesor)')

class HistorialJornadaDetalleView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HistorialJornadaDetailSerializer
    queryset = HistorialJornada.objects.all()

    def get_object(self):
        # Sincronizar estados antes de obtener el objeto
        from .utils import sync_daily_attendance, close_expired_journeys
        sync_daily_attendance()
        close_expired_journeys()
        
        obj = super().get_object()
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        # Validar permisos
        can_view = False
        sedes_ids = get_authorized_sedes_ids(user)
        
        if sedes_ids is None: # Admin
            can_view = True
        elif obj.usuario.sede_id in sedes_ids:
            can_view = True
        elif obj.usuario == user:
            can_view = True
            
        if not can_view:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tiene permisos para ver este detalle.")
            
        return obj
            
class JornadaActividadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JornadaActividadSerializer

    def get_queryset(self):
        user = self.request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        queryset = JornadaActividad.objects.all().order_by('-hora_inicio_actividad')
        
        # Filtros
        historial_jornada_id = self.request.query_params.get('historial_jornada_id')
        usuario_id = self.request.query_params.get('usuario_id')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        estado_actividad = self.request.query_params.get('estado_actividad')
        
        if historial_jornada_id:
            queryset = queryset.filter(historial_jornada_id=historial_jornada_id)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        if fecha_inicio:
            queryset = queryset.filter(hora_inicio_actividad__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(hora_inicio_actividad__date__lte=fecha_fin)
        if estado_actividad:
            queryset = queryset.filter(estado_actividad=estado_actividad)
            
        # Visibilidad
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(sede_id__in=sedes_ids)
            
        if 'asesor' in rol_nombre:
            return queryset.filter(usuario=user)
            
        return queryset.none()

    @action(detail=False, methods=['post'])
    def iniciar(self, request):
        user = request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        
        if rol_nombre != 'asesor':
            return Response({'error': 'Solo los asesores pueden registrar actividades de campo.'}, status=status.HTTP_403_FORBIDDEN)
            
        today = timezone.now().date()
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        
        if not asistencia or not asistencia.hora_entrada:
            return Response({'error': 'Debe marcar entrada antes de iniciar una actividad.'}, status=status.HTTP_400_BAD_REQUEST)
        if asistencia.hora_salida:
            return Response({'error': 'No puede iniciar una actividad si ya marcó salida.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Validar si ya tiene una en proceso
        actividad_pendiente = JornadaActividad.objects.filter(usuario=user, estado_actividad='en_proceso').exists()
        if actividad_pendiente:
            return Response({'error': 'Ya tiene una actividad en proceso. Finalícela antes de iniciar otra.'}, status=status.HTTP_400_BAD_REQUEST)
            
        historial = HistorialJornada.objects.filter(usuario=user, fecha=today).first()
        if not historial:
             return Response({'error': 'No se encontró el historial de jornada para hoy.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save(
            usuario=user,
            asistencia=asistencia,
            historial_jornada=historial,
            sede=user.sede,
            estado_actividad='en_proceso',
            hora_inicio_actividad=timezone.now()
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def finalizar(self, request):
        user = request.user
        actividad_id = request.data.get('actividad_id')
        
        if not actividad_id:
             return Response({'error': 'ID de actividad requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        actividad = JornadaActividad.objects.filter(id=actividad_id, usuario=user, estado_actividad='en_proceso').first()
        if not actividad:
            return Response({'error': 'Actividad no encontrada o ya finalizada.'}, status=status.HTTP_404_NOT_FOUND)
            
        actividad.resultado_actividad = request.data.get('resultado_actividad')
        actividad.observacion = request.data.get('observacion')
        actividad.latitud_fin = request.data.get('latitud_fin')
        actividad.longitud_fin = request.data.get('longitud_fin')
        actividad.evidencia_fin_url = request.data.get('evidencia_fin_url')
        actividad.dispositivo_fin = request.data.get('dispositivo_fin')
        actividad.hora_fin_actividad = timezone.now()
        actividad.estado_actividad = 'finalizada'
        actividad.save()
        
        return Response(self.get_serializer(actividad).data, status=status.HTTP_200_OK)

