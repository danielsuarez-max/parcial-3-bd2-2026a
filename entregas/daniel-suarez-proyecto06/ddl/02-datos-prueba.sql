-- =========================================================================
-- Proyecto N°6 — Control de parqueadero
-- Script DML — Datos de prueba
-- Fecha de referencia: 2026-05-30 (HOY)
-- =========================================================================
--
-- Requiere que 01-crear-bd.sql se haya ejecutado previamente.
--
-- Contenido:
--   5  tipos de vehículo
--   5  tarifas (una por tipo)
--  100 espacios numerados (1..100)
--  12  clientes
--  ~30 vehículos
--  15  mensualidades (12 activas + 3 vencidas)
--  ~18 asociaciones mensualidad-vehiculo
--  60  ingresos (50 cerrados + 10 abiertos)
-- =========================================================================

USE parqueadero;

-- Limpieza por si se vuelve a ejecutar (orden inverso a las FK)
DELETE FROM ingreso;
DELETE FROM mensualidad_vehiculo;
DELETE FROM mensualidad;
DELETE FROM vehiculo;
DELETE FROM cliente;
DELETE FROM espacio;
DELETE FROM tarifa;
DELETE FROM tipo_vehiculo;

-- Reiniciar los AUTO_INCREMENT para que los IDs sean predecibles
ALTER TABLE tipo_vehiculo  AUTO_INCREMENT = 1;
ALTER TABLE tarifa         AUTO_INCREMENT = 1;
ALTER TABLE espacio        AUTO_INCREMENT = 1;
ALTER TABLE cliente        AUTO_INCREMENT = 1;
ALTER TABLE mensualidad    AUTO_INCREMENT = 1;
ALTER TABLE ingreso        AUTO_INCREMENT = 1;

-- =========================================================================
-- 1) tipo_vehiculo
-- =========================================================================
INSERT INTO tipo_vehiculo (nombre, descripcion) VALUES
    ('Carro',      'Vehículo particular de 4 ruedas'),
    ('Moto',       'Motocicleta de 2 ruedas'),
    ('Bicicleta',  'Bicicleta tradicional o eléctrica'),
    ('Camioneta',  'Vehículo SUV / pickup'),
    ('Camión',     'Vehículo de carga pesada');
-- IDs: 1=Carro, 2=Moto, 3=Bicicleta, 4=Camioneta, 5=Camión

-- =========================================================================
-- 2) tarifa (una activa por tipo)
-- =========================================================================
INSERT INTO tarifa (id_tipo, valor_hora, vigente_desde, activa) VALUES
    (1, 5000.00, '2026-01-01', 1),   -- Carro:     $5.000/h
    (2, 2500.00, '2026-01-01', 1),   -- Moto:      $2.500/h
    (3, 1000.00, '2026-01-01', 1),   -- Bicicleta: $1.000/h
    (4, 6500.00, '2026-01-01', 1),   -- Camioneta: $6.500/h
    (5, 9000.00, '2026-01-01', 1);   -- Camión:    $9.000/h
-- IDs tarifa: 1=Carro, 2=Moto, 3=Bici, 4=Camioneta, 5=Camión

-- =========================================================================
-- 3) espacio — 100 espacios numerados
--    Distribución por tipo permitido:
--      Espacios 1-70  : Carros y Camionetas (id_tipo_permitido NULL = cualquiera)
--      Espacios 71-90 : Motos (id_tipo = 2)
--      Espacios 91-100: Bicicletas (id_tipo = 3)
-- =========================================================================
-- Inserción masiva con un procedimiento simple
INSERT INTO espacio (numero, estado, id_tipo_permitido) VALUES
    -- Espacios 1-70: cualquier tipo (NULL = sin restricción)
    (1,  'LIBRE', NULL), (2,  'LIBRE', NULL), (3,  'LIBRE', NULL), (4,  'LIBRE', NULL), (5,  'LIBRE', NULL),
    (6,  'LIBRE', NULL), (7,  'LIBRE', NULL), (8,  'LIBRE', NULL), (9,  'LIBRE', NULL), (10, 'LIBRE', NULL),
    (11, 'LIBRE', NULL), (12, 'LIBRE', NULL), (13, 'LIBRE', NULL), (14, 'LIBRE', NULL), (15, 'LIBRE', NULL),
    (16, 'LIBRE', NULL), (17, 'LIBRE', NULL), (18, 'LIBRE', NULL), (19, 'LIBRE', NULL), (20, 'LIBRE', NULL),
    (21, 'LIBRE', NULL), (22, 'LIBRE', NULL), (23, 'LIBRE', NULL), (24, 'LIBRE', NULL), (25, 'LIBRE', NULL),
    (26, 'LIBRE', NULL), (27, 'LIBRE', NULL), (28, 'LIBRE', NULL), (29, 'LIBRE', NULL), (30, 'LIBRE', NULL),
    (31, 'LIBRE', NULL), (32, 'LIBRE', NULL), (33, 'LIBRE', NULL), (34, 'LIBRE', NULL), (35, 'LIBRE', NULL),
    (36, 'LIBRE', NULL), (37, 'LIBRE', NULL), (38, 'LIBRE', NULL), (39, 'LIBRE', NULL), (40, 'LIBRE', NULL),
    (41, 'LIBRE', NULL), (42, 'LIBRE', NULL), (43, 'LIBRE', NULL), (44, 'LIBRE', NULL), (45, 'LIBRE', NULL),
    (46, 'LIBRE', NULL), (47, 'LIBRE', NULL), (48, 'LIBRE', NULL), (49, 'LIBRE', NULL), (50, 'LIBRE', NULL),
    (51, 'LIBRE', NULL), (52, 'LIBRE', NULL), (53, 'LIBRE', NULL), (54, 'LIBRE', NULL), (55, 'LIBRE', NULL),
    (56, 'LIBRE', NULL), (57, 'LIBRE', NULL), (58, 'LIBRE', NULL), (59, 'LIBRE', NULL), (60, 'LIBRE', NULL),
    (61, 'LIBRE', NULL), (62, 'LIBRE', NULL), (63, 'LIBRE', NULL), (64, 'LIBRE', NULL), (65, 'LIBRE', NULL),
    (66, 'LIBRE', NULL), (67, 'LIBRE', NULL), (68, 'LIBRE', NULL), (69, 'LIBRE', NULL), (70, 'LIBRE', NULL),
    -- Espacios 71-90: solo Motos
    (71, 'LIBRE', 2), (72, 'LIBRE', 2), (73, 'LIBRE', 2), (74, 'LIBRE', 2), (75, 'LIBRE', 2),
    (76, 'LIBRE', 2), (77, 'LIBRE', 2), (78, 'LIBRE', 2), (79, 'LIBRE', 2), (80, 'LIBRE', 2),
    (81, 'LIBRE', 2), (82, 'LIBRE', 2), (83, 'LIBRE', 2), (84, 'LIBRE', 2), (85, 'LIBRE', 2),
    (86, 'LIBRE', 2), (87, 'LIBRE', 2), (88, 'LIBRE', 2), (89, 'LIBRE', 2), (90, 'LIBRE', 2),
    -- Espacios 91-100: solo Bicicletas
    (91, 'LIBRE', 3), (92, 'LIBRE', 3), (93, 'LIBRE', 3), (94, 'LIBRE', 3), (95, 'LIBRE', 3),
    (96, 'LIBRE', 3), (97, 'LIBRE', 3), (98, 'LIBRE', 3), (99, 'LIBRE', 3), (100,'LIBRE', 3);

-- =========================================================================
-- 4) cliente — 12 clientes
-- =========================================================================
INSERT INTO cliente (documento, nombre_completo, telefono, email) VALUES
    ('1098765432', 'Ana María Rodríguez',  '3001112233', 'ana.rodriguez@correo.com'),
    ('1023456789', 'Carlos Andrés Pérez',  '3002223344', 'carlos.perez@correo.com'),
    ('1011223344', 'Lucía Fernanda Gómez', '3003334455', 'lucia.gomez@correo.com'),
    ('1045678901', 'Jorge Iván Martínez',  '3004445566', 'jorge.martinez@correo.com'),
    ('1067890123', 'María José Castaño',   '3005556677', 'maria.castano@correo.com'),
    ('1078901234', 'Diego Alejandro López', '3006667788', 'diego.lopez@correo.com'),
    ('1089012345', 'Valentina Ruiz',       '3007778899', 'valentina.ruiz@correo.com'),
    ('1090123456', 'Sebastián Torres',     '3008889900', 'sebastian.torres@correo.com'),
    ('1102345678', 'Isabella Morales',     '3009990011', 'isabella.morales@correo.com'),
    ('1113456789', 'Andrés Felipe Vargas', '3010001122', 'andres.vargas@correo.com'),
    ('1124567890', 'Camila Hernández',     '3011112233', 'camila.hernandez@correo.com'),
    ('1135678901', 'Mateo Restrepo',       '3012223344', 'mateo.restrepo@correo.com');
-- IDs: 1..12

-- =========================================================================
-- 5) vehiculo — placas únicas, mezcla de tipos
-- =========================================================================
INSERT INTO vehiculo (placa, id_tipo, color, marca) VALUES
    -- Vehículos de clientes mensuales (carros y motos)
    ('ABC123', 1, 'Rojo',     'Mazda'),     -- Cliente 1 (Ana)
    ('ABC124', 2, 'Negro',    'Yamaha'),    -- Cliente 1 (Ana, segundo vehículo)
    ('DEF456', 1, 'Blanco',   'Chevrolet'), -- Cliente 2 (Carlos)
    ('GHI789', 1, 'Gris',     'Renault'),   -- Cliente 3 (Lucía)
    ('JKL012', 4, 'Azul',     'Toyota'),    -- Cliente 4 (Jorge - camioneta)
    ('MNO345', 1, 'Plata',    'Hyundai'),   -- Cliente 5 (María)
    ('PQR678', 2, 'Rojo',     'Honda'),     -- Cliente 6 (Diego - moto)
    ('STU901', 1, 'Negro',    'Kia'),       -- Cliente 7 (Valentina)
    ('STU902', 2, 'Azul',     'Suzuki'),    -- Cliente 7 (Valentina, segundo)
    ('VWX234', 1, 'Blanco',   'Nissan'),    -- Cliente 8 (Sebastián)
    ('YZA567', 4, 'Negro',    'Ford'),      -- Cliente 9 (Isabella - camioneta)
    ('BCD890', 1, 'Verde',    'Volkswagen'), -- Cliente 10 (Andrés)
    ('EFG123', 2, 'Blanco',   'Bajaj'),     -- Cliente 11 (Camila - moto)
    ('HIJ456', 1, 'Gris',     'Mazda'),     -- Cliente 12 (Mateo)
    -- Vehículos ocasionales (los usaremos en ingresos sin mensualidad)
    ('OCC001', 1, 'Rojo',     'Chevrolet'),
    ('OCC002', 1, 'Negro',    'Renault'),
    ('OCC003', 2, 'Azul',     'Yamaha'),
    ('OCC004', 1, 'Blanco',   'Toyota'),
    ('OCC005', 2, 'Negro',    'Honda'),
    ('OCC006', 1, 'Plata',    'Hyundai'),
    ('OCC007', 4, 'Rojo',     'Ford'),
    ('OCC008', 3, 'Azul',     'GW'),
    ('OCC009', 1, 'Verde',    'Mazda'),
    ('OCC010', 2, 'Rojo',     'Suzuki'),
    ('OCC011', 1, 'Negro',    'Nissan'),
    ('OCC012', 5, 'Blanco',   'Mercedes'),
    ('OCC013', 1, 'Gris',     'Kia'),
    ('OCC014', 2, 'Blanco',   'Bajaj'),
    ('OCC015', 3, 'Negro',    'Trek');

-- =========================================================================
-- 6) mensualidad — 12 activas + 3 vencidas
--    Las activas cubren 2026-05-30 (fecha de hoy)
-- =========================================================================
INSERT INTO mensualidad (id_cliente, id_espacio, fecha_inicio, fecha_fin, monto_pagado, estado) VALUES
    -- ACTIVAS (cubren hoy 2026-05-30)
    ( 1,  1, '2026-05-01', '2026-05-31', 150000.00, 'ACTIVA'),  -- Ana — espacio 1
    ( 2,  2, '2026-05-15', '2026-06-14', 150000.00, 'ACTIVA'),  -- Carlos — espacio 2
    ( 3,  3, '2026-05-01', '2026-05-31', 150000.00, 'ACTIVA'),  -- Lucía — espacio 3
    ( 4,  4, '2026-05-10', '2026-06-09', 180000.00, 'ACTIVA'),  -- Jorge (camioneta) — espacio 4
    ( 5,  5, '2026-05-01', '2026-05-31', 150000.00, 'ACTIVA'),  -- María — espacio 5
    ( 6, 71, '2026-05-05', '2026-06-04',  80000.00, 'ACTIVA'),  -- Diego (moto) — espacio 71
    ( 7,  6, '2026-05-01', '2026-05-31', 150000.00, 'ACTIVA'),  -- Valentina — espacio 6
    ( 8,  7, '2026-05-20', '2026-06-19', 150000.00, 'ACTIVA'),  -- Sebastián — espacio 7
    ( 9,  8, '2026-05-01', '2026-05-31', 180000.00, 'ACTIVA'),  -- Isabella (camioneta) — espacio 8
    (10,  9, '2026-05-15', '2026-06-14', 150000.00, 'ACTIVA'),  -- Andrés — espacio 9
    (11, 72, '2026-05-01', '2026-05-31',  80000.00, 'ACTIVA'),  -- Camila (moto) — espacio 72
    (12, 10, '2026-05-25', '2026-06-24', 150000.00, 'ACTIVA'),  -- Mateo — espacio 10
    -- VENCIDAS (histórico)
    ( 1,  1, '2026-04-01', '2026-04-30', 150000.00, 'VENCIDA'),  -- Renovación previa de Ana
    ( 3,  3, '2026-04-01', '2026-04-30', 150000.00, 'VENCIDA'),
    ( 5,  5, '2026-04-01', '2026-04-30', 150000.00, 'VENCIDA');
-- IDs mensualidad: 1..15

-- =========================================================================
-- 7) mensualidad_vehiculo — qué vehículos cubre cada mensualidad
--    Algunos clientes (Ana, Valentina) tienen 2 vehículos en su mensualidad
--    para demostrar la relación N-M.
-- =========================================================================
INSERT INTO mensualidad_vehiculo (id_mensualidad, placa) VALUES
    -- Mensualidades ACTIVAS
    ( 1, 'ABC123'),  ( 1, 'ABC124'),    -- Ana: carro + moto
    ( 2, 'DEF456'),                     -- Carlos: solo carro
    ( 3, 'GHI789'),                     -- Lucía
    ( 4, 'JKL012'),                     -- Jorge (camioneta)
    ( 5, 'MNO345'),                     -- María
    ( 6, 'PQR678'),                     -- Diego (moto)
    ( 7, 'STU901'),  ( 7, 'STU902'),    -- Valentina: carro + moto
    ( 8, 'VWX234'),                     -- Sebastián
    ( 9, 'YZA567'),                     -- Isabella (camioneta)
    (10, 'BCD890'),                     -- Andrés
    (11, 'EFG123'),                     -- Camila (moto)
    (12, 'HIJ456'),                     -- Mateo
    -- Mensualidades VENCIDAS (mismos vehículos cubiertos en el período pasado)
    (13, 'ABC123'),  (13, 'ABC124'),
    (14, 'GHI789'),
    (15, 'MNO345');

-- =========================================================================
-- 8) ingreso — 60 ingresos
--    50 cerrados (con salida) distribuidos en mayo de 2026
--    10 abiertos (sin salida) ocurridos hoy (2026-05-30) — esos son los
--    que están "actualmente dentro" para probar el RF7
--
-- Convención de cálculo de monto para ocasionales:
--   horas = TIME_TO_SEC(TIMEDIFF(salida, entrada)) / 3600, redondeo arriba
--   monto = horas * valor_hora_tarifa
-- Para mensuales: monto_cobrado = 0 (ya pagaron la mensualidad)
-- =========================================================================

-- --- Ingresos MENSUALES cerrados (de los clientes con mensualidad activa) ---
-- es_mensual=1, id_mensualidad=NN, id_tarifa=NULL, monto_cobrado=0
INSERT INTO ingreso (placa, id_espacio, fecha_hora_entrada, fecha_hora_salida, es_mensual, id_mensualidad, id_tarifa, monto_cobrado) VALUES
    ('ABC123',  1, '2026-05-02 07:30:00', '2026-05-02 17:45:00', 1,  1, NULL, 0),
    ('ABC123',  1, '2026-05-05 08:00:00', '2026-05-05 18:30:00', 1,  1, NULL, 0),
    ('ABC123',  1, '2026-05-10 07:15:00', '2026-05-10 19:00:00', 1,  1, NULL, 0),
    ('ABC124', 71, '2026-05-12 09:00:00', '2026-05-12 12:30:00', 1,  1, NULL, 0),
    ('DEF456',  2, '2026-05-16 07:45:00', '2026-05-16 17:30:00', 1,  2, NULL, 0),
    ('DEF456',  2, '2026-05-18 08:30:00', '2026-05-18 18:00:00', 1,  2, NULL, 0),
    ('DEF456',  2, '2026-05-20 07:00:00', '2026-05-20 16:45:00', 1,  2, NULL, 0),
    ('GHI789',  3, '2026-05-03 07:30:00', '2026-05-03 17:00:00', 1,  3, NULL, 0),
    ('GHI789',  3, '2026-05-06 08:00:00', '2026-05-06 18:30:00', 1,  3, NULL, 0),
    ('GHI789',  3, '2026-05-14 07:30:00', '2026-05-14 17:15:00', 1,  3, NULL, 0),
    ('JKL012',  4, '2026-05-11 07:00:00', '2026-05-11 18:00:00', 1,  4, NULL, 0),
    ('JKL012',  4, '2026-05-19 08:30:00', '2026-05-19 17:30:00', 1,  4, NULL, 0),
    ('MNO345',  5, '2026-05-04 07:15:00', '2026-05-04 18:45:00', 1,  5, NULL, 0),
    ('MNO345',  5, '2026-05-08 07:30:00', '2026-05-08 17:00:00', 1,  5, NULL, 0),
    ('MNO345',  5, '2026-05-21 08:00:00', '2026-05-21 19:00:00', 1,  5, NULL, 0),
    ('PQR678', 71, '2026-05-07 09:00:00', '2026-05-07 13:00:00', 1,  6, NULL, 0),
    ('PQR678', 71, '2026-05-13 10:30:00', '2026-05-13 16:30:00', 1,  6, NULL, 0),
    ('STU901',  6, '2026-05-09 07:45:00', '2026-05-09 18:15:00', 1,  7, NULL, 0),
    ('STU902', 72, '2026-05-15 09:00:00', '2026-05-15 12:00:00', 1,  7, NULL, 0),
    ('VWX234',  7, '2026-05-22 08:00:00', '2026-05-22 17:30:00', 1,  8, NULL, 0),
    ('VWX234',  7, '2026-05-26 07:30:00', '2026-05-26 18:00:00', 1,  8, NULL, 0),
    ('YZA567',  8, '2026-05-17 07:00:00', '2026-05-17 18:30:00', 1,  9, NULL, 0),
    ('YZA567',  8, '2026-05-23 08:15:00', '2026-05-23 17:45:00', 1,  9, NULL, 0),
    ('BCD890',  9, '2026-05-25 07:30:00', '2026-05-25 18:00:00', 1, 10, NULL, 0),
    ('EFG123', 72, '2026-05-02 10:00:00', '2026-05-02 14:30:00', 1, 11, NULL, 0),
    ('EFG123', 72, '2026-05-11 09:30:00', '2026-05-11 13:00:00', 1, 11, NULL, 0),
    ('EFG123', 72, '2026-05-24 11:00:00', '2026-05-24 15:30:00', 1, 11, NULL, 0),
    ('HIJ456', 10, '2026-05-27 08:00:00', '2026-05-27 17:30:00', 1, 12, NULL, 0),
    ('HIJ456', 10, '2026-05-28 07:30:00', '2026-05-28 18:30:00', 1, 12, NULL, 0),
    ('ABC123',  1, '2026-05-29 07:45:00', '2026-05-29 18:00:00', 1,  1, NULL, 0);
-- 30 ingresos mensuales cerrados

-- --- Ingresos OCASIONALES cerrados (placas OCC y algunas no-mensuales) ---
-- es_mensual=0, id_mensualidad=NULL, id_tarifa según el tipo, monto calculado
-- Recordar: tarifas → 1=Carro $5000, 2=Moto $2500, 3=Bici $1000, 4=Camioneta $6500, 5=Camión $9000
INSERT INTO ingreso (placa, id_espacio, fecha_hora_entrada, fecha_hora_salida, es_mensual, id_mensualidad, id_tarifa, monto_cobrado) VALUES
    -- 20 ocasionales cerrados, repartidos en mayo
    ('OCC001', 15, '2026-05-02 10:00:00', '2026-05-02 12:30:00', 0, NULL, 1, 15000.00),  -- 3h x 5000
    ('OCC002', 16, '2026-05-03 14:00:00', '2026-05-03 16:00:00', 0, NULL, 1, 10000.00),  -- 2h x 5000
    ('OCC003', 73, '2026-05-04 09:00:00', '2026-05-04 11:30:00', 0, NULL, 2,  7500.00),  -- 3h x 2500
    ('OCC004', 17, '2026-05-05 15:30:00', '2026-05-05 19:00:00', 0, NULL, 1, 20000.00),  -- 4h x 5000
    ('OCC005', 74, '2026-05-07 08:00:00', '2026-05-07 13:30:00', 0, NULL, 2, 15000.00),  -- 6h x 2500
    ('OCC006', 18, '2026-05-09 11:00:00', '2026-05-09 13:00:00', 0, NULL, 1, 10000.00),  -- 2h x 5000
    ('OCC007', 19, '2026-05-10 09:30:00', '2026-05-10 18:00:00', 0, NULL, 4, 58500.00),  -- 9h x 6500
    ('OCC008', 91, '2026-05-11 14:00:00', '2026-05-11 16:00:00', 0, NULL, 3,  2000.00),  -- 2h x 1000
    ('OCC009', 20, '2026-05-13 07:30:00', '2026-05-13 12:15:00', 0, NULL, 1, 25000.00),  -- 5h x 5000
    ('OCC010', 75, '2026-05-14 10:00:00', '2026-05-14 14:00:00', 0, NULL, 2, 10000.00),  -- 4h x 2500
    ('OCC011', 21, '2026-05-16 16:00:00', '2026-05-16 19:30:00', 0, NULL, 1, 20000.00),  -- 4h x 5000
    ('OCC012', 22, '2026-05-18 06:00:00', '2026-05-18 14:00:00', 0, NULL, 5, 72000.00),  -- 8h x 9000
    ('OCC013', 23, '2026-05-19 13:30:00', '2026-05-19 18:00:00', 0, NULL, 1, 25000.00),  -- 5h x 5000
    ('OCC014', 76, '2026-05-21 10:00:00', '2026-05-21 12:30:00', 0, NULL, 2,  7500.00),  -- 3h x 2500
    ('OCC015', 92, '2026-05-22 15:00:00', '2026-05-22 16:00:00', 0, NULL, 3,  1000.00),  -- 1h x 1000
    ('OCC001', 24, '2026-05-23 09:30:00', '2026-05-23 11:00:00', 0, NULL, 1, 10000.00),  -- 2h x 5000 (rep)
    ('OCC003', 77, '2026-05-25 13:00:00', '2026-05-25 17:30:00', 0, NULL, 2, 12500.00),  -- 5h x 2500
    ('OCC005', 78, '2026-05-26 10:00:00', '2026-05-26 12:00:00', 0, NULL, 2,  5000.00),  -- 2h x 2500
    ('OCC007', 25, '2026-05-27 14:00:00', '2026-05-27 19:00:00', 0, NULL, 4, 32500.00),  -- 5h x 6500
    ('OCC009', 26, '2026-05-28 11:30:00', '2026-05-28 14:30:00', 0, NULL, 1, 15000.00);  -- 3h x 5000
-- 20 ingresos ocasionales cerrados → total 50 cerrados

-- --- 10 ingresos ABIERTOS (sin salida, "actualmente dentro") ---
-- Ocurridos hoy 2026-05-30, distribuidos durante la mañana.
-- Probarán el RF7.
-- 4 mensuales + 6 ocasionales
INSERT INTO ingreso (placa, id_espacio, fecha_hora_entrada, fecha_hora_salida, es_mensual, id_mensualidad, id_tarifa, monto_cobrado) VALUES
    -- Mensuales actualmente dentro
    ('DEF456',  2, '2026-05-30 07:30:00', NULL, 1,  2, NULL, NULL),
    ('JKL012',  4, '2026-05-30 08:15:00', NULL, 1,  4, NULL, NULL),
    ('PQR678', 71, '2026-05-30 09:00:00', NULL, 1,  6, NULL, NULL),
    ('VWX234',  7, '2026-05-30 07:45:00', NULL, 1,  8, NULL, NULL),
    -- Ocasionales actualmente dentro
    ('OCC002', 27, '2026-05-30 09:30:00', NULL, 0, NULL, 1, NULL),
    ('OCC004', 28, '2026-05-30 10:00:00', NULL, 0, NULL, 1, NULL),
    ('OCC006', 79, '2026-05-30 10:15:00', NULL, 0, NULL, 2, NULL),
    ('OCC008', 93, '2026-05-30 10:30:00', NULL, 0, NULL, 3, NULL),
    ('OCC011', 29, '2026-05-30 11:00:00', NULL, 0, NULL, 1, NULL),
    ('OCC013', 30, '2026-05-30 11:30:00', NULL, 0, NULL, 1, NULL);

-- =========================================================================
-- Actualización del estado de los espacios:
--   Los 10 espacios actualmente ocupados pasan a 'OCUPADO'.
--   Los espacios asignados a mensuales que NO estén usándolos ahora
--   deberían estar 'RESERVADO'.
-- =========================================================================

-- Espacios actualmente ocupados (los 10 ingresos abiertos)
UPDATE espacio SET estado = 'OCUPADO'
    WHERE id_espacio IN (2, 4, 71, 7, 27, 28, 79, 93, 29, 30);

-- Espacios reservados (asignados a mensualidades activas pero sin uso ahora)
UPDATE espacio SET estado = 'RESERVADO'
    WHERE id_espacio IN (1, 3, 5, 72, 6, 8, 9, 10);
--   (1=Ana, 3=Lucía, 5=María, 72=Camila, 6=Valentina, 8=Isabella, 9=Andrés, 10=Mateo)

-- =========================================================================
-- Verificación rápida (descomenta si quieres verlas tras ejecutar):
-- =========================================================================
-- SELECT COUNT(*) AS total_ingresos          FROM ingreso;
-- SELECT COUNT(*) AS ingresos_actuales       FROM ingreso WHERE fecha_hora_salida IS NULL;
-- SELECT COUNT(*) AS mensualidades_activas   FROM mensualidad WHERE estado='ACTIVA';
-- SELECT estado, COUNT(*) FROM espacio GROUP BY estado;
