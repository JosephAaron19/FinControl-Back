# Guía de Implementación: Backend FinaTrack con Django

Esta guía detalla cómo construir el backend para FinaTrack utilizando Django y Django Rest Framework (DRF), integrándolo con el esquema de base de datos PostgreSQL `finc`.

## 1. Requisitos Previos
- Python 3.9+
- PostgreSQL instalado y corriendo.
- Esquema `finc` creado (usando el archivo `database_schema.sql`).

## 2. Configuración del Proyecto

```bash
# Crear entorno virtual
python -m venv venv
# Activar (Windows)
.\venv\Scripts\activate

# Instalar dependencias
pip install django djangorestframework psycopg2-binary django-cors-headers Pillow
```

## 3. Configuración de Base de Datos (settings.py)

Debes configurar Django para apuntar a tu esquema `finc`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tu_base_de_datos',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=finc,public'
        }
    }
}
```

## 4. Definición de Modelos (models.py)

Para que Django reconozca tus tablas con los nombres específicos (`usu_id`, `sed_latitud`, etc.), usa la opción `db_table` en el Meta de cada clase.

### Ejemplo: Modelo Sede
```python
class Sede(models.Model):
    sed_id = models.AutoField(primary_key=True)
    sed_codigo = models.CharField(max_length=30, unique=True)
    sed_nombre = models.CharField(max_length=120)
    sed_latitud = models.DecimalField(max_digits=10, decimal_places=8)
    sed_longitud = models.DecimalField(max_digits=11, decimal_places=8)
    sed_radio_metros = models.IntegerField(default=100)

    class Meta:
        db_table = 'finc"."sedes'  # Mapeo exacto al esquema
```

## 5. Panel Administrativo (admin.py)

Django Admin te permitirá gestionar todo el sistema de forma visual.

```python
from django.contrib import admin
from .models import Asistencia, Usuario, Sede, Incidencia

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('usu_id', 'asi_fecha', 'asi_estado', 'asi_hora_entrada')
    list_filter = ('asi_fecha', 'asi_estado')
    search_fields = ('usu_id__usu_dni', 'usu_id__usu_nombre_completo')
```

## 6. Endpoints Clave para la App Móvil (API)

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/auth/login/` | Autentica al usuario y devuelve el token, su sede y horario. |
| `POST` | `/api/attendance/event/` | Registra ENTRADA, BREAK o SALIDA con GPS y foto. |
| `GET` | `/api/attendance/history/` | Devuelve la lista de asistencias filtradas por el usuario actual. |
| `POST` | `/api/incidents/create/` | Registra un nuevo reporte de incidencia. |

## 7. Lógica de Marcado (Views)

En la vista de marcado, el backend debe:
1. Validar la distancia entre las coordenadas enviadas por el móvil y las de la sede asignada.
2. Si la distancia > `sed_radio_metros`, marcar el evento como `FUERA_DE_ZONA` o `OBSERVADO`.
3. Guardar la hora del servidor (no confiar en la hora del celular del usuario).

## 8. Siguientes Pasos
1. Ejecutar `python manage.py inspectdb > models.py` si quieres generar los modelos automáticamente desde la BD actual.
2. Crear un `SuperUser` para acceder al panel admin: `python manage.py createsuperuser`.
