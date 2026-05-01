from rest_framework import serializers
from .models import Sede, Usuario, Asistencia, Incidencia

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
    class Meta:
        model = Asistencia
        fields = '__all__'

class IncidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incidencia
        fields = '__all__'
