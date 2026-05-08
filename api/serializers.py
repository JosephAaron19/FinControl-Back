from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto, Rol, TipoIncidencia

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
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
                if not user.rol or user.rol.nombre.lower() != 'operador':
                    raise serializers.ValidationError({"detail": "Acceso denegado. Solo los operadores pueden usar la app móvil."})
            except Usuario.DoesNotExist:
                raise serializers.ValidationError({"detail": "Usuario no encontrado."})
                
        return data
