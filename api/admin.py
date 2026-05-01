from django.contrib import admin
from .models import Sede, Usuario, Asistencia, Incidencia

@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'latitud', 'longitud', 'radio_metros')
    search_fields = ('nombre',)

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('dni', 'nombre_completo', 'cargo', 'sede', 'is_active', 'is_staff')
    search_fields = ('dni', 'nombre_completo')
    list_filter = ('is_active', 'is_staff', 'sede')

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha', 'estado', 'hora_entrada', 'hora_salida')
    list_filter = ('fecha', 'estado')
    search_fields = ('usuario__dni', 'usuario__nombre_completo')

@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_incidencia', 'fecha_hora_reporte', 'estado_revision')
    list_filter = ('estado_revision', 'tipo_incidencia')
    search_fields = ('usuario__dni', 'usuario__nombre_completo', 'descripcion')
