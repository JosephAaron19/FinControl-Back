from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Sede, Usuario, Asistencia, Incidencia, AsistenciaEvento, ConfiguracionTracking, UbicacionPunto

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

class UsuarioSerializer(serializers.ModelSerializer):
    sede = SedeSerializer(read_only=True)
    class Meta:
        model = Usuario
        fields = ('id', 'dni', 'nombre_completo', 'cargo', 'sede', 'is_active')

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

    def validate(self, attrs):
        # Mapear 'dni' a 'username' si viene en la petición
        if 'dni' in attrs and not attrs.get('username'):
            attrs['username'] = attrs['dni']
        return super().validate(attrs)
