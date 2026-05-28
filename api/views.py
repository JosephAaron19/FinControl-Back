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
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia, UsuarioSede, HistorialJornada, JornadaActividad, Horario, HorarioDetalle, UsuarioHorario, IntercambioHorario, JornadaConfiguracion
from .serializers import (
    SedeSerializer, UsuarioSerializer, UsuarioCreateUpdateSerializer, AsistenciaSerializer, 
    IncidenciaSerializer, CustomTokenObtainPairSerializer,
    ConfiguracionTrackingSerializer, UbicacionPuntoSerializer,
    RolSerializer, TipoIncidenciaSerializer, JornadaConfiguracionSerializer,
    HistorialJornadaSerializer, HistorialJornadaListSerializer, HistorialJornadaDetailSerializer,
    JornadaActividadSerializer, HorarioSerializer, HorarioDetalleSerializer,
    UsuarioHorarioSerializer, IntercambioHorarioSerializer
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


def resolve_usuario_horario_para_fecha(usuario, fecha):
    # 1. Buscar intercambios aprobados
    intercambio = IntercambioHorario.objects.filter(
        fecha_intercambio=fecha,
        estado__iexact='aprobado',
        activo=True
    ).filter(Q(usuario_solicitante=usuario) | Q(usuario_reemplazo=usuario)).first()
    
    if intercambio:
        if intercambio.usuario_solicitante == usuario:
            horario = intercambio.horario_reemplazo_original
        else:
            horario = intercambio.horario_solicitante_original
        if horario:
            return horario, 'intercambio'
            
    # 2. Buscar horario asignado directamente
    uh = UsuarioHorario.objects.filter(
        usuario=usuario,
        activo=True,
        vigente_desde__lte=fecha
    ).filter(Q(vigente_hasta__gte=fecha) | Q(vigente_hasta__isnull=True)).first()
    
    if uh and uh.horario:
        return uh.horario, 'usuario'
        
    return None, 'sin_horario'


def check_usuario_horario_overlap(usuario_id, horario_id, vigente_desde, vigente_hasta, exclude_uh_id=None):
    from datetime import date
    if isinstance(vigente_desde, str):
        vigente_desde = date.fromisoformat(vigente_desde) if vigente_desde else date.today()
    elif vigente_desde is None:
        vigente_desde = date.today()
        
    if isinstance(vigente_hasta, str):
        vigente_hasta = date.fromisoformat(vigente_hasta) if vigente_hasta else None

    # Get the new Horario details
    new_details = {
        d.dia_semana.lower(): (d.hora_inicio_entrada, d.hora_fin_salida)
        for d in HorarioDetalle.objects.filter(horario_id=horario_id, activo=True)
    }
    if not new_details:
        return False

    # Query all active assignments for this user
    active_assignments = UsuarioHorario.objects.filter(usuario_id=usuario_id, activo=True)
    if exclude_uh_id:
        active_assignments = active_assignments.exclude(id=exclude_uh_id)

    for uh in active_assignments:
        # Check date range overlap
        a_start = uh.vigente_desde
        a_end = uh.vigente_hasta
        
        # Check if date ranges overlap:
        overlap_dates = (vigente_desde <= a_end if a_end else True) and (a_start <= vigente_hasta if vigente_hasta else True)
        if not overlap_dates:
            continue
            
        # Get details of the existing horario
        existing_details = {
            d.dia_semana.lower(): (d.hora_inicio_entrada, d.hora_fin_salida)
            for d in HorarioDetalle.objects.filter(horario=uh.horario, activo=True)
        }
        
        # Check day and time overlap
        for day, new_times in new_details.items():
            if day in existing_details:
                existing_times = existing_details[day]
                t1_start, t1_end = new_times
                t2_start, t2_end = existing_times
                
                # Check if times overlap using strict inequality for the touch point
                if t1_start < t2_end and t2_start < t1_end:
                    return True
                    
    return False


def deactivate_dependent_relations(horario):
    # 1. Deactivate details
    HorarioDetalle.objects.filter(horario=horario).update(activo=False)
    # 2. Deactivate user assignments
    UsuarioHorario.objects.filter(horario=horario).update(activo=False, es_principal=False)
    # 3. Deactivate interchanges that use this schedule
    IntercambioHorario.objects.filter(
        Q(horario_solicitante_original=horario) | Q(horario_reemplazo_original=horario)
    ).update(activo=False)


def get_active_horario_detalle(usuario, fecha):
    dias_map = {
        0: 'lunes',
        1: 'martes',
        2: 'miercoles',
        3: 'jueves',
        4: 'viernes',
        5: 'sabado',
        6: 'domingo'
    }
    day_str = dias_map[fecha.weekday()]
    
    horario, origen = resolve_usuario_horario_para_fecha(usuario, fecha)
    if horario:
        detalle = HorarioDetalle.objects.filter(horario=horario, dia_semana=day_str, activo=True).first()
        if detalle:
            return {
                'tipo': 'detalle',
                'origen': origen,
                'hora_inicio_entrada': detalle.hora_inicio_entrada,
                'hora_fin_entrada': detalle.hora_fin_entrada,
                'hora_inicio_salida': detalle.hora_inicio_salida,
                'hora_fin_salida': detalle.hora_fin_salida,
                'horario_id': horario.id,
                'nombre': horario.nombre
            }
        else:
            return {
                'tipo': 'sin_horario',
                'origen': 'sin_horario',
                'hora_inicio_entrada': None,
                'hora_fin_entrada': None,
                'hora_inicio_salida': None,
                'hora_fin_salida': None,
                'horario_id': None,
                'nombre': None
            }
            
    # If no direct schedule or exchange schedule covers today, return sin_horario
    return {
        'tipo': 'sin_horario',
        'origen': 'sin_horario',
        'hora_inicio_entrada': None,
        'hora_fin_entrada': None,
        'hora_inicio_salida': None,
        'hora_fin_salida': None,
        'horario_id': None,
        'nombre': None
    }


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

        # Validaciones de Estado (Horario flexible con prioridades)
        horario_info = get_active_horario_detalle(user, today)
        if horario_info['origen'] == 'sin_horario':
            return Response({'error': 'No tienes horario asignado para hoy.'}, status=status.HTTP_400_BAD_REQUEST)

        hora_inicio_entrada = horario_info['hora_inicio_entrada']
        hora_fin_entrada = horario_info['hora_fin_entrada']
        hora_inicio_salida = horario_info['hora_inicio_salida']
        hora_fin_salida = horario_info['hora_fin_salida']

        current_time = now_local.time()

        if event_type == 'ENTRADA':
            if asistencia_hoy and asistencia_hoy.hora_entrada:
                return Response({'error': 'Ya tiene una entrada registrada para hoy.'}, status=status.HTTP_400_BAD_REQUEST)
                
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
            if not hora_fin_entrada or current_time <= hora_fin_entrada:
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

            is_outside_exit = False
            if hora_inicio_salida and time_exit < hora_inicio_salida:
                is_outside_exit = True
            if hora_fin_salida and time_exit > hora_fin_salida:
                is_outside_exit = True

            if is_outside_exit:
                 asistencia.estado_salida = 'fuera_rango'
            else:
                 asistencia.estado_salida = 'dentro_rango'
            
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

        # Resolver historial_jornada_id si no viene o es nulo
        if not historial_jornada_id:
            historial = HistorialJornada.objects.filter(asistencia=asistencia).first()
            if not historial:
                historial = HistorialJornada.objects.filter(usuario=user, fecha=today).first()
            if historial:
                historial_jornada_id = historial.id

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
        
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            return queryset
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            return queryset.filter(id__in=sedes_ids)
            
        if 'operador' in rol_nombre or 'asesor' in rol_nombre:
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
            
        sede_id = self.request.query_params.get('sede')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
            
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
            rol_nombre = (user.rol.nombre or '').lower() if user.rol else ''
            rol_codigo = (user.rol.codigo or '').lower() if user.rol else ''
            
            is_manager = 'gerente' in rol_nombre or 'gerente' in rol_codigo or \
                         'supervisor' in rol_nombre or 'supervisor' in rol_codigo
            
            if is_manager:
                # Validar rol permitido
                target_rol_id = self.request.data.get('rol')
                target_rol = Rol.objects.filter(id=target_rol_id).first()
                target_rol_nombre = (target_rol.nombre or '').lower() if target_rol else ''
                target_rol_codigo = (target_rol.codigo or '').lower() if target_rol else ''
                
                if not target_rol or (target_rol_nombre not in ['operador', 'asesor'] and target_rol_codigo not in ['operador', 'asesor']):
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'rol': 'Solo puede crear usuarios con rol Operador o Asesor.'})
                
                # Validar Sede: Solo puede asignar a su sede o sedes asignadas
                target_sede_id = self.request.data.get('sede')
                sedes_gestionables = get_authorized_sedes_ids(user)
                    
                try:
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

    def perform_update(self, serializer):
        try:
            user = self.request.user
            rol_nombre = (user.rol.nombre or '').lower() if user.rol else ''
            rol_codigo = (user.rol.codigo or '').lower() if user.rol else ''
            
            is_manager = 'gerente' in rol_nombre or 'gerente' in rol_codigo or \
                         'supervisor' in rol_nombre or 'supervisor' in rol_codigo
            
            if is_manager:
                # Validar rol permitido si se está editando
                target_rol_id = self.request.data.get('rol')
                if target_rol_id:
                    target_rol = Rol.objects.filter(id=target_rol_id).first()
                    target_rol_nombre = (target_rol.nombre or '').lower() if target_rol else ''
                    target_rol_codigo = (target_rol.codigo or '').lower() if target_rol else ''
                    
                    if not target_rol or (target_rol_nombre not in ['operador', 'asesor'] and target_rol_codigo not in ['operador', 'asesor']):
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'rol': 'Solo puede asignar rol Operador o Asesor.'})
                
                # Validar Sede si se está editando
                target_sede_id = self.request.data.get('sede')
                if target_sede_id:
                    sedes_gestionables = get_authorized_sedes_ids(user)
                    try:
                        if sedes_gestionables is not None and int(target_sede_id) not in sedes_gestionables:
                            from rest_framework.exceptions import ValidationError
                            raise ValidationError({'sede': 'No tiene permisos para asignar esta sede.'})
                    except (ValueError, TypeError):
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'sede': 'Sede no válida.'})

            serializer.save()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            raise e

    @action(detail=True, methods=['post'], url_path='change-password')
    def change_password(self, request, pk=None):
        from django.shortcuts import get_object_or_404
        requesting_user = request.user
        rol_nombre = requesting_user.rol.nombre.lower() if requesting_user.rol else ''
        rol_codigo = (requesting_user.rol.codigo or '').lower() if requesting_user.rol else ''

        # Superadmin/Admin puede cambiar cualquier contraseña
        if any(r in rol_nombre for r in ['admin', 'superadmin', 'super administrador']) or \
           any(r in rol_codigo for r in ['admin', 'superadmin']):
            usuario = get_object_or_404(Usuario, pk=pk)
        elif 'gerente' in rol_nombre or 'gerente' in rol_codigo or \
             'supervisor' in rol_nombre or 'supervisor' in rol_codigo:
            # Gerente/Supervisor: puede cambiar contraseña de cualquier usuario de sus sedes
            sedes_ids = get_authorized_sedes_ids(requesting_user)
            if sedes_ids is None:
                # Gerente sin sedes asignadas aún — permitir sobre usuarios que él creó
                usuario = get_object_or_404(Usuario, pk=pk, creado_por=requesting_user)
            else:
                # Buscar en sedes autorizadas (sin restricción de rol del target)
                usuario = get_object_or_404(Usuario, pk=pk, sede_id__in=sedes_ids)
        else:
            # Operador/Asesor: solo puede cambiar su propia contraseña
            if str(pk) != str(requesting_user.pk):
                return Response(
                    {'error': 'No tiene permisos para cambiar la contraseña de este usuario.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            usuario = requesting_user

        new_password = request.data.get('password')
        if not new_password:
            return Response({'error': 'La contraseña es requerida.'}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(new_password)
        # Por defecto False: si alguien cambia intencionalmente la contraseña, no forzar otro cambio
        usuario.debe_cambiar_password = request.data.get('debe_cambiar_password', False)
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
        today = timezone.now().date()
        
        # Recopilar marcas temporales de modelos que afectan a este usuario
        timestamps = [user.actualizado_at]
        
        if user.sede:
            timestamps.append(user.sede.actualizado_at)
            
        config = ConfiguracionTracking.objects.first()
        if config and config.actualizado_at:
            timestamps.append(config.actualizado_at)
            
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        if asistencia and asistencia.actualizado_at:
            timestamps.append(asistencia.actualizado_at)
            
        # Configuración de jornada de su sede (para cualquier día de la semana)
        if user.sede:
            jc = JornadaConfiguracion.objects.filter(sede=user.sede, activo=True).order_by('-actualizado_at').first()
            if jc and jc.actualizado_at:
                timestamps.append(jc.actualizado_at)
                
        # Asignación de horario directo (UsuarioHorario)
        uh = UsuarioHorario.objects.filter(usuario=user, activo=True).order_by('-actualizado_at').first()
        if uh and uh.actualizado_at:
            timestamps.append(uh.actualizado_at)
            
        # Detalles del horario asignado (Horario y HorarioDetalle)
        if uh and uh.horario:
            if uh.horario.actualizado_at:
                timestamps.append(uh.horario.actualizado_at)
            hd = HorarioDetalle.objects.filter(horario=uh.horario, activo=True).order_by('-actualizado_at').first()
            if hd and hd.actualizado_at:
                timestamps.append(hd.actualizado_at)
                
        # Intercambios/extensiones de horario (IntercambioHorario)
        intc = IntercambioHorario.objects.filter(
            Q(usuario_solicitante=user) | Q(usuario_reemplazo=user),
            activo=True
        ).order_by('-actualizado_at').first()
        if intc and intc.actualizado_at:
            timestamps.append(intc.actualizado_at)
            
        # Encontramos el máximo de los timestamps válidos
        valid_timestamps = [ts for ts in timestamps if ts is not None]
        max_ts = max(valid_timestamps) if valid_timestamps else timezone.now()
        
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
        
        # Importar modelos localmente
        from .models import HistorialJornada, Asistencia, JornadaActividad
        
        horario_info = get_active_horario_detalle(user, today)
        
        response_data = {
            'hora_servidor': now.strftime('%H:%M:%S'),
            'dia_servidor': day_str,
            'origen_horario': horario_info['origen'],
        }
        
        if horario_info['origen'] == 'sin_horario':
            response_data.update({
                'puede_marcar_entrada': False,
                'puede_iniciar_descanso': False,
                'puede_finalizar_descanso': False,
                'puede_marcar_salida': False,
                'puede_iniciar_break': False,
                'puede_finalizar_break': False,
                'puede_iniciar_actividad': False,
                'puede_finalizar_actividad': False,
                'puede_culminar_actividad': False,
                'actividad_en_proceso': None,
                'estado_jornada': 'no_iniciada',
                'mensaje': 'No tienes horario asignado para hoy',
                'asistencia_estado': 'Sin Marcar',
                'estado_puntualidad': 'pendiente',
                'horario_actual': None
            })
            return Response(response_data, status=status.HTTP_200_OK)
            
        hora_inicio_entrada = horario_info['hora_inicio_entrada']
        hora_fin_entrada = horario_info['hora_fin_entrada']
        hora_inicio_salida = horario_info['hora_inicio_salida']
        hora_fin_salida = horario_info['hora_fin_salida']
        
        horario_actual = {
            'nombre': horario_info['nombre'],
            'hora_inicio_entrada': hora_inicio_entrada.strftime('%H:%M:%S') if hora_inicio_entrada else None,
            'hora_fin_entrada': hora_fin_entrada.strftime('%H:%M:%S') if hora_fin_entrada else None,
            'hora_inicio_salida': hora_inicio_salida.strftime('%H:%M:%S') if hora_inicio_salida else None,
            'hora_fin_salida': hora_fin_salida.strftime('%H:%M:%S') if hora_fin_salida else None,
        }
        response_data['horario_actual'] = horario_actual
        
        current_time = now.time()
        
        # Validar si ya tiene asistencia o jornada creada
        asistencia = Asistencia.objects.filter(usuario=user, fecha=today).first()
        historial = HistorialJornada.objects.filter(usuario=user, fecha=today).first()
        
        puede_marcar_entrada = False
        puede_iniciar_descanso = False
        puede_finalizar_descanso = False
        puede_marcar_salida = False
        estado_jornada = 'no_iniciada'
        
        asistencia_estado = 'no_marco_entrada' # Default
        mensaje = ""
        
        if not asistencia or not asistencia.hora_entrada:
            puede_marcar_entrada = True
            estado_jornada = 'no_iniciada'
            
            if hora_inicio_entrada and current_time < hora_inicio_entrada:
                asistencia_estado = 'Sin Marcar'
                mensaje = 'Puede marcar entrada (Anticipado).'
            elif hora_fin_entrada and current_time <= hora_fin_entrada:
                asistencia_estado = 'Sin Marcar'
                mensaje = 'Puede marcar entrada puntual.'
            else:
                asistencia_estado = 'no_marco_entrada'
                mensaje = 'Rango de entrada finalizado. Puede marcar entrada (Tardanza).'
        else:
            asistencia_estado = asistencia.estado
        
        # Si ya marcó entrada
        if asistencia:
            if asistencia.hora_salida or (historial and historial.cerrado):
                puede_marcar_entrada = False
                puede_iniciar_descanso = False
                puede_finalizar_descanso = False
                puede_marcar_salida = False
                estado_jornada = 'cerrada'
                mensaje = 'Ya completó su jornada de hoy.'
            else:
                estado_jornada = historial.estado_jornada if historial else 'en_proceso'
                
                # BREAK LIBRE: Se permite iniciar y finalizar en cualquier momento
                if not asistencia.hora_inicio_break:
                    puede_iniciar_descanso = True
                    mensaje = 'Jornada en curso. Puede iniciar descanso.'
                elif not asistencia.hora_fin_break:
                    puede_finalizar_descanso = True
                    mensaje = 'En descanso. Marque el fin del descanso para continuar.'
                else:
                    mensaje = 'Descanso finalizado. Espere para marcar salida.'

                # Salida (se requiere completar break si se inició)
                if not asistencia.hora_inicio_break or asistencia.hora_fin_break:
                    puede_marcar_salida = True
                    
                    is_outside_exit = False
                    if hora_inicio_salida and current_time < hora_inicio_salida:
                        is_outside_exit = True
                    if hora_fin_salida and current_time > hora_fin_salida:
                        is_outside_exit = True
                        
                    if is_outside_exit:
                        if hora_inicio_salida and current_time < hora_inicio_salida:
                            mensaje = 'Fuera de rango de salida. Puede marcar salida anticipada.'
                        else:
                            mensaje = 'Fuera de rango de salida. Puede marcar salida.'
                    else:
                        mensaje = 'Puede marcar su salida.'

        # Datos adicionales para Asesores
        puede_iniciar_actividad = False
        puede_finalizar_actividad = False
        actividad_en_proceso = None
        
        if user.rol and (
            user.rol.nombre.lower() == 'asesor' or
            (user.rol.codigo or '').lower() == 'asesor'
        ):
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
            # Mantener compatibilidad con ambas nomenclaturas
            'puede_iniciar_break': puede_iniciar_descanso,
            'puede_finalizar_break': puede_finalizar_descanso,
            'puede_iniciar_actividad': puede_iniciar_actividad,
            'puede_finalizar_actividad': puede_finalizar_actividad,
            'puede_culminar_actividad': puede_finalizar_actividad,
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
        is_admin = any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador'])
        
        # Validar permisos
        if not is_admin:
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


class JourneyTrackingRecorridoJornadaView(APIView):
    """
    Endpoint para obtener el recorrido GPS detallado de una jornada por su ID de historial.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, historial_jornada_id):
        # 1. Obtener el historial de jornada
        historial = get_object_or_404(HistorialJornada, id=historial_jornada_id)
        user = request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''

        # 2. Control de seguridad según roles
        can_view = False
        if any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador']):
            can_view = True
        elif 'gerente' in rol_nombre or 'supervisor' in rol_nombre:
            sedes_ids = get_authorized_sedes_ids(user)
            if sedes_ids is None:
                can_view = True
            else:
                if user.sede_id:
                    sedes_ids.append(user.sede_id)
                sedes_ids = list(set(sedes_ids))
                # Creado por él o asignado a sus sedes
                if (historial.usuario.creado_por == user or 
                    (historial.usuario.sede_id and historial.usuario.sede_id in sedes_ids) or
                    (historial.sede_id and historial.sede_id in sedes_ids)):
                    can_view = True
        elif 'operador' in rol_nombre or 'asesor' in rol_nombre:
            if historial.usuario == user:
                can_view = True

        if not can_view:
            return Response({'error': 'No tiene permisos para ver este recorrido.'}, status=status.HTTP_403_FORBIDDEN)

        # 3. Obtener la sede (priorizar la de la jornada, luego la del usuario)
        sede = None
        if historial.sede_id:
            sede = Sede.objects.filter(id=historial.sede_id).first()
        if not sede and historial.usuario.sede:
            sede = historial.usuario.sede

        sede_data = {
            'sede_id': sede.id if sede else None,
            'nombre': sede.nombre if sede else None,
            'latitud': float(sede.latitud) if sede and sede.latitud is not None else None,
            'longitud': float(sede.longitud) if sede and sede.longitud is not None else None,
            'radio_metros': sede.radio_metros if sede else None,
        }

        # 4. Obtener puntos GPS ordenados por fecha_hora
        puntos = UbicacionPunto.objects.filter(
            historial_jornada_id=historial.id,
            latitud__isnull=False,
            longitud__isnull=False
        ).order_by('fecha_hora')

        # Si no hay puntos por historial_jornada_id, intentar buscar por su asistencia asociada
        if not puntos.exists() and historial.asistencia:
            puntos = UbicacionPunto.objects.filter(
                asistencia=historial.asistencia,
                latitud__isnull=False,
                longitud__isnull=False
            ).order_by('fecha_hora')

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

        # 5. Estructurar respuesta
        response_data = {
            'jornada': {
                'historial_jornada_id': historial.id,
                'fecha': historial.fecha.isoformat() if historial.fecha else None,
                'hora_entrada': historial.hora_entrada.isoformat() if historial.hora_entrada else None,
                'hora_salida': historial.hora_salida.isoformat() if historial.hora_salida else None,
                'estado_jornada': historial.estado_jornada,
                'estado_asistencia': historial.estado_asistencia
            },
            'usuario': {
                'usuario_id': historial.usuario.id,
                'nombre_completo': historial.usuario.nombre_completo,
                'rol': historial.usuario.rol.nombre if historial.usuario.rol else None
            },
            'sede': sede_data,
            'puntos': puntos_data,
            'resumen': {
                'total_puntos': len(puntos_data),
                'primera_ubicacion': puntos_data[0] if puntos_data else None,
                'ultima_ubicacion': puntos_data[-1] if puntos_data else None,
                'total_fuera_de_zona': total_fuera_de_zona
            }
        }

        if not puntos_data:
            response_data['message'] = 'No se registraron puntos GPS para esta jornada.'

        return Response(response_data, status=status.HTTP_200_OK)


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
        evidencia_fin = request.data.get('evidencia_fin_url')
        if evidencia_fin in [None, '', 'null']:
            actividad.evidencia_fin_url = None
        else:
            actividad.evidencia_fin_url = evidencia_fin
        actividad.dispositivo_fin = request.data.get('dispositivo_fin')
        actividad.hora_fin_actividad = timezone.now()
        actividad.estado_actividad = 'finalizada'
        actividad.save()
        
        return Response(self.get_serializer(actividad).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def actual(self, request):
        user = request.user
        actividad = JornadaActividad.objects.filter(usuario=user, estado_actividad='en_proceso').first()
        if not actividad:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(actividad)
        return Response(serializer.data, status=status.HTTP_200_OK)


class HorarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HorarioSerializer

    def get_queryset(self):
        user = self.request.user
        sedes_ids = get_authorized_sedes_ids(user)
        queryset = Horario.objects.filter(activo=True)
        if sedes_ids is not None:
            queryset = queryset.filter(sede_id__in=sedes_ids)
        sede_id = self.request.query_params.get('sede')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user
        
        modo = data.get('modo')
        sede_id = data.get('sede_id')
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        dias = data.get('dias', [])
        usuarios_ids = data.get('usuarios_ids', [])
        
        if not sede_id:
            return Response({'error': 'La sede (sede_id) es obligatoria'}, status=status.HTTP_400_BAD_REQUEST)
        
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None and int(sede_id) not in sedes_ids:
            return Response({'error': 'No tienes permisos en la sede seleccionada'}, status=status.HTTP_403_FORBIDDEN)
            
        # Mapear para el serializador
        serializer_data = {
            'sede': sede_id,
            'nombre': nombre,
            'descripcion': descripcion,
            'tipo_configuracion': modo
        }
        
        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        horario = serializer.save(creado_por=user)
        
        # Guardar detalles (dias)
        if modo == 'general_unico':
            hora_inicio_entrada = data.get('hora_inicio_entrada')
            hora_fin_entrada = data.get('hora_fin_entrada')
            hora_inicio_salida = data.get('hora_inicio_salida')
            hora_fin_salida = data.get('hora_fin_salida')
            
            if not all([hora_inicio_entrada, hora_fin_entrada, hora_inicio_salida, hora_fin_salida]):
                return Response({'error': 'Faltan rangos de entrada/salida para el modo general_unico'}, status=status.HTTP_400_BAD_REQUEST)
                
            for dia in dias:
                HorarioDetalle.objects.create(
                    horario=horario,
                    dia_semana=dia.lower(),
                    hora_inicio_entrada=hora_inicio_entrada,
                    hora_fin_entrada=hora_fin_entrada,
                    hora_inicio_salida=hora_inicio_salida,
                    hora_fin_salida=hora_fin_salida
                )
        elif modo == 'personalizado_por_dias':
            for d in dias:
                HorarioDetalle.objects.create(
                    horario=horario,
                    dia_semana=d['dia_semana'].lower(),
                    hora_inicio_entrada=d['hora_inicio_entrada'],
                    hora_fin_entrada=d['hora_fin_entrada'],
                    hora_inicio_salida=d['hora_inicio_salida'],
                    hora_fin_salida=d['hora_fin_salida']
                )
        else:
            return Response({'error': 'Modo de configuración de horario inválido'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Asignar usuarios si se especifican
        if usuarios_ids:
            from datetime import date
            vigente_desde = data.get('vigente_desde')
            if not vigente_desde or vigente_desde == "":
                vigente_desde = date.today().isoformat()
            vigente_hasta = data.get('vigente_hasta')
            if not vigente_hasta or vigente_hasta == "":
                vigente_hasta = None
            
            # Validar cruces
            for u_id in usuarios_ids:
                if check_usuario_horario_overlap(u_id, horario.id, vigente_desde, vigente_hasta):
                    transaction.set_rollback(True)
                    return Response({'error': 'El usuario ya tiene un horario asignado que se cruza con este horario.'}, status=status.HTTP_400_BAD_REQUEST)
            
            for u_id in usuarios_ids:
                try:
                    target_user = Usuario.objects.get(id=u_id)
                except Usuario.DoesNotExist:
                    continue
                
                # Check user Sede authorized
                if sedes_ids is not None and target_user.sede_id not in sedes_ids:
                    continue
                
                # Crear asignación
                UsuarioHorario.objects.create(
                    usuario=target_user,
                    horario=horario,
                    sede_id=target_user.sede_id or horario.sede_id,
                    vigente_desde=vigente_desde,
                    vigente_hasta=vigente_hasta,
                    es_principal=True,
                    activo=True,
                    creado_por=user
                )
                
        return Response(self.get_serializer(horario).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        user = request.user
        
        modo = data.get('modo') or instance.tipo_configuracion
        sede_id = data.get('sede_id') or instance.sede_id
        nombre = data.get('nombre') or instance.nombre
        descripcion = data.get('descripcion') if 'descripcion' in data else instance.descripcion
        dias = data.get('dias', None)
        usuarios_ids = data.get('usuarios_ids', None)
        
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None and int(sede_id) not in sedes_ids:
            return Response({'error': 'No tienes permisos en la sede seleccionada'}, status=status.HTTP_403_FORBIDDEN)
            
        activo = data.get('activo') if 'activo' in data else instance.activo
        serializer_data = {
            'sede': sede_id,
            'nombre': nombre,
            'descripcion': descripcion,
            'tipo_configuracion': modo,
            'activo': activo
        }
        
        serializer = self.get_serializer(instance, data=serializer_data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        horario = serializer.save(actualizado_por=user)
        
        if not horario.activo:
            deactivate_dependent_relations(horario)
            
        # Si se envían días, se reemplazan los detalles antiguos
        if dias is not None:
            instance.detalles.all().delete()
            if modo == 'general_unico':
                hora_inicio_entrada = data.get('hora_inicio_entrada')
                hora_fin_entrada = data.get('hora_fin_entrada')
                hora_inicio_salida = data.get('hora_inicio_salida')
                hora_fin_salida = data.get('hora_fin_salida')
                
                # Intentar usar las del horario original si no se enviaron
                if not all([hora_inicio_entrada, hora_fin_entrada, hora_inicio_salida, hora_fin_salida]):
                    first_det = HorarioDetalle.objects.filter(horario=horario).first()
                    if first_det:
                        hora_inicio_entrada = hora_inicio_entrada or first_det.hora_inicio_entrada
                        hora_fin_entrada = hora_fin_entrada or first_det.hora_fin_entrada
                        hora_inicio_salida = hora_inicio_salida or first_det.hora_inicio_salida
                        hora_fin_salida = hora_fin_salida or first_det.hora_fin_salida
                
                for dia in dias:
                    HorarioDetalle.objects.create(
                        horario=horario,
                        dia_semana=dia.lower(),
                        hora_inicio_entrada=hora_inicio_entrada,
                        hora_fin_entrada=hora_fin_entrada,
                        hora_inicio_salida=hora_inicio_salida,
                        hora_fin_salida=hora_fin_salida
                    )
            elif modo == 'personalizado_por_dias':
                for d in dias:
                    HorarioDetalle.objects.create(
                        horario=horario,
                        dia_semana=d['dia_semana'].lower(),
                        hora_inicio_entrada=d['hora_inicio_entrada'],
                        hora_fin_entrada=d['hora_fin_entrada'],
                        hora_inicio_salida=d['hora_inicio_salida'],
                        hora_fin_salida=d['hora_fin_salida']
                    )

            # Validar si el cambio de detalles causó cruces para usuarios ya asignados
            if horario.activo:
                for uh in UsuarioHorario.objects.filter(horario=horario, activo=True):
                    if check_usuario_horario_overlap(uh.usuario_id, horario.id, uh.vigente_desde, uh.vigente_hasta, exclude_uh_id=uh.id):
                        transaction.set_rollback(True)
                        return Response({'error': 'El usuario ya tiene un horario asignado que se cruza con este horario.'}, status=status.HTTP_400_BAD_REQUEST)
                    
        # Si se envían usuarios, sincronizamos sus asignaciones
        if usuarios_ids is not None:
            from datetime import date
            vigente_desde = data.get('vigente_desde')
            if not vigente_desde or vigente_desde == "":
                vigente_desde = date.today().isoformat()
            vigente_hasta = data.get('vigente_hasta')
            if not vigente_hasta or vigente_hasta == "":
                vigente_hasta = None
            
            # 1. Desactivar asignaciones de usuarios que YA NO están en la lista
            UsuarioHorario.objects.filter(horario=horario, activo=True).exclude(usuario_id__in=usuarios_ids).update(activo=False, es_principal=False)
            
            # 2. Agregar asignaciones para los usuarios nuevos en la lista
            for u_id in usuarios_ids:
                exists = UsuarioHorario.objects.filter(horario=horario, usuario_id=u_id, activo=True).exists()
                if not exists:
                    try:
                        target_user = Usuario.objects.get(id=u_id)
                    except Usuario.DoesNotExist:
                        continue
                    
                    if sedes_ids is not None and target_user.sede_id not in sedes_ids:
                        continue
                    
                    if check_usuario_horario_overlap(u_id, horario.id, vigente_desde, vigente_hasta):
                        transaction.set_rollback(True)
                        return Response({'error': 'El usuario ya tiene un horario asignado que se cruza con este horario.'}, status=status.HTTP_400_BAD_REQUEST)
                        
                    UsuarioHorario.objects.create(
                        usuario=target_user,
                        horario=horario,
                        sede_id=target_user.sede_id,
                        vigente_desde=vigente_desde,
                        vigente_hasta=vigente_hasta,
                        es_principal=True,
                        activo=True,
                        creado_por=user
                    )
                    
        return Response(self.get_serializer(horario).data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.activo = False
        instance.actualizado_por = request.user
        instance.save()
        deactivate_dependent_relations(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UsuarioHorarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UsuarioHorarioSerializer

    def get_queryset(self):
        user = self.request.user
        sedes_ids = get_authorized_sedes_ids(user)
        queryset = UsuarioHorario.objects.filter(activo=True)
        if sedes_ids is not None:
            queryset = queryset.filter(sede_id__in=sedes_ids)
        sede_id = self.request.query_params.get('sede')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        u_id = request.data.get('usuario')
        h_id = request.data.get('horario')
        vigente_desde = request.data.get('vigente_desde')
        vigente_hasta = request.data.get('vigente_hasta', None)
        observacion = request.data.get('observacion', '')
        from datetime import date
        if not vigente_desde or vigente_desde == "":
            vigente_desde = date.today().isoformat()
        if vigente_hasta == "":
            vigente_hasta = None

        if not all([u_id, h_id, vigente_desde]):
            return Response({'error': 'Los campos usuario, horario y vigente_desde son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            target_user = Usuario.objects.get(id=u_id)
            horario = Horario.objects.get(id=h_id)
        except (Usuario.DoesNotExist, Horario.DoesNotExist):
            return Response({'error': 'Usuario o Horario no existen'}, status=status.HTTP_404_NOT_FOUND)
            
        # Security validation
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            if target_user.sede_id not in sedes_ids or horario.sede_id not in sedes_ids:
                return Response({'error': 'No tienes permisos en las sedes correspondientes'}, status=status.HTTP_403_FORBIDDEN)
                
        # Validar cruces
        if check_usuario_horario_overlap(u_id, h_id, vigente_desde, vigente_hasta):
            transaction.set_rollback(True)
            return Response({'error': 'El usuario ya tiene un horario asignado que se cruza con este horario.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create assignment
        uh = UsuarioHorario.objects.create(
            usuario=target_user,
            horario=horario,
            sede_id=target_user.sede_id or horario.sede_id,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
            es_principal=True,
            activo=True,
            observacion=observacion,
            creado_por=user
        )
        
        return Response(self.get_serializer(uh).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        user = request.user
        
        u_id = data.get('usuario') or instance.usuario_id
        h_id = data.get('horario') or instance.horario_id
        vigente_desde = data.get('vigente_desde')
        vigente_hasta = data.get('vigente_hasta')
        
        if vigente_desde is None:
            vigente_desde = instance.vigente_desde
        if vigente_hasta is None:
            vigente_hasta = instance.vigente_hasta
        elif vigente_hasta == "":
            vigente_hasta = None
            
        try:
            target_user = Usuario.objects.get(id=u_id)
            horario = Horario.objects.get(id=h_id)
        except (Usuario.DoesNotExist, Horario.DoesNotExist):
            return Response({'error': 'Usuario o Horario no existen'}, status=status.HTTP_404_NOT_FOUND)
            
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            if target_user.sede_id not in sedes_ids or horario.sede_id not in sedes_ids:
                return Response({'error': 'No tienes permisos en las sedes correspondientes'}, status=status.HTTP_403_FORBIDDEN)
                
        is_active = data.get('activo', True) if 'activo' in data else instance.activo
        if is_active:
            if check_usuario_horario_overlap(u_id, h_id, vigente_desde, vigente_hasta, exclude_uh_id=instance.id):
                transaction.set_rollback(True)
                return Response({'error': 'El usuario ya tiene un horario asignado que se cruza con este horario.'}, status=status.HTTP_400_BAD_REQUEST)
                
        serializer = self.get_serializer(instance, data=data, partial=kwargs.get('partial', False))
        serializer.is_valid(raise_exception=True)
        uh = serializer.save(actualizado_por=user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.activo = False
        instance.es_principal = False
        instance.actualizado_por = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IntercambioHorarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = IntercambioHorarioSerializer

    def get_queryset(self):
        user = self.request.user
        sedes_ids = get_authorized_sedes_ids(user)
        queryset = IntercambioHorario.objects.filter(activo=True)
        if sedes_ids is not None:
            queryset = queryset.filter(sede_id__in=sedes_ids)
        sede_id = self.request.query_params.get('sede')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        solicitante_id = request.data.get('usuario_solicitante')
        reemplazo_id = request.data.get('usuario_reemplazo')
        fecha_str = request.data.get('fecha_intercambio')
        motivo = request.data.get('motivo', '')
        observacion = request.data.get('observacion', '')
        
        if not all([solicitante_id, reemplazo_id, fecha_str]):
            return Response({'error': 'Los campos usuario_solicitante, usuario_reemplazo y fecha_intercambio son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)
            
        from datetime import datetime
        try:
            fecha_val = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Fecha con formato inválido (debe ser YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            solicitante = Usuario.objects.get(id=solicitante_id)
            reemplazo = Usuario.objects.get(id=reemplazo_id)
        except Usuario.DoesNotExist:
            return Response({'error': 'Uno o ambos usuarios no existen'}, status=status.HTTP_404_NOT_FOUND)
            
        # Security validation: same sede and authorized sede
        sedes_ids = get_authorized_sedes_ids(user)
        if sedes_ids is not None:
            if solicitante.sede_id not in sedes_ids or reemplazo.sede_id not in sedes_ids:
                return Response({'error': 'No tienes permisos en las sedes de estos usuarios'}, status=status.HTTP_403_FORBIDDEN)
                
        # Resolve original schedules directly from UsuarioHorario (avoiding exchange recursion)
        uh_sol = UsuarioHorario.objects.filter(
            usuario=solicitante,
            activo=True,
            vigente_desde__lte=fecha_val
        ).filter(Q(vigente_hasta__gte=fecha_val) | Q(vigente_hasta__isnull=True)).first()
        h_sol = uh_sol.horario if uh_sol else None

        uh_ree = UsuarioHorario.objects.filter(
            usuario=reemplazo,
            activo=True,
            vigente_desde__lte=fecha_val
        ).filter(Q(vigente_hasta__gte=fecha_val) | Q(vigente_hasta__isnull=True)).first()
        h_ree = uh_ree.horario if uh_ree else None
        
        # Create exchange record
        intercambio = IntercambioHorario.objects.create(
            sede_id=solicitante.sede_id,
            usuario_solicitante=solicitante,
            usuario_reemplazo=reemplazo,
            fecha_intercambio=fecha_val,
            horario_solicitante_original=h_sol,
            horario_reemplazo_original=h_ree,
            estado='aprobado',
            motivo=motivo,
            observacion=observacion,
            registrado_por=user,
            aprobado_por=user,
            aprobado_at=timezone.now()
        )
        
        return Response(self.get_serializer(intercambio).data, status=status.HTTP_201_CREATED)


class SedesResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        sedes_ids = get_authorized_sedes_ids(user)
        
        if sedes_ids is not None:
            sedes = Sede.objects.filter(id__in=sedes_ids, activo=True)
        else:
            sedes = Sede.objects.filter(activo=True)
            
        resumen = []
        for s in sedes:
            # Horarios creados para esta sede
            horarios_creados = Horario.objects.filter(sede=s, activo=True).count()
            
            # Usuarios de esta sede
            usuarios_sede = Usuario.objects.filter(sede=s, activo=True)
            
            # De estos usuarios, cuántos tienen un horario asignado actualmente (o en el futuro)
            # Para simplificar, buscamos si tienen algún UsuarioHorario activo principal
            usuarios_con_horario = UsuarioHorario.objects.filter(
                usuario__in=usuarios_sede, 
                activo=True, 
                es_principal=True
            ).values_list('usuario_id', flat=True).distinct().count()
            
            total_usuarios = usuarios_sede.count()
            usuarios_sin_horario = total_usuarios - usuarios_con_horario
            
            # Intercambios registrados para esta sede
            intercambios_count = IntercambioHorario.objects.filter(sede=s, activo=True).count()
            
            resumen.append({
                'sede_id': s.id,
                'sede_nombre': s.nombre,
                'horarios_creados': horarios_creados,
                'usuarios_con_horario': usuarios_con_horario,
                'usuarios_sin_horario': max(0, usuarios_sin_horario),
                'intercambios_count': intercambios_count
            })
            
        return Response(resumen, status=status.HTTP_200_OK)


class DashboardResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        rol_nombre = user.rol.nombre.lower() if user.rol else ''
        is_admin = any(role in rol_nombre for role in ['admin', 'superadmin', 'super administrador'])
        is_gerente = any(role in rol_nombre for role in ['gerente', 'supervisor'])

        if not is_admin and not is_gerente:
            return Response({'error': 'No tiene permisos para ver este panel.'}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.localdate() if timezone.is_aware(timezone.now()) else timezone.now().date()
        rango = request.query_params.get('rango', 'hoy').lower()
        sede_id = request.query_params.get('sede', None)

        if rango == 'semana':
            fecha_inicio = today - timezone.timedelta(days=6)
            fecha_fin = today
        elif rango == 'mes':
            fecha_inicio = today - timezone.timedelta(days=29)
            fecha_fin = today
        else: # default 'hoy'
            fecha_inicio = today
            fecha_fin = today

        # Overwrite if explicit query params are passed
        fecha_inicio_param = request.query_params.get('fecha_inicio', None)
        fecha_fin_param = request.query_params.get('fecha_fin', None)
        if fecha_inicio_param:
            try:
                fecha_inicio = timezone.datetime.strptime(fecha_inicio_param, '%Y-%m-%d').date()
            except ValueError:
                pass
        if fecha_fin_param:
            try:
                fecha_fin = timezone.datetime.strptime(fecha_fin_param, '%Y-%m-%d').date()
            except ValueError:
                pass

        authorized_sedes = get_authorized_sedes_ids(user)
        if authorized_sedes is not None:
            if sede_id:
                try:
                    s_id = int(sede_id)
                    if s_id in authorized_sedes:
                        sedes_filter = [s_id]
                    else:
                        sedes_filter = []
                except ValueError:
                    sedes_filter = authorized_sedes
            else:
                sedes_filter = authorized_sedes
        else:
            if sede_id:
                try:
                    sedes_filter = [int(sede_id)]
                except ValueError:
                    sedes_filter = None
            else:
                sedes_filter = None

        # 1. Resumen general
        usuarios_qs = Usuario.objects.all()
        if sedes_filter is not None:
            usuarios_qs = usuarios_qs.filter(sede_id__in=sedes_filter)

        total_usuarios = usuarios_qs.count()
        total_operadores = usuarios_qs.filter(rol__codigo__iexact='operador').count()
        total_asesores = usuarios_qs.filter(rol__codigo__iexact='asesor').count()
        total_gerentes = usuarios_qs.filter(rol__codigo__in=['gerente', 'supervisor']).count()
        usuarios_activos = usuarios_qs.filter(activo=True).count()
        usuarios_inactivos = usuarios_qs.filter(activo=False).count()

        sedes_qs = Sede.objects.all()
        if sedes_filter is not None:
            sedes_qs = sedes_qs.filter(id__in=sedes_filter)
        total_sedes = sedes_qs.count()
        sedes_activas = sedes_qs.filter(activo=True).count()

        # 2. Resumen de jornadas del periodo
        jornadas_qs = HistorialJornada.objects.filter(fecha__range=(fecha_inicio, fecha_fin))
        if sedes_filter is not None:
            jornadas_qs = jornadas_qs.filter(sede_id__in=sedes_filter)

        jornadas_programadas = jornadas_qs.filter(estado_asistencia='programada').count()
        jornadas_en_proceso = jornadas_qs.filter(estado_asistencia='en_proceso').count()
        jornadas_completas = jornadas_qs.filter(estado_asistencia__in=['completa', 'completada']).count()
        jornadas_incompletas = jornadas_qs.filter(estado_asistencia='incompleta').count()
        jornadas_ausentes = jornadas_qs.filter(estado_asistencia='ausente').count()

        total_entradas_marcadas = jornadas_qs.filter(hora_entrada__isnull=False).count()
        total_salidas_marcadas = jornadas_qs.filter(hora_salida__isnull=False).count()

        # 3. Puntualidad
        puntual = jornadas_qs.filter(estado_puntualidad='puntual').count()
        tardanza = jornadas_qs.filter(estado_puntualidad='tardanza').count()
        temprano = jornadas_qs.filter(estado_puntualidad='temprano').count()
        no_marco_entrada = jornadas_qs.filter(estado_puntualidad='no_marco_entrada').count()

        # 4. Salidas
        salida_en_rango = jornadas_qs.filter(estado_salida='puntual').count()
        salida_fuera_rango = jornadas_qs.filter(estado_salida='tardanza').count()
        no_marco_salida = jornadas_qs.filter(estado_salida='no_marco_salida').count()

        # 5. Incidencias
        incidencias_qs = Incidencia.objects.filter(fecha_hora_reporte__date__range=(fecha_inicio, fecha_fin))
        if sedes_filter is not None:
            incidencias_qs = incidencias_qs.filter(usuario__sede_id__in=sedes_filter)

        incidencias_hoy_qs = Incidencia.objects.filter(fecha_hora_reporte__date=today)
        if sedes_filter is not None:
            incidencias_hoy_qs = incidencias_hoy_qs.filter(usuario__sede_id__in=sedes_filter)

        total_incidencias_hoy = incidencias_hoy_qs.count()
        incidencias_pendientes = incidencias_qs.filter(estado_revision__iexact='pendiente').count()
        incidencias_revisadas = incidencias_qs.filter(estado_revision__in=['aprobado', 'rechazado']).count()

        incidencias_por_tipo = []
        tipo_counts = incidencias_qs.values('tipo_incidencia').annotate(count=models.Count('id')).order_by('-count')
        for tc in tipo_counts:
            incidencias_por_tipo.append({
                'tipo': tc['tipo_incidencia'] or 'Otro',
                'cantidad': tc['count']
            })

        # 6. Actividades de asesores
        actividades_qs = JornadaActividad.objects.filter(hora_inicio_actividad__date__range=(fecha_inicio, fecha_fin))
        if sedes_filter is not None:
            actividades_qs = actividades_qs.filter(sede_id__in=sedes_filter)

        actividades_hoy_qs = JornadaActividad.objects.filter(hora_inicio_actividad__date=today)
        if sedes_filter is not None:
            actividades_hoy_qs = actividades_hoy_qs.filter(sede_id__in=sedes_filter)

        actividades_hoy = actividades_hoy_qs.count()
        actividades_en_proceso = actividades_qs.filter(estado_actividad='en_proceso').count()
        actividades_finalizadas = actividades_qs.filter(estado_actividad='finalizada').count()

        asesores_qs = usuarios_qs.filter(rol__codigo__iexact='asesor', activo=True)
        total_asesores_activos = asesores_qs.count()
        asesores_con_act_ids = actividades_qs.values_list('usuario_id', flat=True).distinct()
        asesores_con_actividad = asesores_qs.filter(id__in=asesores_con_act_ids).count()
        asesores_sin_actividad = max(0, total_asesores_activos - asesores_con_actividad)

        # 7. Tracking GPS
        gps_hoy_qs = UbicacionPunto.objects.filter(fecha_hora__date=today)
        if sedes_filter is not None:
            gps_hoy_qs = gps_hoy_qs.filter(usuario__sede_id__in=sedes_filter)

        total_puntos_gps_hoy = gps_hoy_qs.count()

        fifteen_mins_ago = timezone.now() - timezone.timedelta(minutes=15)
        active_tracking_users = UbicacionPunto.objects.filter(fecha_hora__gte=fifteen_mins_ago)
        if sedes_filter is not None:
            active_tracking_users = active_tracking_users.filter(usuario__sede_id__in=sedes_filter)
        usuarios_con_tracking_activo = active_tracking_users.values('usuario').distinct().count()

        usuarios_fuera_de_zona = gps_hoy_qs.filter(es_fuera_de_zona=True).values('usuario').distinct().count()

        # Ultima ubicacion registrada por usuario hoy
        ultimas_ubicaciones = []
        users_with_gps = list(gps_hoy_qs.values_list('usuario_id', flat=True).distinct())
        for user_id in users_with_gps:
            latest_point = gps_hoy_qs.filter(usuario_id=user_id).select_related('usuario').order_by('-fecha_hora').first()
            if latest_point:
                ultimas_ubicaciones.append({
                    'usuario_id': user_id,
                    'usuario_nombre': latest_point.usuario.nombre_completo,
                    'latitud': float(latest_point.latitud),
                    'longitud': float(latest_point.longitud),
                    'fecha_hora': latest_point.fecha_hora.isoformat(),
                    'bateria': latest_point.bateria_porcentaje,
                    'es_fuera_de_zona': latest_point.es_fuera_de_zona,
                    'distancia_sede_metros': float(latest_point.distancia_sede_metros) if latest_point.distancia_sede_metros else None
                })

        # 8. Datos para gráficos
        by_date = {}
        curr = fecha_inicio
        while curr <= fecha_fin:
            by_date[curr.isoformat()] = {'fecha': curr.isoformat(), 'completa': 0, 'incompleta': 0, 'ausente': 0}
            curr += timezone.timedelta(days=1)

        day_stats = jornadas_qs.values('fecha', 'estado_asistencia').annotate(count=models.Count('id'))
        for ds in day_stats:
            f_str = ds['fecha'].isoformat()
            est = ds['estado_asistencia']
            if f_str in by_date:
                if est in ['completa', 'completada']:
                    by_date[f_str]['completa'] += ds['count']
                elif est == 'incompleta':
                    by_date[f_str]['incompleta'] += ds['count']
                elif est == 'ausente':
                    by_date[f_str]['ausente'] += ds['count']
        asistencia_por_dia_semana = list(by_date.values())

        jornadas_por_estado = [
            {'estado': 'Programada', 'cantidad': jornadas_programadas},
            {'estado': 'En Proceso', 'cantidad': jornadas_en_proceso},
            {'estado': 'Completada', 'cantidad': jornadas_completas},
            {'estado': 'Incompleta', 'cantidad': jornadas_incompletas},
            {'estado': 'Ausente', 'cantidad': jornadas_ausentes}
        ]

        puntualidad_por_estado = [
            {'estado': 'Puntual', 'cantidad': puntual},
            {'estado': 'Tardanza', 'cantidad': tardanza},
            {'estado': 'Temprano', 'cantidad': temprano},
            {'estado': 'No Marcó', 'cantidad': no_marco_entrada}
        ]

        actividades_por_estado = [
            {'estado': 'En Proceso', 'cantidad': actividades_en_proceso},
            {'estado': 'Finalizada', 'cantidad': actividades_finalizadas}
        ]

        usuarios_por_sede = []
        sede_counts = usuarios_qs.values('sede__nombre').annotate(count=models.Count('id')).order_by('-count')
        for sc in sede_counts:
            usuarios_por_sede.append({
                'sede': sc['sede__nombre'] or 'Sin Sede',
                'cantidad': sc['count']
            })

        # 9. Actividad reciente
        eventos_qs = AsistenciaEvento.objects.select_related('usuario', 'usuario__rol', 'usuario__sede').all()
        if sedes_filter is not None:
            eventos_qs = eventos_qs.filter(usuario__sede_id__in=sedes_filter)
        eventos_recent = eventos_qs.order_by('-fecha_hora')[:15]

        incidencias_recent_qs = Incidencia.objects.select_related('usuario', 'usuario__rol', 'usuario__sede').all()
        if sedes_filter is not None:
            incidencias_recent_qs = incidencias_recent_qs.filter(usuario__sede_id__in=sedes_filter)
        incidencias_recent = incidencias_recent_qs.order_by('-fecha_hora_reporte')[:15]

        actividades_recent_qs = JornadaActividad.objects.select_related('usuario', 'usuario__rol', 'sede').all()
        if sedes_filter is not None:
            actividades_recent_qs = actividades_recent_qs.filter(sede_id__in=sedes_filter)
        actividades_recent = actividades_recent_qs.order_by('-hora_inicio_actividad')[:15]

        fuera_recent_qs = UbicacionPunto.objects.filter(es_fuera_de_zona=True).select_related('usuario', 'usuario__rol', 'usuario__sede').all()
        if sedes_filter is not None:
            fuera_recent_qs = fuera_recent_qs.filter(usuario__sede_id__in=sedes_filter)
        fuera_recent = fuera_recent_qs.order_by('-fecha_hora')[:15]

        unified_events = []
        for e in eventos_recent:
            unified_events.append({
                'usuario': e.usuario.nombre_completo,
                'rol': e.usuario.rol.nombre if e.usuario.rol else 'Operador',
                'sede': e.usuario.sede.nombre if e.usuario.sede else 'Sede Principal',
                'tipo_evento': e.tipo_evento,
                'fecha_hora': e.fecha_hora.isoformat(),
                'estado': 'info',
                'descripcion': f"Marcó {e.tipo_evento.replace('_', ' ').lower()}"
            })
        for inc in incidencias_recent:
            unified_events.append({
                'usuario': inc.usuario.nombre_completo,
                'rol': inc.usuario.rol.nombre if inc.usuario.rol else 'Operador',
                'sede': inc.usuario.sede.nombre if inc.usuario.sede else 'Sede Principal',
                'tipo_evento': 'INCIDENCIA',
                'fecha_hora': inc.fecha_hora_reporte.isoformat(),
                'estado': 'danger',
                'descripcion': f"Reportó incidencia: {inc.tipo_incidencia}"
            })
        for act in actividades_recent:
            unified_events.append({
                'usuario': act.usuario.nombre_completo,
                'rol': act.usuario.rol.nombre if act.usuario.rol else 'Asesor',
                'sede': act.sede.nombre if act.sede else 'Sede Principal',
                'tipo_evento': 'ACTIVIDAD_INICIO',
                'fecha_hora': act.hora_inicio_actividad.isoformat(),
                'estado': 'warning' if act.estado_actividad == 'en_proceso' else 'success',
                'descripcion': f"Inició actividad: {act.titulo}"
            })
            if act.hora_fin_actividad:
                unified_events.append({
                    'usuario': act.usuario.nombre_completo,
                    'rol': act.usuario.rol.nombre if act.usuario.rol else 'Asesor',
                    'sede': act.sede.nombre if act.sede else 'Sede Principal',
                    'tipo_evento': 'ACTIVIDAD_FIN',
                    'fecha_hora': act.hora_fin_actividad.isoformat(),
                    'estado': 'success',
                    'descripcion': f"Finalizó actividad: {act.titulo}"
                })
        for f in fuera_recent:
            unified_events.append({
                'usuario': f.usuario.nombre_completo,
                'rol': f.usuario.rol.nombre if f.usuario.rol else 'Operador',
                'sede': f.usuario.sede.nombre if f.usuario.sede else 'Sede Principal',
                'tipo_evento': 'FUERA_DE_ZONA',
                'fecha_hora': f.fecha_hora.isoformat(),
                'estado': 'danger',
                'descripcion': "Se detectó fuera de la zona autorizada"
            })

        unified_events.sort(key=lambda x: x['fecha_hora'], reverse=True)
        recent_activity = unified_events[:20]

        resumen_data = {
            'resumen_general': {
                'total_usuarios': total_usuarios,
                'total_operadores': total_operadores,
                'total_asesores': total_asesores,
                'total_gerentes': total_gerentes,
                'total_sedes': total_sedes,
                'sedes_activas': sedes_activas,
                'usuarios_activos': usuarios_activos,
                'usuarios_inactivos': usuarios_inactivos
            },
            'jornadas_dia': {
                'jornadas_programadas': jornadas_programadas,
                'jornadas_en_proceso': jornadas_en_proceso,
                'jornadas_completas': jornadas_completas,
                'jornadas_incompletas': jornadas_incompletas,
                'jornadas_ausentes': jornadas_ausentes,
                'total_entradas_marcadas': total_entradas_marcadas,
                'total_salidas_marcadas': total_salidas_marcadas
            },
            'puntualidad': {
                'puntual': puntual,
                'tardanza': tardanza,
                'temprano': temprano,
                'no_marco_entrada': no_marco_entrada
            },
            'salidas': {
                'salida_en_rango': salida_en_rango,
                'salida_fuera_rango': salida_fuera_rango,
                'no_marco_salida': no_marco_salida
            },
            'incidencias': {
                'total_incidencias_hoy': total_incidencias_hoy,
                'incidencias_pendientes': incidencias_pendientes,
                'incidencias_revisadas': incidencias_revisadas,
                'incidencias_por_tipo': incidencias_por_tipo
            },
            'actividades': {
                'actividades_hoy': actividades_hoy,
                'actividades_en_proceso': actividades_en_proceso,
                'actividades_finalizadas': actividades_finalizadas,
                'asesores_con_actividad': asesores_con_actividad,
                'asesores_sin_actividad': asesores_sin_actividad
            },
            'tracking': {
                'usuarios_con_tracking_activo': usuarios_con_tracking_activo,
                'usuarios_fuera_de_zona': usuarios_fuera_de_zona,
                'total_puntos_gps_hoy': total_puntos_gps_hoy,
                'ultimas_ubicaciones': ultimas_ubicaciones
            },
            'graficos': {
                'asistencia_por_dia_semana': asistencia_por_dia_semana,
                'jornadas_por_estado': jornadas_por_estado,
                'puntualidad_por_estado': puntualidad_por_estado,
                'incidencias_por_tipo': incidencias_por_tipo,
                'actividades_por_estado': actividades_por_estado,
                'usuarios_por_sede': usuarios_por_sede
            },
            'actividad_reciente': recent_activity
        }

        return Response(resumen_data, status=status.HTTP_200_OK)


class DatabaseConnectionCheckView(APIView):
    permission_classes = []

    def get(self, request):
        from django.db import connection
        from django.db.utils import OperationalError
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
                if row is None:
                    raise OperationalError("No response from database query.")
            return Response({
                "status": "connected",
                "database": connection.settings_dict.get('NAME'),
                "message": "Conexión exitosa con la base de datos."
            }, status=status.HTTP_200_OK)
        except OperationalError as e:
            return Response({
                "status": "disconnected",
                "message": "Error al conectar con la base de datos.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                "status": "error",
                "message": "Ocurrió un error inesperado al verificar la conexión.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
