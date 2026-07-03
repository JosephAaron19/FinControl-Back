from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class Rol(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre

class TipoIncidencia(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    requiere_evidencia = models.BooleanField(default=False, null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    orden = models.IntegerField(default=0, null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'tipos_incidencia'
        verbose_name = 'Tipo de Incidencia'
        verbose_name_plural = 'Tipos de Incidencia'

    def __str__(self):
        return self.nombre
class SedeCentral(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='sedes_centrales/', null=True, blank=True)
    imagen_url = models.TextField(null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sedes_centrales'
        verbose_name = 'Sede Central'
        verbose_name_plural = 'Sedes Centrales'

    def __str__(self):
        return self.nombre

class Sede(models.Model):
    id = models.AutoField(primary_key=True)
    sede_central = models.ForeignKey(SedeCentral, on_delete=models.SET_NULL, null=True, blank=True, related_name='sedes')
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(null=True, blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    radio_metros = models.IntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)
    referencia = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='creado_por', related_name='sedes_creadas', null=True, blank=True)
    actualizado_por = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='actualizado_por', related_name='sedes_actualizadas', null=True, blank=True)
    class Meta:
        db_table = 'sedes'
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'

    def __str__(self):
        return self.nombre

class JornadaConfiguracion(models.Model):
    sede = models.ForeignKey('Sede', models.DO_NOTHING)
    dia_semana = models.CharField(max_length=20)
    # Rango para entrada puntual
    hora_inicio_marcacion = models.TimeField()
    hora_fin_marcacion = models.TimeField()
    # Rango para salida permitida
    hora_inicio_salida = models.TimeField(null=True, blank=True)
    hora_fin_salida = models.TimeField(null=True, blank=True)
    
    activo = models.BooleanField(default=True, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='creado_por', blank=True, null=True)
    actualizado_por = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='actualizado_por', related_name='jornadaconfiguracion_actualizado_por_set', blank=True, null=True)
    creado_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    actualizado_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'jornada_configuracion'
        unique_together = (('sede', 'dia_semana'),)
        verbose_name = 'Configuración de Jornada'
        verbose_name_plural = 'Configuraciones de Jornada'


class UsuarioManager(BaseUserManager):
    def create_user(self, dni, password=None, **extra_fields):
        if not dni:
            raise ValueError('El DNI es obligatorio')
        user = self.model(dni=dni, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, dni, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(dni, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    dni = models.CharField(max_length=15, unique=True)
    nombre_completo = models.CharField(max_length=150)
    cargo = models.CharField(max_length=100, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, related_name='usuarios')
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, related_name='usuarios')
    activo = models.BooleanField(default=True, null=True, blank=True)
    debe_cambiar_password = models.BooleanField(default=False, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_creados', db_column='creado_por')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)
    fcm = models.TextField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'dni'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_completo} ({self.dni})"

class UsuarioSede(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sedes_asignadas')
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='usuarios_asignados')
    puede_visualizar = models.BooleanField(default=True)
    puede_gestionar = models.BooleanField(default=True)
    es_principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario_sedes'
        unique_together = ('usuario', 'sede')
        verbose_name = 'Usuario por Sede'
        verbose_name_plural = 'Usuarios por Sede'

class Asistencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(auto_now_add=True)
    hora_entrada = models.DateTimeField(null=True, blank=True)
    hora_salida = models.DateTimeField(null=True, blank=True)
    hora_inicio_break = models.DateTimeField(null=True, blank=True)
    hora_fin_break = models.DateTimeField(null=True, blank=True)
    latitud_entrada = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_entrada = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    latitud_salida = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_salida = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    estado = models.CharField(max_length=50, default='Sin Marcar')
    dispositivo_info = models.TextField(null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    estado_asistencia = models.CharField(max_length=20, default='programada') # 'programada', 'en_proceso', 'completa', 'incompleta', 'ausente'
    estado_puntualidad = models.CharField(max_length=20, default='pendiente') # 'temprano', 'puntual', 'tardanza', 'no_marco_entrada', 'pendiente'
    estado_salida = models.CharField(max_length=20, default='pendiente') # 'puntual', 'tardanza', 'no_marco_salida', 'pendiente'
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistencias'
        unique_together = ('usuario', 'fecha')
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

class Incidencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='incidencias')
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='incidencias_detalle', null=True, blank=True)
    tipo_incidencia = models.CharField(max_length=100)
    tipo_incidencia_0 = models.ForeignKey(TipoIncidencia, on_delete=models.SET_NULL, null=True, blank=True, db_column='tipo_incidencia_id')
    descripcion = models.TextField()
    foto_evidencia_url = models.ImageField(upload_to='incidencias/', db_column='foto_evidencia_url', null=True, blank=True)
    evidencia_url = models.TextField(null=True, blank=True)
    evidencia_nombre_archivo = models.CharField(max_length=255, null=True, blank=True)
    evidencia_mime_type = models.CharField(max_length=100, null=True, blank=True)
    fecha_hora_reporte = models.DateTimeField(auto_now_add=True)
    estado_revision = models.CharField(max_length=50, default='Pendiente')
    comentario_revision = models.TextField(null=True, blank=True)
    revisado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, related_name='incidencias_revisadas', null=True, blank=True, db_column='revisado_por')
    revisado_at = models.DateTimeField(null=True, blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    dispositivo_info = models.TextField(null=True, blank=True)
    ip_origen = models.CharField(max_length=100, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    origen = models.CharField(max_length=50, null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'incidencias'
        verbose_name = 'Incidencia'
        verbose_name_plural = 'Incidencias'

class AsistenciaEvento(models.Model):
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='eventos')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='eventos_detalle', null=True, blank=True)
    tipo_evento = models.CharField(max_length=50)  # 'ENTRADA', 'INICIO_BREAK', 'FIN_BREAK', 'SALIDA'
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    dispositivo_info = models.TextField(null=True, blank=True)
    sede_id = models.IntegerField(null=True, blank=True)
    es_fuera_de_zona = models.BooleanField(default=False)
    distancia_sede_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ip_origen = models.CharField(max_length=100, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'asistencia_eventos'
        verbose_name = 'Evento de Asistencia'
        verbose_name_plural = 'Eventos de Asistencia'

class ConfiguracionTracking(models.Model):
    intervalo_segundos = models.IntegerField(default=60)
    tracking_activo = models.BooleanField(default=True)
    enviar_en_background = models.BooleanField(default=True)
    precision_minima_metros = models.DecimalField(max_digits=10, decimal_places=2, default=50.00)
    descripcion = models.TextField(null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configuracion_tracking'
        verbose_name = 'Configuración de Tracking'
        verbose_name_plural = 'Configuraciones de Tracking'

class UbicacionPunto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='puntos_gps')
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='puntos_gps', null=True, blank=True)
    historial_jornada_id = models.IntegerField(null=True, blank=True) # Para compatibilidad con tu BD
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    precision_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    velocidad_mps = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    altitud_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    direccion_grados = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bateria_porcentaje = models.IntegerField(null=True, blank=True)
    es_fuera_de_zona = models.BooleanField(default=False)
    distancia_sede_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    origen = models.CharField(max_length=50, default='App Móvil')
    estado_envio = models.CharField(max_length=50, null=True, blank=True)
    dispositivo_info = models.TextField(null=True, blank=True)
    ip_origen = models.CharField(max_length=100, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    fecha = models.DateField(auto_now_add=True, null=True, blank=True)
    hora = models.TimeField(auto_now_add=True, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    creado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ubicacion_puntos'
        verbose_name = 'Punto de Ubicación'
        verbose_name_plural = 'Puntos de Ubicación'
        ordering = ['fecha_hora']

class HistorialJornada(models.Model):
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='historiales', null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historiales_jornada')
    sede_id = models.IntegerField(null=True, blank=True)
    fecha = models.DateField()
    hora_entrada = models.DateTimeField(null=True, blank=True)
    hora_inicio_break = models.DateTimeField(null=True, blank=True)
    hora_fin_break = models.DateTimeField(null=True, blank=True)
    hora_salida = models.DateTimeField(null=True, blank=True)
    latitud_entrada = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_entrada = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    latitud_inicio_break = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_inicio_break = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    latitud_fin_break = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_fin_break = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    latitud_salida = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_salida = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    entrada_fuera_de_zona = models.BooleanField(default=False)
    inicio_break_fuera_de_zona = models.BooleanField(default=False)
    fin_break_fuera_de_zona = models.BooleanField(default=False)
    salida_fuera_de_zona = models.BooleanField(default=False)
    distancia_entrada_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distancia_inicio_break_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distancia_fin_break_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    distancia_salida_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_tiempo_break = models.DurationField(null=True, blank=True)
    total_horas_trabajadas = models.DurationField(null=True, blank=True)
    cantidad_marcaciones = models.IntegerField(default=0)
    dispositivo_entrada = models.TextField(null=True, blank=True)
    dispositivo_inicio_break = models.TextField(null=True, blank=True)
    dispositivo_fin_break = models.TextField(null=True, blank=True)
    dispositivo_salida = models.TextField(null=True, blank=True)
    estado_jornada = models.CharField(max_length=50, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    cerrado = models.BooleanField(default=False)
    cerrado_at = models.DateTimeField(null=True, blank=True)
    estado_asistencia = models.CharField(max_length=20, default='programada')
    estado_puntualidad = models.CharField(max_length=20, default='pendiente')
    estado_salida = models.CharField(max_length=20, default='pendiente')
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'historial_jornadas'
        unique_together = ('usuario', 'fecha')
        verbose_name = 'Historial de Jornada'
        verbose_name_plural = 'Historial de Jornadas'

class JornadaActividad(models.Model):
    ESTADO_CHOICES = (
        ('en_proceso', 'En Proceso'),
        ('finalizada', 'Finalizada'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='actividades_jornada')
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='actividades_jornada')
    historial_jornada = models.ForeignKey(HistorialJornada, on_delete=models.CASCADE, related_name='actividades_jornada')
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='actividades_jornada')
    
    titulo = models.CharField(max_length=150)
    tipo_actividad = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    
    cliente_nombre = models.CharField(max_length=150, null=True, blank=True)
    cliente_documento = models.CharField(max_length=30, null=True, blank=True)
    cliente_telefono = models.CharField(max_length=30, null=True, blank=True)
    direccion_actividad = models.TextField(null=True, blank=True)
    
    latitud_inicio = models.DecimalField(max_digits=10, decimal_places=8)
    longitud_inicio = models.DecimalField(max_digits=11, decimal_places=8)
    evidencia_inicio_url = models.ImageField(upload_to='actividades/', null=True, blank=True)
    dispositivo_inicio = models.TextField(null=True, blank=True)
    hora_inicio_actividad = models.DateTimeField(auto_now_add=True)
    
    latitud_fin = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_fin = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    evidencia_fin_url = models.ImageField(upload_to='actividades/', null=True, blank=True)
    dispositivo_fin = models.TextField(null=True, blank=True)
    hora_fin_actividad = models.DateTimeField(null=True, blank=True)
    
    resultado_actividad = models.CharField(max_length=100, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    
    estado_actividad = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='en_proceso')
    
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'jornada_actividades'
        verbose_name = 'Actividad de Jornada'
        verbose_name_plural = 'Actividades de Jornada'


class Horario(models.Model):
    id = models.AutoField(primary_key=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='horarios')
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='horarios_creados', db_column='creado_por')
    actualizado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='horarios_actualizados', db_column='actualizado_por')
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    tipo_configuracion = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'horarios'
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'

    def __str__(self):
        return f"{self.nombre} - Sede: {self.sede.nombre}"


class HorarioDetalle(models.Model):
    id = models.AutoField(primary_key=True)
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, related_name='detalles')
    dia_semana = models.CharField(max_length=50) # 'lunes', 'martes', etc.
    hora_inicio_entrada = models.TimeField()
    hora_fin_entrada = models.TimeField()
    hora_inicio_salida = models.TimeField()
    hora_fin_salida = models.TimeField()
    activo = models.BooleanField(default=True, null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'horario_detalles'
        verbose_name = 'Detalle de Horario'
        verbose_name_plural = 'Detalles de Horarios'

    def __str__(self):
        return f"{self.horario.nombre} - Dia: {self.dia_semana} ({self.hora_inicio_entrada} - {self.hora_fin_salida})"


class UsuarioHorario(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='horarios_usuario')
    horario = models.ForeignKey(Horario, on_delete=models.CASCADE, related_name='usuarios_horario')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios_horario_sede')
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    es_principal = models.BooleanField(default=True, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuario_horarios_creados', db_column='creado_por')
    actualizado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuario_horarios_actualizados', db_column='actualizado_por')
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'usuario_horarios'
        verbose_name = 'Horario de Usuario'
        verbose_name_plural = 'Horarios de Usuarios'

    def __str__(self):
        return f"{self.usuario.nombre_completo} -> {self.horario.nombre}"


class IntercambioHorario(models.Model):
    id = models.AutoField(primary_key=True)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercambios')
    usuario_solicitante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='intercambios_solicitados', db_column='usuario_solicitante_id')
    usuario_reemplazo = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='intercambios_reemplazos', db_column='usuario_reemplazo_id')
    fecha_intercambio = models.DateField()
    horario_solicitante_original = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercambios_solicitante_orig', db_column='horario_solicitante_original_id')
    horario_reemplazo_original = models.ForeignKey(Horario, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercambios_reemplazo_orig', db_column='horario_reemplazo_original_id')
    estado = models.CharField(max_length=50, default='aprobado', null=True, blank=True) # 'pendiente', 'aprobado', 'rechazado'
    motivo = models.TextField(null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercambios_registrados', db_column='registrado_por')
    aprobado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercambios_aprobados', db_column='aprobado_por')
    aprobado_at = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True, null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = 'intercambios_horario'
        verbose_name = 'Intercambio de Horario'
        verbose_name_plural = 'Intercambios de Horarios'

    def __str__(self):
        return f"{self.usuario_solicitante.nombre_completo} <-> {self.usuario_reemplazo.nombre_completo} ({self.fecha_intercambio})"

class NotificacionPush(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones_push')
    fcm_token = models.TextField()
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=100, null=True, blank=True)
    payload = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=50, default='PENDIENTE')
    error = models.TextField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notificaciones_push'
        verbose_name = 'Notificación Push'
        verbose_name_plural = 'Notificaciones Push'

    def __str__(self):
        return f"Notificación a {self.usuario.nombre_completo} - {self.estado}"

