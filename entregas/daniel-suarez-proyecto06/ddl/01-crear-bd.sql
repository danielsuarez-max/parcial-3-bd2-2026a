-- =========================================================================
-- Proyecto N°6 — Control de parqueadero
-- Script DDL (Data Definition Language)
-- Motor: MySQL 8.0+ / MariaDB 10.5+
-- Autor: Daniel Suárez
-- =========================================================================
--
-- Este script crea la base de datos desde cero. Si ya existe, la elimina
-- para garantizar un estado limpio. Ejecutarlo SOLO en entorno de desarrollo.
--
-- Convención de nombres: las tablas que representan COLECCIONES van en
-- plural (clientes, espacios, ingresos, mensualidades, tarifas, vehiculos);
-- las tablas catálogo simples y las puente conservan el singular
-- (tipo_vehiculo, mensualidad_vehiculo, espacio_tipo_permitido).
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
-- 2) tarifas — Precio por hora para cada tipo de vehículo, con histórico
-- =========================================================================
CREATE TABLE tarifas (
    id_tarifa      INT AUTO_INCREMENT,
    id_tipo        INT          NOT NULL,
    valor_hora     DECIMAL(10,2) NOT NULL,
    vigente_desde  DATE         NOT NULL,
    activa         TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT pk_tarifas PRIMARY KEY (id_tarifa),
    CONSTRAINT fk_tarifas_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_tarifas_valor CHECK (valor_hora >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 2b) tarifa_mensual — Valor del mes estipulado por tipo de vehículo
--     Catálogo simple (un valor vigente por tipo). El monto de una mensualidad
--     se calcula como la SUMA del valor_mes de los vehículos que cubre, y se
--     guarda en mensualidades.monto_pagado (así el histórico no cambia aunque
--     luego se ajusten estos precios).
-- =========================================================================
CREATE TABLE tarifa_mensual (
    id_tipo   INT           NOT NULL,
    valor_mes DECIMAL(10,2) NOT NULL,
    CONSTRAINT pk_tarifa_mensual PRIMARY KEY (id_tipo),
    CONSTRAINT fk_tarifa_mensual_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_valor_mes_no_negativo CHECK (valor_mes >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 3) espacios — Los 100 espacios numerados del parqueadero
--    Los tipos de vehículo que cada espacio acepta se manejan en la tabla
--    puente espacio_tipo_permitido (relación N-M), porque un mismo espacio
--    puede permitir varios tipos (ej.: zona grande para Carro/Camioneta/Camión).
-- =========================================================================
CREATE TABLE espacios (
    id_espacio   INT AUTO_INCREMENT,
    numero       INT          NOT NULL,
    estado       ENUM('LIBRE','OCUPADO','RESERVADO') NOT NULL DEFAULT 'LIBRE',
    CONSTRAINT pk_espacios PRIMARY KEY (id_espacio),
    CONSTRAINT uk_espacios_numero UNIQUE (numero),
    CONSTRAINT ck_espacios_numero CHECK (numero BETWEEN 1 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 3.b) espacio_tipo_permitido — Tabla puente N-M
--      Qué tipos de vehículo acepta cada espacio.
--      Reglas reales del parqueadero:
--        Espacios 1-70  : Carro, Camioneta, Camión
--        Espacios 71-90 : Moto
--        Espacios 91-100: Bicicleta
-- =========================================================================
CREATE TABLE espacio_tipo_permitido (
    id_espacio INT NOT NULL,
    id_tipo    INT NOT NULL,
    CONSTRAINT pk_espacio_tipo_permitido PRIMARY KEY (id_espacio, id_tipo),
    CONSTRAINT fk_etp_espacio FOREIGN KEY (id_espacio)
        REFERENCES espacios (id_espacio)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_etp_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 4) vehiculos — Identificado por placa. NO distinguimos cliente ocasional.
-- =========================================================================
CREATE TABLE vehiculos (
    placa     VARCHAR(10) NOT NULL,
    id_tipo   INT         NOT NULL,
    color     VARCHAR(30),
    marca     VARCHAR(30),
    CONSTRAINT pk_vehiculos PRIMARY KEY (placa),
    CONSTRAINT fk_vehiculos_tipo FOREIGN KEY (id_tipo)
        REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 5) clientes — Persona dueña de mensualidad
-- =========================================================================
CREATE TABLE clientes (
    id_cliente        INT AUTO_INCREMENT,
    documento         VARCHAR(20) NOT NULL,
    nombre_completo   VARCHAR(100) NOT NULL,
    telefono          VARCHAR(20),
    email             VARCHAR(120),
    CONSTRAINT pk_clientes PRIMARY KEY (id_cliente),
    CONSTRAINT uk_clientes_documento UNIQUE (documento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 6) mensualidades — Contrato mensual: cliente + período
--    El espacio NO va aquí: cada vehículo cubierto tiene su propio cupo
--    (ver mensualidad_vehiculo). Así dos vehículos del mismo cliente pueden
--    estar dentro a la vez y cada uno usa un espacio compatible con su tipo.
-- =========================================================================
CREATE TABLE mensualidades (
    id_mensualidad  INT AUTO_INCREMENT,
    id_cliente      INT          NOT NULL,
    fecha_inicio    DATE         NOT NULL,
    fecha_fin       DATE         NOT NULL,
    monto_pagado    DECIMAL(10,2) NOT NULL,
    estado          ENUM('ACTIVA','VENCIDA','CANCELADA') NOT NULL DEFAULT 'ACTIVA',
    CONSTRAINT pk_mensualidades PRIMARY KEY (id_mensualidad),
    CONSTRAINT fk_mensualidades_cliente FOREIGN KEY (id_cliente)
        REFERENCES clientes (id_cliente)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT ck_mensualidades_fechas CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT ck_mensualidades_monto  CHECK (monto_pagado >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 7) mensualidad_vehiculo — Tabla puente N–M (cada vehículo con SU cupo)
-- =========================================================================
CREATE TABLE mensualidad_vehiculo (
    id_mensualidad  INT         NOT NULL,
    placa           VARCHAR(10) NOT NULL,
    id_espacio      INT         NOT NULL,   -- cupo reservado para ESTE vehículo
    CONSTRAINT pk_mensualidad_vehiculo PRIMARY KEY (id_mensualidad, placa),
    CONSTRAINT fk_mv_mensualidad FOREIGN KEY (id_mensualidad)
        REFERENCES mensualidades (id_mensualidad)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_mv_vehiculo FOREIGN KEY (placa)
        REFERENCES vehiculos (placa)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_mv_espacio FOREIGN KEY (id_espacio)
        REFERENCES espacios (id_espacio)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================================================
-- 8) ingresos — Entrada/salida de un vehículo
-- =========================================================================
CREATE TABLE ingresos (
    id_ingreso          INT AUTO_INCREMENT,
    placa               VARCHAR(10)  NOT NULL,
    id_espacio          INT          NOT NULL,
    fecha_hora_entrada  DATETIME     NOT NULL,
    fecha_hora_salida   DATETIME,
    es_mensual          TINYINT(1)   NOT NULL DEFAULT 0,
    id_mensualidad      INT,
    id_tarifa           INT,
    monto_cobrado       DECIMAL(10,2),
    CONSTRAINT pk_ingresos PRIMARY KEY (id_ingreso),
    CONSTRAINT fk_ingresos_vehiculo FOREIGN KEY (placa)
        REFERENCES vehiculos (placa)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ingresos_espacio FOREIGN KEY (id_espacio)
        REFERENCES espacios (id_espacio)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    -- Nota: estas FK usan RESTRICT en AMBAS acciones (DELETE y UPDATE)
    -- porque sus columnas aparecen en el CHECK ck_ingresos_tipo_cobro.
    -- MySQL 8 prohíbe que una columna referenciada por un CHECK pueda
    -- ser modificada automáticamente por una acción referencial
    -- (CASCADE, SET NULL y SET DEFAULT cuentan como modificación;
    --  RESTRICT y NO ACTION no, porque solo bloquean).
    -- En la práctica perdemos poco: las PK son AUTO_INCREMENT y nunca
    -- se actualizan a mano. Y nunca queremos perder el vínculo
    -- histórico de un ingreso: para "borrar" se usa borrado lógico
    -- (cambiar estado/activa), no DELETE físico.
    CONSTRAINT fk_ingresos_mensualidad FOREIGN KEY (id_mensualidad)
        REFERENCES mensualidades (id_mensualidad)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_ingresos_tarifa FOREIGN KEY (id_tarifa)
        REFERENCES tarifas (id_tarifa)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_ingresos_fechas CHECK (
        fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_entrada
    ),
    CONSTRAINT ck_ingresos_monto CHECK (
        monto_cobrado IS NULL OR monto_cobrado >= 0
    ),
    CONSTRAINT ck_ingresos_tipo_cobro CHECK (
        -- Si es mensual: NO debe traer tarifa por hora.
        -- Si es ocasional: SÍ debe traer tarifa por hora.
        (es_mensual = 1 AND id_tarifa IS NULL AND id_mensualidad IS NOT NULL)
        OR
        (es_mensual = 0 AND id_mensualidad IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Índice útil para la consulta "¿qué vehículos están dentro?" (RF7)
CREATE INDEX idx_ingresos_dentro
    ON ingresos (fecha_hora_salida, fecha_hora_entrada);
