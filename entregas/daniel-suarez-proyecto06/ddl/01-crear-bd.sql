-- =========================================================================
-- Proyecto N°6 — Control de parqueadero
-- Script DDL (Data Definition Language)
-- Motor: MySQL 8.0+ / MariaDB 10.5+
-- Autor: Daniel Suárez
-- =========================================================================
--
-- Este script crea la base de datos desde cero. Si ya existe, la elimina
-- para garantizar un estado limpio. Ejecutarlo SOLO en entorno de desarrollo.
-- =========================================================================

DROP DATABASE IF EXISTS parqueadero;
CREATE DATABASE parqueadero
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE parqueadero;

-- =========================================================================
-- 1) tipo_vehiculo — Catálogo de tipos (Carro, Moto, Bicicleta, Camioneta…)
-- =========================================================================
CREATE TABLE tipo_vehiculo (
    id_tipo      INT AUTO_INCREMENT,
    nombre       VARCHAR(30)  NOT NULL,
    descripcion  VARCHAR(150),
    CONSTRAINT pk_tipo_vehiculo PRIMARY KEY (id_tipo),
    CONSTRAINT uk_tipo_vehiculo_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 2) tarifa — Precio por hora para cada tipo de vehículo, con histórico
-- =========================================================================
CREATE TABLE tarifa (
    id_tarifa      INT AUTO_INCREMENT,
    id_tipo        INT          NOT NULL,
    valor_hora     DECIMAL(10,2) NOT NULL,
    vigente_desde  DATE         NOT NULL,
    activa         TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT pk_tarifa PRIMARY KEY (id_tarifa),
    CONSTRAINT fk_tarifa_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_tarifa_valor CHECK (valor_hora >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 3) espacio — Los 100 espacios numerados del parqueadero
-- =========================================================================
CREATE TABLE espacio (
    id_espacio          INT AUTO_INCREMENT,
    numero              INT          NOT NULL,
    estado              ENUM('LIBRE','OCUPADO','RESERVADO') NOT NULL DEFAULT 'LIBRE',
    id_tipo_permitido   INT,
    CONSTRAINT pk_espacio PRIMARY KEY (id_espacio),
    CONSTRAINT uk_espacio_numero UNIQUE (numero),
    CONSTRAINT fk_espacio_tipo FOREIGN KEY (id_tipo_permitido)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT ck_espacio_numero CHECK (numero BETWEEN 1 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 4) vehiculo — Identificado por placa. NO distinguimos cliente ocasional.
-- =========================================================================
CREATE TABLE vehiculo (
    placa     VARCHAR(10) NOT NULL,
    id_tipo   INT         NOT NULL,
    color     VARCHAR(30),
    marca     VARCHAR(30),
    CONSTRAINT pk_vehiculo PRIMARY KEY (placa),
    CONSTRAINT fk_vehiculo_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 5) cliente — Persona dueña de mensualidad
-- =========================================================================
CREATE TABLE cliente (
    id_cliente        INT AUTO_INCREMENT,
    documento         VARCHAR(20) NOT NULL,
    nombre_completo   VARCHAR(100) NOT NULL,
    telefono          VARCHAR(20),
    email             VARCHAR(120),
    CONSTRAINT pk_cliente PRIMARY KEY (id_cliente),
    CONSTRAINT uk_cliente_documento UNIQUE (documento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 6) mensualidad — Contrato mensual: cliente + espacio + período
-- =========================================================================
CREATE TABLE mensualidad (
    id_mensualidad  INT AUTO_INCREMENT,
    id_cliente      INT          NOT NULL,
    id_espacio      INT          NOT NULL,
    fecha_inicio    DATE         NOT NULL,
    fecha_fin       DATE         NOT NULL,
    monto_pagado    DECIMAL(10,2) NOT NULL,
    estado          ENUM('ACTIVA','VENCIDA','CANCELADA') NOT NULL DEFAULT 'ACTIVA',
    CONSTRAINT pk_mensualidad PRIMARY KEY (id_mensualidad),
    CONSTRAINT fk_mensualidad_cliente FOREIGN KEY (id_cliente)
        REFERENCES cliente (id_cliente)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_mensualidad_espacio FOREIGN KEY (id_espacio)
        REFERENCES espacio (id_espacio)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_mensualidad_fechas CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT ck_mensualidad_monto  CHECK (monto_pagado >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 7) mensualidad_vehiculo — Tabla puente N–M
-- =========================================================================
CREATE TABLE mensualidad_vehiculo (
    id_mensualidad  INT         NOT NULL,
    placa           VARCHAR(10) NOT NULL,
    CONSTRAINT pk_mensualidad_vehiculo PRIMARY KEY (id_mensualidad, placa),
    CONSTRAINT fk_mv_mensualidad FOREIGN KEY (id_mensualidad)
        REFERENCES mensualidad (id_mensualidad)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_mv_vehiculo FOREIGN KEY (placa)
        REFERENCES vehiculo (placa)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 8) ingreso — Entrada/salida de un vehículo
-- =========================================================================
CREATE TABLE ingreso (
    id_ingreso          INT AUTO_INCREMENT,
    placa               VARCHAR(10)  NOT NULL,
    id_espacio          INT          NOT NULL,
    fecha_hora_entrada  DATETIME     NOT NULL,
    fecha_hora_salida   DATETIME,
    es_mensual          TINYINT(1)   NOT NULL DEFAULT 0,
    id_mensualidad      INT,
    id_tarifa           INT,
    monto_cobrado       DECIMAL(10,2),
    CONSTRAINT pk_ingreso PRIMARY KEY (id_ingreso),
    CONSTRAINT fk_ingreso_vehiculo FOREIGN KEY (placa)
        REFERENCES vehiculo (placa)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ingreso_espacio FOREIGN KEY (id_espacio)
        REFERENCES espacio (id_espacio)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- Nota: estas FK usan RESTRICT en AMBAS acciones (DELETE y UPDATE)
    -- porque sus columnas aparecen en el CHECK ck_ingreso_tipo_cobro.
    -- MySQL 8 prohíbe que una columna referenciada por un CHECK pueda
    -- ser modificada automáticamente por una acción referencial
    -- (CASCADE, SET NULL y SET DEFAULT cuentan como modificación;
    --  RESTRICT y NO ACTION no, porque solo bloquean).
    -- En la práctica perdemos poco: las PK son AUTO_INCREMENT y nunca
    -- se actualizan a mano. Y nunca queremos perder el vínculo
    -- histórico de un ingreso: para "borrar" se usa borrado lógico
    -- (cambiar estado/activa), no DELETE físico.
    CONSTRAINT fk_ingreso_mensualidad FOREIGN KEY (id_mensualidad)
        REFERENCES mensualidad (id_mensualidad)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_ingreso_tarifa FOREIGN KEY (id_tarifa)
        REFERENCES tarifa (id_tarifa)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_ingreso_fechas CHECK (
        fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_entrada
    ),
    CONSTRAINT ck_ingreso_monto CHECK (
        monto_cobrado IS NULL OR monto_cobrado >= 0
    ),
    CONSTRAINT ck_ingreso_tipo_cobro CHECK (
        -- Si es mensual: NO debe traer tarifa por hora.
        -- Si es ocasional: SÍ debe traer tarifa por hora.
        (es_mensual = 1 AND id_tarifa IS NULL AND id_mensualidad IS NOT NULL)
        OR
        (es_mensual = 0 AND id_mensualidad IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índice útil para la consulta "¿qué vehículos están dentro?" (RF7)
CREATE INDEX idx_ingreso_dentro
    ON ingreso (fecha_hora_salida, fecha_hora_entrada);
