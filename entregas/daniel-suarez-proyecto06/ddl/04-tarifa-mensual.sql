-- ============================================================
--  04 — Catálogo de TARIFA MENSUAL por tipo de vehículo
-- ============================================================
-- Una mensualidad ya no cobra un monto digitado a mano: el valor del mes
-- está estipulado por tipo de vehículo en este catálogo. El monto de una
-- mensualidad se calcula como la SUMA del valor mensual de cada vehículo
-- que cubre. (La mensualidad guarda su propio monto_pagado, así que cambiar
-- este catálogo no altera contratos ya creados: se preserva el histórico.)

USE parqueadero;

CREATE TABLE IF NOT EXISTS tarifa_mensual (
    id_tipo   INT            NOT NULL,
    valor_mes DECIMAL(10,2)  NOT NULL,
    PRIMARY KEY (id_tipo),
    CONSTRAINT fk_tarifa_mensual_tipo
        FOREIGN KEY (id_tipo) REFERENCES tipo_vehiculo (id_tipo)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_valor_mes_no_negativo CHECK (valor_mes >= 0)
);

-- Valores semilla (uno por cada tipo de tipo_vehiculo: 1..5)
-- IDs reales: 1=Carro, 2=Camioneta, 3=Camión, 4=Moto, 5=Bicicleta
INSERT INTO tarifa_mensual (id_tipo, valor_mes) VALUES
    (1, 150000.00),   -- Carro
    (2, 180000.00),   -- Camioneta
    (3, 220000.00),   -- Camión
    (4,  70000.00),   -- Moto
    (5,  30000.00)    -- Bicicleta
AS nuevos
ON DUPLICATE KEY UPDATE valor_mes = nuevos.valor_mes;
