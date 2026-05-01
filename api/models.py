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
        db_table = '"FinC"."sedes"'
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
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, related_name='usuarios')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    creado_at = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'dni'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = '"FinC"."usuarios"'
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
    creado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"FinC"."asistencias"'
        unique_together = ('usuario', 'fecha')
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

class Incidencia(models.Model):
    asistencia = models.ForeignKey(Asistencia, on_delete=models.CASCADE, null=True, related_name='incidencias')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='incidencias')
    tipo_incidencia = models.CharField(max_length=100)
    descripcion = models.TextField()
    foto_evidencia = models.ImageField(upload_to='incidencias/', null=True, blank=True)
    fecha_hora_reporte = models.DateTimeField(auto_now_add=True)
    estado_revision = models.CharField(max_length=50, default='Pendiente')

    class Meta:
        db_table = '"FinC"."incidencias"'
        verbose_name = 'Incidencia'
        verbose_name_plural = 'Incidencias'
