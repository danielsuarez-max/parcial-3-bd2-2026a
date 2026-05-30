# Notas de normalización — Proyecto N°6 (Control de parqueadero)

Este documento sustenta que el modelo está normalizado hasta **3FN**, cumpliendo
la exigencia mínima del parcial.

## 1. Resumen del modelo

El modelo cuenta con 8 entidades:

| # | Entidad | Tipo | PK |
|---|---|---|---|
| 1 | `tipo_vehiculo` | Catálogo | `id_tipo` |
| 2 | `tarifa` | Catálogo histórico | `id_tarifa` |
| 3 | `vehiculo` | Maestro | `placa` |
| 4 | `cliente` | Maestro | `id_cliente` |
| 5 | `espacio` | Catálogo | `id_espacio` |
| 6 | `mensualidad` | Transaccional | `id_mensualidad` |
| 7 | `mensualidad_vehiculo` | Tabla puente N–M | `(id_mensualidad, placa)` |
| 8 | `ingreso` | Transaccional | `id_ingreso` |

## 2. Verificación de las formas normales

### 2.1 Primera Forma Normal (1FN)

**Regla:** todos los atributos contienen valores atómicos (un solo valor por celda).

Toda nuestra tabla cumple 1FN porque:

- Ningún atributo guarda listas, conjuntos ni valores compuestos.
- En particular, los vehículos cubiertos por una mensualidad NO se guardan
  como una lista en `mensualidad`, sino que cada par mensualidad–vehículo
  es una fila en la tabla puente `mensualidad_vehiculo`.

### 2.2 Segunda Forma Normal (2FN)

**Regla:** estando en 1FN, ningún atributo no-clave depende parcialmente de
una clave compuesta. (Solo aplica a tablas con PK compuesta.)

La única tabla con PK compuesta es `mensualidad_vehiculo`, cuya PK es
`(id_mensualidad, placa)`. Esta tabla **no tiene atributos adicionales** más
allá de la propia clave, por lo que cumple 2FN trivialmente.

Las demás tablas tienen PK simple, por lo que 2FN se cumple por definición.

### 2.3 Tercera Forma Normal (3FN)

**Regla:** estando en 2FN, ningún atributo no-clave depende transitivamente
de la PK a través de otro atributo no-clave.

Verificación entidad por entidad:

| Tabla | Atributos no-clave | Dependencia | ¿3FN? |
|---|---|---|---|
| `tipo_vehiculo` | `nombre`, `descripcion` | Solo de `id_tipo` | ✅ |
| `tarifa` | `id_tipo`, `valor_hora`, `vigente_desde`, `activa` | Solo de `id_tarifa` | ✅ |
| `vehiculo` | `id_tipo`, `color`, `marca` | Solo de `placa` | ✅ |
| `cliente` | `documento`, `nombre_completo`, `telefono`, `email` | Solo de `id_cliente` | ✅ |
| `espacio` | `numero`, `estado`, `id_tipo_permitido` | Solo de `id_espacio` | ✅ |
| `mensualidad` | `id_cliente`, `id_espacio`, `fecha_inicio`, `fecha_fin`, `monto_pagado`, `estado` | Solo de `id_mensualidad` | ✅ |
| `mensualidad_vehiculo` | (ninguno) | — | ✅ |
| `ingreso` | `placa`, `id_espacio`, `fecha_hora_entrada`, `fecha_hora_salida`, `es_mensual`, `id_mensualidad`, `id_tarifa`, `monto_cobrado` | Solo de `id_ingreso` | ✅ |

**Punto sutil — caso `ingreso`:**

Podría parecer que `monto_cobrado` depende de `id_tarifa` y de la duración
del ingreso, generando una dependencia transitiva. **No es así**:
`monto_cobrado` es el resultado **histórico** de aplicar una fórmula en
el momento de la salida. Su valor pertenece al ingreso y queda congelado
incluso si más tarde cambia la tarifa. Por eso es correcto que viva
directamente en la fila del ingreso y no se "calcule cada vez".

Guardar `id_tarifa` junto al `monto_cobrado` permite auditar el cálculo
sin perder la trazabilidad cuando las tarifas evolucionan. Esta es una
decisión consciente de modelado, no una redundancia accidental.

## 3. Decisiones de diseño relevantes para la normalización

- **Tarifa con histórico (`vigente_desde`, `activa`)**: en lugar de
  sobrescribir el precio en `tipo_vehiculo`, las tarifas son una tabla
  independiente que conserva versiones a lo largo del tiempo.
  Esto evita anomalías de actualización al cambiar precios.

- **Separación `cliente` ↔ `mensualidad`**: un cliente puede tener varias
  mensualidades (renovaciones). No se duplican datos personales por cada
  renovación; cada renovación es una fila en `mensualidad`.

- **Tabla puente `mensualidad_vehiculo`**: resuelve la relación N–M entre
  mensualidades y vehículos sin violar 1FN.

- **Clientes ocasionales no se modelan**: la categoría "ocasional" no es
  una entidad con datos propios, sino una clasificación que surge de no
  estar en `cliente_mensual` activo. Evitamos crear filas vacías.
