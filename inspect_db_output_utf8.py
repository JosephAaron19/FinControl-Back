# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AsistenciaEventos(models.Model):
    asistencia = models.ForeignKey('Asistencias', models.DO_NOTHING)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    sede = models.ForeignKey('Sedes', models.DO_NOTHING, blank=True, null=True)
    tipo_evento = models.CharField(max_length=50)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    es_fuera_de_zona = models.BooleanField(blank=True, null=True)
    distancia_sede_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    dispositivo_info = models.TextField(blank=True, null=True)
    ip_origen = models.CharField(max_length=100, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    fecha_hora = models.DateTimeField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'asistencia_eventos'


class Asistencias(models.Model):
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    fecha = models.DateField()
    hora_entrada = models.DateTimeField(blank=True, null=True)
    hora_inicio_break = models.DateTimeField(blank=True, null=True)
    hora_fin_break = models.DateTimeField(blank=True, null=True)
    hora_salida = models.DateTimeField(blank=True, null=True)
    latitud_entrada = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_entrada = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    latitud_salida = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_salida = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)
    dispositivo_info = models.TextField(blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'asistencias'
        unique_together = (('usuario', 'fecha'),)


class ConfiguracionTracking(models.Model):
    intervalo_segundos = models.IntegerField()
    tracking_activo = models.BooleanField(blank=True, null=True)
    enviar_en_background = models.BooleanField(blank=True, null=True)
    precision_minima_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_tracking'


class HistorialJornadas(models.Model):
    asistencia = models.OneToOneField(Asistencias, models.DO_NOTHING)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    sede = models.ForeignKey('Sedes', models.DO_NOTHING, blank=True, null=True)
    fecha = models.DateField()
    hora_entrada = models.DateTimeField(blank=True, null=True)
    hora_inicio_break = models.DateTimeField(blank=True, null=True)
    hora_fin_break = models.DateTimeField(blank=True, null=True)
    hora_salida = models.DateTimeField(blank=True, null=True)
    latitud_entrada = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_entrada = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    latitud_inicio_break = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_inicio_break = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    latitud_fin_break = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_fin_break = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    latitud_salida = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_salida = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    entrada_fuera_de_zona = models.BooleanField(blank=True, null=True)
    inicio_break_fuera_de_zona = models.BooleanField(blank=True, null=True)
    fin_break_fuera_de_zona = models.BooleanField(blank=True, null=True)
    salida_fuera_de_zona = models.BooleanField(blank=True, null=True)
    distancia_entrada_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    distancia_inicio_break_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    distancia_fin_break_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    distancia_salida_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_tiempo_break = models.DurationField(blank=True, null=True)
    total_horas_trabajadas = models.DurationField(blank=True, null=True)
    cantidad_marcaciones = models.IntegerField(blank=True, null=True)
    dispositivo_entrada = models.TextField(blank=True, null=True)
    dispositivo_inicio_break = models.TextField(blank=True, null=True)
    dispositivo_fin_break = models.TextField(blank=True, null=True)
    dispositivo_salida = models.TextField(blank=True, null=True)
    estado_jornada = models.CharField(max_length=50, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    cerrado = models.BooleanField(blank=True, null=True)
    cerrado_at = models.DateTimeField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'historial_jornadas'
        unique_together = (('usuario', 'fecha'),)


class Incidencias(models.Model):
    asistencia = models.ForeignKey(Asistencias, models.DO_NOTHING, blank=True, null=True)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    historial_jornada = models.ForeignKey(HistorialJornadas, models.DO_NOTHING, blank=True, null=True)
    tipo_incidencia = models.CharField(max_length=100)
    descripcion = models.TextField()
    foto_evidencia_url = models.TextField(blank=True, null=True)
    estado_revision = models.CharField(max_length=50, blank=True, null=True)
    comentario_revision = models.TextField(blank=True, null=True)
    revisado_por = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='revisado_por', related_name='incidencias_revisado_por_set', blank=True, null=True)
    revisado_at = models.DateTimeField(blank=True, null=True)
    fecha_hora_reporte = models.DateTimeField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    tipo_incidencia_0 = models.ForeignKey('TiposIncidencia', models.DO_NOTHING, db_column='tipo_incidencia_id', blank=True, null=True)  # Field renamed because of name conflict.
    evidencia_url = models.TextField(blank=True, null=True)
    evidencia_nombre_archivo = models.CharField(max_length=255, blank=True, null=True)
    evidencia_mime_type = models.CharField(max_length=100, blank=True, null=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    dispositivo_info = models.TextField(blank=True, null=True)
    ip_origen = models.CharField(max_length=100, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    origen = models.CharField(max_length=50, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'incidencias'


class Roles(models.Model):
    codigo = models.CharField(unique=True, max_length=50)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class Sedes(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True, null=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    radio_metros = models.IntegerField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sedes'


class TiposIncidencia(models.Model):
    codigo = models.CharField(unique=True, max_length=50)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    requiere_evidencia = models.BooleanField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    orden = models.IntegerField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tipos_incidencia'


class UbicacionPuntos(models.Model):
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    asistencia = models.ForeignKey(Asistencias, models.DO_NOTHING, blank=True, null=True)
    historial_jornada = models.ForeignKey(HistorialJornadas, models.DO_NOTHING, blank=True, null=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    precision_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    velocidad_mps = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    altitud_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    direccion_grados = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bateria_porcentaje = models.IntegerField(blank=True, null=True)
    es_fuera_de_zona = models.BooleanField(blank=True, null=True)
    distancia_sede_metros = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    origen = models.CharField(max_length=50, blank=True, null=True)
    estado_envio = models.CharField(max_length=50, blank=True, null=True)
    dispositivo_info = models.TextField(blank=True, null=True)
    ip_origen = models.CharField(max_length=100, blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    fecha = models.DateField()
    hora = models.TimeField()
    fecha_hora = models.DateTimeField()
    creado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ubicacion_puntos'


class Usuarios(models.Model):
    dni = models.CharField(unique=True, max_length=15)
    nombre_completo = models.CharField(max_length=150)
    password = models.TextField()
    cargo = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    sede = models.ForeignKey(Sedes, models.DO_NOTHING, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    creado_at = models.DateTimeField(blank=True, null=True)
    actualizado_at = models.DateTimeField(blank=True, null=True)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField(blank=True, null=True)
    is_staff = models.BooleanField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    rol = models.ForeignKey(Roles, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'
