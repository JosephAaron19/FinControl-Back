from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia, JornadaConfiguracion, HistorialJornada, JornadaActividad

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
    class Meta:
        model = Usuario
        fields = ('id', 'dni', 'nombre_completo', 'cargo', 'telefono', 'email', 'sede', 'rol', 'sede_info', 'rol_info', 'is_active', 'activo', 'debe_cambiar_password', 'observacion')

class UsuarioCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = ('dni', 'nombre_completo', 'password', 'cargo', 'telefono', 'email', 'sede', 'rol', 'activo', 'is_active', 'debe_cambiar_password', 'observacion')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class AsistenciaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.ReadOnlyField(source='usuario.sede.nombre')
    
    class Meta:
        model = Asistencia
        fields = '__all__'

class IncidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incidencia
        fields = '__all__'
        read_only_fields = ('usuario', 'asistencia', 'fecha_hora_reporte', 'estado_revision')

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
            
        origen = attrs.get('origen')
        
        data = super().validate(attrs)
        
        # Validar el rol si el origen es 'movil'
        if origen == 'movil':
            # Inner join con roles
            from .models import Usuario
            try:
                user = Usuario.objects.select_related('rol').get(dni=attrs['username'])
                if not user.rol or user.rol.nombre.lower() not in ['operador', 'asesor']:
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
    estado_puntualidad = serializers.SerializerMethodField()

    class Meta:
        model = HistorialJornada
        fields = [
            'id', 'operador', 'sede', 'fecha', 'hora_entrada', 'hora_inicio_break', 
            'hora_fin_break', 'hora_salida', 'total_tiempo_break', 'total_horas_trabajadas', 
            'estado_puntualidad', 'estado_jornada', 'cerrado', 'cerrado_at', 
            'total_incidencias', 'total_puntos_gps'
        ]

    def get_sede(self, obj):
        if obj.sede_id:
            sede = Sede.objects.filter(id=obj.sede_id).first()
            return sede.nombre if sede else f"Sede {obj.sede_id}"
        return "-"

    def get_estado_puntualidad(self, obj):
        if obj.asistencia:
            return obj.asistencia.estado
        return "-"

class HistorialJornadaDetailSerializer(serializers.ModelSerializer):
    operador = serializers.ReadOnlyField(source='usuario.nombre_completo')
    sede = serializers.SerializerMethodField()
    eventos = AsistenciaEventoSerializer(source='asistencia.eventos', many=True, read_only=True)
    incidencias = IncidenciaSerializer(source='asistencia.incidencias_detalle', many=True, read_only=True)
    puntos_gps = UbicacionPuntoSerializer(source='asistencia.puntos_gps', many=True, read_only=True)
    actividades_campo = JornadaActividadSerializer(source='actividades_jornada', many=True, read_only=True)
    rol_codigo = serializers.ReadOnlyField(source='usuario.rol.codigo')
    rol_nombre = serializers.ReadOnlyField(source='usuario.rol.nombre')

    class Meta:
        model = HistorialJornada
        fields = [
            'id', 'operador', 'sede', 'fecha', 'hora_entrada', 'hora_inicio_break', 
            'hora_fin_break', 'hora_salida', 'total_tiempo_break', 'total_horas_trabajadas', 
            'estado_jornada', 'cerrado', 'cerrado_at', 'observacion',
            'eventos', 'incidencias', 'puntos_gps', 'actividades_campo',
            'rol_codigo', 'rol_nombre'
        ]

    def get_sede(self, obj):
        if obj.sede_id:
            sede = Sede.objects.filter(id=obj.sede_id).first()
            return sede.nombre if sede else f"Sede {obj.sede_id}"
        return "-"
