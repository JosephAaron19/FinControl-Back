# Usar la imagen oficial de Python 3.10 slim por ser ligera
FROM python:3.10-slim

# Evitar que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE 1
# Evitar que Python haga buffer de stdout y stderr (mejor para logs)
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL (psycopg2) y otras herramientas
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos
COPY requirements.txt /app/

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto al contenedor
COPY . /app/

# Crear directorios media y staticfiles con permisos adecuados
RUN mkdir -p /app/media /app/staticfiles && chmod -R 775 /app/media /app/staticfiles

# Crear grupo y usuario djangouser con UID/GID 1000 explícitos para mapear con el host
RUN groupadd -g 1000 djangouser && \
    useradd -u 1000 -g djangouser -d /app -s /sbin/nologin djangouser

# Asegurar que djangouser sea dueño del directorio de la aplicación
RUN chown -R djangouser:djangouser /app

USER djangouser

# Exponer el puerto que usará Django/Daphne
EXPOSE 8000

# Ejecutar Daphne (soporta WebSockets/ASGI)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "fincontrol_backend.asgi:application"]
