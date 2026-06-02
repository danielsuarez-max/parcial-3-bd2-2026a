-- =========================================================================
-- Proyecto N°6 — Control de parqueadero
-- Consultas y reportes para los requisitos funcionales
-- =========================================================================
--
-- Estas consultas cubren RF5 (validación de disponibilidad), RF6 (reportes
-- de ingresos) y RF7 (vehículos actualmente dentro). Las consultas 4 y 5
-- son auxiliares que usará el aplicativo al registrar entradas/salidas.
--
-- Fecha de referencia para los datos de prueba: 2026-05-30.
-- =========================================================================

USE parqueadero;

-- =========================================================================
-- Consulta 1 — RF7: Vehículos actualmente dentro del parqueadero
-- =========================================================================
-- Lógica: un ingreso "abierto" es aquel sin fecha_hora_salida.
-- Mostramos placa, tipo, espacio, hora de entrada y si es mensual/ocasional.
SELECT
    i.id_ingreso,
    v.placa,
    tv.nombre                          AS tipo_vehiculo,
    e.numero                           AS numero_espacio,
    i.fecha_hora_entrada,
    CASE WHEN i.es_mensual = 1 THEN 'MENSUAL' ELSE 'OCASIONAL' END AS modalidad,
    c.nombre_completo                  AS cliente_mensual,
    TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada, NOW()) AS minutos_dentro
FROM ingreso i
JOIN vehiculo v             ON v.placa = i.placa
JOIN tipo_vehiculo tv       ON tv.id_tipo = v.id_tipo
JOIN espacio e              ON e.id_espacio = i.id_espacio
LEFT JOIN mensualidad m     ON m.id_mensualidad = i.id_mensualidad
LEFT JOIN cliente c         ON c.id_cliente = m.id_cliente
WHERE i.fecha_hora_salida IS NULL
ORDER BY i.fecha_hora_entrada;
-- LEFT JOIN porque los ocasionales no tienen mensualidad/cliente.

-- =========================================================================
-- Consulta 2 — RF5: ¿Está permitido este tipo de vehículo en este espacio?
-- =========================================================================
-- Devuelve 1 si SÍ está permitido, 0 si NO.
-- Útil al registrar una entrada: validar antes de insertar.
SELECT EXISTS (
    SELECT 1
    FROM espacio_tipo_permitido etp
    JOIN espacio  e  ON e.id_espacio = etp.id_espacio
    JOIN vehiculo v  ON v.id_tipo    = etp.id_tipo
    WHERE e.numero = 5            -- número del espacio a validar
      AND v.placa  = 'ABC123'     -- placa del vehículo
) AS permitido;

-- =========================================================================
-- Consulta 3 — RF5: Listar espacios LIBRES compatibles con un tipo
-- =========================================================================
-- Útil cuando el operador necesita asignar manualmente un espacio.
-- Sustituye :id_tipo por el id del tipo del vehículo (ej: 1 = Carro).
SELECT
    e.id_espacio,
    e.numero
FROM espacio e
JOIN espacio_tipo_permitido etp ON etp.id_espacio = e.id_espacio
WHERE e.estado = 'LIBRE'
  AND etp.id_tipo = 1            -- id del tipo de vehículo
ORDER BY e.numero;

-- =========================================================================
-- Consulta 4 — RF1/RF2: ¿La placa X tiene mensualidad activa HOY?
-- =========================================================================
-- Si devuelve fila → es mensual hoy. Devuelve la mensualidad y el cupo.
-- Si vacío → es ocasional, debe cobrarse por hora al salir.
SELECT
    m.id_mensualidad,
    m.id_espacio,
    m.fecha_inicio,
    m.fecha_fin,
    c.nombre_completo
FROM mensualidad m
JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
JOIN cliente c               ON c.id_cliente = m.id_cliente
WHERE mv.placa = 'ABC123'
  AND m.estado = 'ACTIVA'
  AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin;

-- =========================================================================
-- Consulta 5 — RF2: Calcular monto a cobrar al salir (ocasional)
-- =========================================================================
-- Lógica: horas redondeadas hacia arriba × valor_hora de la tarifa activa
-- para el tipo del vehículo.
-- Sustituye :placa y :id_ingreso por los valores reales.
SELECT
    i.id_ingreso,
    i.placa,
    tv.nombre                    AS tipo,
    t.valor_hora,
    TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada, NOW())         AS minutos,
    CEIL(TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada, NOW())/60) AS horas_a_cobrar,
    CEIL(TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada, NOW())/60) * t.valor_hora
                                                                AS monto_a_cobrar
FROM ingreso i
JOIN vehiculo v        ON v.placa = i.placa
JOIN tipo_vehiculo tv  ON tv.id_tipo = v.id_tipo
JOIN tarifa t          ON t.id_tipo = v.id_tipo AND t.activa = 1
WHERE i.id_ingreso = 55            -- id del ingreso ocasional a cerrar
                                   -- (en los datos de prueba, los ocasionales
                                   --  abiertos son los IDs 55..60)
  AND i.fecha_hora_salida IS NULL
  AND i.es_mensual = 0;

-- =========================================================================
-- Consulta 6 — RF6: Reporte de ingresos por DÍA
-- =========================================================================
-- Cantidad de ingresos y total recaudado de ocasionales, agrupado por día.
SELECT
    DATE(i.fecha_hora_entrada)                            AS dia,
    COUNT(*)                                              AS total_ingresos,
    SUM(CASE WHEN i.es_mensual = 0 THEN 1 ELSE 0 END)     AS ocasionales,
    SUM(CASE WHEN i.es_mensual = 1 THEN 1 ELSE 0 END)     AS mensuales,
    COALESCE(SUM(i.monto_cobrado), 0)                     AS recaudado_ocasionales
FROM ingreso i
WHERE i.fecha_hora_salida IS NOT NULL
GROUP BY DATE(i.fecha_hora_entrada)
ORDER BY dia;
-- Solo cuenta ingresos cerrados (con salida); los abiertos no se han cobrado aún.

-- =========================================================================
-- Consulta 7 — RF6: Reporte de ingresos por MES, separando modalidad
-- =========================================================================
-- Resumen mensual: cuántos ingresos por modalidad y cuánto se recaudó.
--
-- Estructura en 3 partes:
--   meses : lista de TODOS los meses que aparecen en ingreso o mensualidad
--           (simula FULL OUTER JOIN que MySQL no soporta nativamente)
--   ing   : agregación de ingresos por mes
--   men   : agregación de mensualidades por mes
-- Se parte de `meses` con LEFT JOIN a las otras dos: ningún mes se pierde.
SELECT
    meses.mes,
    COALESCE(ing.ingresos_ocasionales,    0) AS ingresos_ocasionales,
    COALESCE(ing.ingresos_mensuales,      0) AS ingresos_mensuales,
    COALESCE(ing.recaudado_ocasionales,   0) AS recaudado_ocasionales,
    COALESCE(men.recaudado_mensualidades, 0) AS recaudado_mensualidades
FROM (
    -- Lista de meses: unión de los que aparecen en ambas tablas.
    -- UNION (no UNION ALL) elimina duplicados automáticamente.
    SELECT DISTINCT DATE_FORMAT(fecha_hora_entrada, '%Y-%m') AS mes
    FROM ingreso WHERE fecha_hora_salida IS NOT NULL
    UNION
    SELECT DISTINCT DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes
    FROM mensualidad
) meses
LEFT JOIN (
    SELECT
        DATE_FORMAT(fecha_hora_entrada, '%Y-%m')             AS mes,
        SUM(CASE WHEN es_mensual = 0 THEN 1 ELSE 0 END)      AS ingresos_ocasionales,
        SUM(CASE WHEN es_mensual = 1 THEN 1 ELSE 0 END)      AS ingresos_mensuales,
        SUM(CASE WHEN es_mensual = 0 THEN monto_cobrado END) AS recaudado_ocasionales
    FROM ingreso
    WHERE fecha_hora_salida IS NOT NULL
    GROUP BY DATE_FORMAT(fecha_hora_entrada, '%Y-%m')
) ing ON ing.mes = meses.mes
LEFT JOIN (
    SELECT
        DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes,
        SUM(monto_pagado)                  AS recaudado_mensualidades
    FROM mensualidad
    GROUP BY DATE_FORMAT(fecha_inicio, '%Y-%m')
) men ON men.mes = meses.mes
ORDER BY meses.mes;

-- =========================================================================
-- Consulta 8 — Extra: Ocupación actual y tasa de uso
-- =========================================================================
-- Da una visión rápida del estado del parqueadero en este momento.
-- Nota: `ocupados` (basado en espacio.estado) coincide con la cantidad de
-- vehículos actualmente dentro (ingresos sin salida) cuando el modelo
-- está sincronizado, por lo que mostrar ambas sería redundante.
SELECT
    (SELECT COUNT(*) FROM espacio)                            AS total_espacios,
    (SELECT COUNT(*) FROM espacio WHERE estado = 'LIBRE')     AS libres,
    (SELECT COUNT(*) FROM espacio WHERE estado = 'OCUPADO')   AS ocupados,
    (SELECT COUNT(*) FROM espacio WHERE estado = 'RESERVADO') AS reservados,
    ROUND(
        (SELECT COUNT(*) FROM espacio WHERE estado = 'OCUPADO') * 100.0
        / (SELECT COUNT(*) FROM espacio),
        2
    )                                                         AS porcentaje_ocupacion;
