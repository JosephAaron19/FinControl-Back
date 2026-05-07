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

# Crear un usuario no-root para mayor seguridad (opcional pero recomendado)
RUN adduser --disabled-password --no-create-home djangouser
USER djangouser

# Exponer el puerto que usará Django/Gunicorn
EXPOSE 8000

# Ejecutar Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "fincontrol_backend.wsgi:application"]
