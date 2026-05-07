from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class Sede(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(null=True, blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    radio_metros = models.IntegerField(default=100)
    creado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finc"."sedes'
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'

    def __str__(self):
        return self.nombre

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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'dni'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'finc"."usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_completo} ({self.dni})"

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
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finc"."asistencias'
        unique_together = ('usuario', 'fecha')
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

class Incidencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='incidencias')
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='incidencias_detalle', null=True, blank=True)
    tipo_incidencia = models.CharField(max_length=100)
    descripcion = models.TextField()
    foto_evidencia_url = models.ImageField(upload_to='incidencias/', db_column='foto_evidencia_url', null=True, blank=True)
    fecha_hora_reporte = models.DateTimeField(auto_now_add=True)
    estado_revision = models.CharField(max_length=50, default='Pendiente')
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    dispositivo_info = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'finc"."incidencias'
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
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finc"."asistencia_eventos'
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
        db_table = 'finc"."configuracion_tracking'
        verbose_name = 'Configuración de Tracking'
        verbose_name_plural = 'Configuraciones de Tracking'

class UbicacionPunto(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='puntos_gps')
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, related_name='puntos_gps', null=True, blank=True)
    historial_jornada_id = models.IntegerField(null=True, blank=True) # Para compatibilidad con tu BD
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    precision_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bateria_porcentaje = models.IntegerField(null=True, blank=True)
    es_fuera_de_zona = models.BooleanField(default=False)
    distancia_sede_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    origen = models.CharField(max_length=50, default='App Móvil')
    dispositivo_info = models.TextField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    creado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finc"."ubicacion_puntos'
        verbose_name = 'Punto de Ubicación'
        verbose_name_plural = 'Puntos de Ubicación'

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
    cantidad_marcaciones = models.IntegerField(default=0)
    dispositivo_entrada = models.TextField(null=True, blank=True)
    dispositivo_inicio_break = models.TextField(null=True, blank=True)
    dispositivo_fin_break = models.TextField(null=True, blank=True)
    dispositivo_salida = models.TextField(null=True, blank=True)
    estado_jornada = models.CharField(max_length=50, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    cerrado = models.BooleanField(default=False)
    cerrado_at = models.DateTimeField(null=True, blank=True)
    creado_at = models.DateTimeField(auto_now_add=True)
    actualizado_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finc"."historial_jornadas'
        verbose_name = 'Historial de Jornada'
        verbose_name_plural = 'Historial de Jornadas'
