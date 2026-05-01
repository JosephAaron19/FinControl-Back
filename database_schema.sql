-- ESQUEMA DE BASE DE DATOS - FINATRACK (PostgreSQL)
-- Generado para el sistema de asistencia georeferenciada

-- 1. CREACIÓN DEL ESQUEMA
CREATE SCHEMA IF NOT EXISTS "FinC";

-- 2. TABLA DE SEDES (GEOCERCAS)
CREATE TABLE "FinC"."sedes" (
    "id" SERIAL PRIMARY KEY,
    "nombre" VARCHAR(100) NOT NULL,
    "direccion" TEXT,
    "latitud" DECIMAL(10, 8) NOT NULL,
    "longitud" DECIMAL(11, 8) NOT NULL,
    "radio_metros" INTEGER DEFAULT 100,
    "creado_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABLA DE USUARIOS (TRABAJADORES)
CREATE TABLE "FinC"."usuarios" (
    "id" SERIAL PRIMARY KEY,
    "dni" VARCHAR(15) UNIQUE NOT NULL,
    "nombre_completo" VARCHAR(150) NOT NULL,
    "password_hash" TEXT NOT NULL,
    "cargo" VARCHAR(100),
    "sede_id" INTEGER REFERENCES "FinC"."sedes"("id") ON DELETE SET NULL,
    "activo" BOOLEAN DEFAULT TRUE,
    "creado_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLA DE ASISTENCIAS (MARCACIONES)
CREATE TABLE "FinC"."asistencias" (
    "id" SERIAL PRIMARY KEY,
    "usuario_id" INTEGER NOT NULL REFERENCES "FinC"."usuarios"("id") ON DELETE CASCADE,
    "fecha" DATE NOT NULL DEFAULT CURRENT_DATE,
    "hora_entrada" TIMESTAMP,
    "hora_salida" TIMESTAMP,
    "hora_inicio_break" TIMESTAMP,
    "hora_fin_break" TIMESTAMP,
    "latitud_entrada" DECIMAL(10, 8),
    "longitud_entrada" DECIMAL(11, 8),
    "latitud_salida" DECIMAL(10, 8),
    "longitud_salida" DECIMAL(11, 8),
    "estado" VARCHAR(50) DEFAULT 'Sin Marcar', -- 'Válido', 'Observado', 'Pendiente'
    "dispositivo_info" TEXT,
    "creado_at" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Un usuario solo debería tener un registro de asistencia por fecha
    UNIQUE("usuario_id", "fecha")
);

-- 5. TABLA DE INCIDENCIAS (REPORTES)
CREATE TABLE "FinC"."incidencias" (
    "id" SERIAL PRIMARY KEY,
    "asistencia_id" INTEGER REFERENCES "FinC"."asistencias"("id") ON DELETE CASCADE,
    "usuario_id" INTEGER NOT NULL REFERENCES "FinC"."usuarios"("id") ON DELETE CASCADE,
    "tipo_incidencia" VARCHAR(100) NOT NULL,
    "descripcion" TEXT NOT NULL,
    "foto_evidencia_url" TEXT,
    "fecha_hora_reporte" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "estado_revision" VARCHAR(50) DEFAULT 'Pendiente' -- 'Pendiente', 'Aprobada', 'Rechazada'
);

-- 6. DATOS DE PRUEBA (OPCIONAL)
INSERT INTO "FinC"."sedes" (nombre, direccion, latitud, longitud, radio_metros)
VALUES ('Sede Central - Finhold', 'Calle Las Orquídeas 456, San Isidro', -12.046374, -77.042793, 100);

INSERT INTO "FinC"."usuarios" (dni, nombre_completo, password_hash, cargo, sede_id)
VALUES ('12345678', 'Juan Pérez', 'hash_password_here', 'Analista de Sistemas', 1);
