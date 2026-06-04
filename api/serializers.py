from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia, JornadaConfiguracion, HistorialJornada, JornadaActividad, Horario, HorarioDetalle, UsuarioHorario, IntercambioHorario

class JornadaActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = JornadaActividad
        fields = '__all__'
        read_only_fields = ('usuario', 'asistencia', 'historial_jornada', 'sede', 'hora_inicio_actividad', 'hora_fin_actividad', 'estado_actividad')

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

class JornadaConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JornadaConfiguracion
        fields = '__all__'

class RolSerializer(serializers.ModelSerializer):

    class Meta:
        model = Rol
        fields = '__all__'

class TipoIncidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIncidencia
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    sede_info = SedeSerializer(source='sede', read_only=True)
    rol_info = RolSerializer(source='rol', read_only=True)
    sedes_ids = serializers.SerializerMethodField()
    class Meta:
        model = Usuario
        fields = ('id', 'dni', 'nombre_completo', 'cargo', 'telefono', 'email', 'sede', 'rol', 'sede_info', 'rol_info', 'is_active', 'activo', 'debe_cambiar_password', 'observacion', 'sedes_ids', 'creado_at')

    def get_sedes_ids(self, obj):
        return list(obj.sedes_asignadas.values_list('sede_id', flat=True))

class UsuarioCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    sedes_ids = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Usuario
        fields = ('dni', 'nombre_completo', 'password', 'cargo', 'telefono', 'email', 'sede', 'rol', 'activo', 'is_active', 'debe_cambiar_password', 'observacion', 'sedes_ids')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        sedes_ids = validated_data.pop('sedes_ids', [])
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
            
        # Sincronizar sedes
        if sedes_ids:
            from .models import UsuarioSede
            # Limpiar por si acaso (aunque en create no debería haber)
            UsuarioSede.objects.filter(usuario=user).delete()
            for s_id in sedes_ids:
                UsuarioSede.objects.create(
                    usuario=user, 
                    sede_id=s_id, 
                    puede_gestionar=True, 
                    puede_visualizar=True,
                    es_principal=(s_id == user.sede_id),
                    activo=True
                )
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        sedes_ids = validated_data.pop('sedes_ids', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
            
        # Sincronizar sedes si se enviaron
        if sedes_ids is not None:
            from .models import UsuarioSede
            UsuarioSede.objects.filter(usuario=user).delete()
            for s_id in sedes_ids:
                UsuarioSede.objects.create(
                    usuario=user, 
                    sede_id=s_id, 
                    puede_gestionar=True, 
                    puede_visualizar=True,
                    es_principal=(s_id == user.sede_id),
                    activo=True
                )
        return user

class AsistenciaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.ReadOnlyField(source='usuario.sede.nombre')
    
    class Meta:
        model = Asistencia
        fields = '__all__'

class IncidenciaSerializer(serializers.ModelSerializer):
    tipo_incidencia_0 = TipoIncidenciaSerializer(read_only=True)
    foto = serializers.SerializerMethodField()

    class Meta:
        model = Incidencia
        fields = '__all__'
        read_only_fields = ('usuario', 'asistencia', 'fecha_hora_reporte', 'estado_revision')

    def get_foto(self, obj):
        if obj.foto_evidencia_url:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.foto_evidencia_url.url)
            return obj.foto_evidencia_url.url
        return obj.evidencia_url or None

class AsistenciaEventoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsistenciaEvento
        fields = '__all__'

class ConfiguracionTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionTracking
        fields = '__all__'

class UbicacionPuntoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UbicacionPunto
        fields = '__all__'
        read_only_fields = ('usuario', 'asistencia', 'es_fuera_de_zona', 'distancia_sede_metros', 'fecha_hora')

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Permitir que el campo se llame 'dni' o 'username'
        self.fields['dni'] = serializers.CharField(required=False)
        self.fields['username'] = serializers.CharField(required=False)
        self.fields['origen'] = serializers.CharField(required=False)

    def validate(self, attrs):
        # Mapear 'dni' a 'username' si viene en la petición
        if 'dni' in attrs and not attrs.get('username'):
            attrs['username'] = attrs['dni']
        # Mapear 'username' a 'dni' si viene en la petición (ej. desde clientes genéricos de API)
        if 'username' in attrs and not attrs.get('dni'):
            attrs['dni'] = attrs['username']
            
        origen = attrs.get('origen')
        
        data = super().validate(attrs)
        
        # Agregar información extra al token
        data['user_role'] = self.user.rol.codigo if self.user.rol else ''
        data['user_name'] = self.user.nombre_completo
        
        # Validar el rol si el origen es 'movil'
        if origen == 'movil':
            # Inner join con roles
            from .models import Usuario
            try:
                user = Usuario.objects.select_related('rol').get(dni=attrs['username'])
                # Validar por codigo (campo normalizado) Y por nombre (fallback),
                # en minúsculas para evitar errores de capitalización
                rol_codigo = (user.rol.codigo or '').lower() if user.rol else ''
                rol_nombre = (user.rol.nombre or '').lower() if user.rol else ''
                es_movil_permitido = (
                    rol_codigo in ['operador', 'asesor'] or
                    rol_nombre in ['operador', 'asesor']
                )
                if not user.rol or not es_movil_permitido:
                    raise serializers.ValidationError({"detail": "Acceso denegado. Solo los operadores y asesores pueden usar la app móvil."})
            except Usuario.DoesNotExist:
                raise serializers.ValidationError({"detail": "Usuario no encontrado."})
                
        return data

class HistorialJornadaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.nombre_completo')
    sede_nombre = serializers.SerializerMethodField()

    class Meta:
        model = HistorialJornada
        fields = '__all__'

    def get_sede_nombre(self, obj):
        if obj.sede_id:
            sede = Sede.objects.filter(id=obj.sede_id).first()
            return sede.nombre if sede else f"Sede {obj.sede_id}"
        return "-"

class HistorialJornadaListSerializer(serializers.ModelSerializer):
    operador = serializers.ReadOnlyField(source='usuario.nombre_completo')
    sede = serializers.SerializerMethodField()
    total_incidencias = serializers.IntegerField(read_only=True)
    total_puntos_gps = serializers.IntegerField(read_only=True)

    class Meta:
        model = HistorialJornada
        fields = [
            'id', 'operador', 'sede', 'fecha', 'hora_entrada', 'hora_inicio_break', 
            'hora_fin_break', 'hora_salida', 'total_tiempo_break', 'total_horas_trabajadas', 
            'estado_puntualidad', 'estado_salida', 'estado_jornada', 'cerrado', 'cerrado_at', 
            'total_incidencias', 'total_puntos_gps', 'estado_asistencia'
        ]

    def get_sede(self, obj):
        if obj.sede_id:
            from .models import Sede
            sede = Sede.objects.filter(id=obj.sede_id).first()
            return sede.nombre if sede else f"Sede {obj.sede_id}"
        return "-"
class HistorialJornadaDetailSerializer(serializers.ModelSerializer):
    operador = serializers.ReadOnlyField(source='usuario.nombre_completo')
    sede = serializers.SerializerMethodField()
    eventos = AsistenciaEventoSerializer(source='asistencia.eventos', many=True, read_only=True)
    incidencias = IncidenciaSerializer(source='asistencia.incidencias_detalle', many=True, read_only=True)
    total_puntos_gps = serializers.SerializerMethodField()
    actividades_campo = serializers.SerializerMethodField()
    rol_codigo = serializers.ReadOnlyField(source='usuario.rol.codigo')
    rol_nombre = serializers.ReadOnlyField(source='usuario.rol.nombre')

    class Meta:
        model = HistorialJornada
        fields = [
            'id', 'operador', 'sede', 'fecha', 'hora_entrada', 'hora_inicio_break', 
            'hora_fin_break', 'hora_salida', 'total_tiempo_break', 'total_horas_trabajadas', 
            'estado_jornada', 'cerrado', 'cerrado_at', 'observacion',
            'eventos', 'incidencias', 'total_puntos_gps', 'actividades_campo',
            'rol_codigo', 'rol_nombre', 'estado_asistencia', 'estado_puntualidad', 'estado_salida'
        ]

    def get_total_puntos_gps(self, obj):
        if obj.asistencia:
            return obj.asistencia.puntos_gps.filter(latitud__isnull=False, longitud__isnull=False).count()
        return 0

    def get_sede(self, obj):
        if obj.sede_id:
            sede = Sede.objects.filter(id=obj.sede_id).first()
            return sede.nombre if sede else f"Sede {obj.sede_id}"
        return "-"

    def get_actividades_campo(self, obj):
        actividades = obj.actividades_jornada.all().order_by('hora_inicio_actividad')
        return JornadaActividadSerializer(actividades, many=True, context=self.context).data


class HorarioDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioDetalle
        fields = '__all__'


class HorarioSerializer(serializers.ModelSerializer):
    detalles = HorarioDetalleSerializer(many=True, read_only=True)
    sede_nombre = serializers.ReadOnlyField(source='sede.nombre')
    creado_por_nombre = serializers.ReadOnlyField(source='creado_por.nombre_completo')
    usuario_count = serializers.SerializerMethodField()

    class Meta:
        model = Horario
        fields = '__all__'

    def get_usuario_count(self, obj):
        return obj.usuarios_horario.filter(activo=True).count()


class UsuarioHorarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.ReadOnlyField(source='usuario.nombre_completo')
    usuario_rol = serializers.ReadOnlyField(source='usuario.rol.nombre')
    horario_nombre = serializers.ReadOnlyField(source='horario.nombre')
    sede_nombre = serializers.ReadOnlyField(source='sede.nombre')
    horario_detalles = HorarioDetalleSerializer(source='horario.detalles', many=True, read_only=True)

    class Meta:
        model = UsuarioHorario
        fields = '__all__'


class IntercambioHorarioSerializer(serializers.ModelSerializer):
    usuario_solicitante_nombre = serializers.ReadOnlyField(source='usuario_solicitante.nombre_completo')
    usuario_reemplazo_nombre = serializers.ReadOnlyField(source='usuario_reemplazo.nombre_completo')
    horario_solicitante_original_nombre = serializers.ReadOnlyField(source='horario_solicitante_original.nombre')
    horario_reemplazo_original_nombre = serializers.ReadOnlyField(source='horario_reemplazo_original.nombre')
    registrado_por_nombre = serializers.ReadOnlyField(source='registrado_por.nombre_completo')
    aprobado_por_nombre = serializers.ReadOnlyField(source='aprobado_por.nombre_completo')

    class Meta:
        model = IntercambioHorario
        fields = '__all__'
