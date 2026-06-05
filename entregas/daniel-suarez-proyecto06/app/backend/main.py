"""
main.py — Capa de API (FastAPI).
Define los endpoints HTTP que el frontend (Angular) consumirá.
Cada endpoint ejecuta una consulta en la BD y devuelve JSON.
"""
import re
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from db import run_query, transaccion   # capa de datos (db.py)

# Crea la aplicación. title/description salen en la documentación Swagger.
app = FastAPI(
    title="API Parqueadero",
    description="Backend del control de parqueadero — Proyecto N°6",
    version="1.0.0",
)

# CORS: permite que Angular (puerto 4200) llame a este API (puerto 8001).
# Sin esto, el navegador bloquea la petición por seguridad.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def con_total(filas):
    """Envuelve una lista en {total, datos}: así el frontend recibe de una
    vez cuántos registros hay, sin tener que contarlos."""
    return {"total": len(filas), "datos": filas}


@app.get("/")
def inicio():
    """Endpoint de cortesía: confirma que el API está vivo."""
    return {"mensaje": "API Parqueadero funcionando 🚗"}


@app.get("/ingresos/dentro")
def vehiculos_dentro():
    """
    RF7 — Vehículos actualmente dentro del parqueadero.
    Un ingreso 'abierto' es el que todavía no tiene fecha_hora_salida.
    """
    sql = """
        SELECT
            i.id_ingreso,
            v.placa,
            tv.nombre                          AS tipo_vehiculo,
            e.numero                           AS numero_espacio,
            i.fecha_hora_entrada,
            CASE WHEN i.es_mensual = 1 THEN 'MENSUAL' ELSE 'OCASIONAL' END AS modalidad,
            c.nombre_completo                  AS cliente_mensual,
            TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada, NOW()) AS minutos_dentro
        FROM ingresos i
        JOIN vehiculos v        ON v.placa = i.placa
        JOIN tipo_vehiculo tv  ON tv.id_tipo = v.id_tipo
        JOIN espacios e         ON e.id_espacio = i.id_espacio
        LEFT JOIN mensualidades m ON m.id_mensualidad = i.id_mensualidad
        LEFT JOIN clientes c     ON c.id_cliente = m.id_cliente
        WHERE i.fecha_hora_salida IS NULL
        ORDER BY i.fecha_hora_entrada
    """
    return con_total(run_query(sql))

# ============================================================
#  CATÁLOGOS (los usará el frontend para llenar menús/listas)
# ============================================================

@app.get("/tipos")
def tipos_vehiculo():
    """Catálogo de tipos de vehículo (Carro, Moto, Bicicleta...)."""
    return con_total(run_query("SELECT id_tipo, nombre, descripcion FROM tipo_vehiculo ORDER BY id_tipo"))


@app.get("/tarifas")
def tarifas():
    """RF3 — Tarifas activas por tipo de vehículo (valor por hora)."""
    sql = """
        SELECT t.id_tarifa, t.id_tipo, tv.nombre AS tipo,
               t.valor_hora, t.vigente_desde
        FROM tarifas t
        JOIN tipo_vehiculo tv ON tv.id_tipo = t.id_tipo
        WHERE t.activa = 1
        ORDER BY tv.nombre
    """
    return con_total(run_query(sql))


# ============================================================
#  PANEL / REPORTES
# ============================================================

@app.get("/ocupacion")
def ocupacion():
    """Estado actual: libres / ocupados / reservados y % de ocupación."""
    sql = """
        SELECT
            (SELECT COUNT(*) FROM espacios)                            AS total_espacios,
            (SELECT COUNT(*) FROM espacios WHERE estado = 'LIBRE')     AS libres,
            (SELECT COUNT(*) FROM espacios WHERE estado = 'OCUPADO')   AS ocupados,
            (SELECT COUNT(*) FROM espacios WHERE estado = 'RESERVADO') AS reservados,
            ROUND(
                (SELECT COUNT(*) FROM espacios WHERE estado = 'OCUPADO') * 100.0
                / (SELECT COUNT(*) FROM espacios), 2
            )                                                         AS porcentaje_ocupacion
    """
    return run_query(sql)[0]   # una sola fila -> devolvemos el dict, no la lista


@app.get("/reportes/dia")
def reporte_dia():
    """RF6 — Ingresos cerrados agrupados por día, con recaudo de ocasionales."""
    sql = """
        SELECT
            DATE(i.fecha_hora_entrada)                        AS dia,
            COUNT(*)                                          AS total_ingresos,
            SUM(CASE WHEN i.es_mensual = 0 THEN 1 ELSE 0 END) AS ocasionales,
            SUM(CASE WHEN i.es_mensual = 1 THEN 1 ELSE 0 END) AS mensuales,
            COALESCE(SUM(i.monto_cobrado), 0)                 AS recaudado_ocasionales
        FROM ingresos i
        WHERE i.fecha_hora_salida IS NOT NULL
        GROUP BY DATE(i.fecha_hora_entrada)
        ORDER BY dia
    """
    return con_total(run_query(sql))


@app.get("/reportes/mes")
def reporte_mes():
    """RF6 — Resumen mensual por modalidad (ocasional/mensual) y recaudo."""
    sql = """
        SELECT
            meses.mes,
            COALESCE(ing.ingresos_ocasionales,    0) AS ingresos_ocasionales,
            COALESCE(ing.ingresos_mensuales,      0) AS ingresos_mensuales,
            COALESCE(ing.recaudado_ocasionales,   0) AS recaudado_ocasionales,
            COALESCE(men.recaudado_mensualidades, 0) AS recaudado_mensualidades
        FROM (
            SELECT DISTINCT DATE_FORMAT(fecha_hora_entrada, '%Y-%m') AS mes
            FROM ingresos WHERE fecha_hora_salida IS NOT NULL
            UNION
            SELECT DISTINCT DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes
            FROM mensualidades
        ) meses
        LEFT JOIN (
            SELECT
                DATE_FORMAT(fecha_hora_entrada, '%Y-%m')             AS mes,
                SUM(CASE WHEN es_mensual = 0 THEN 1 ELSE 0 END)      AS ingresos_ocasionales,
                SUM(CASE WHEN es_mensual = 1 THEN 1 ELSE 0 END)      AS ingresos_mensuales,
                SUM(CASE WHEN es_mensual = 0 THEN monto_cobrado END) AS recaudado_ocasionales
            FROM ingresos
            WHERE fecha_hora_salida IS NOT NULL
            GROUP BY DATE_FORMAT(fecha_hora_entrada, '%Y-%m')
        ) ing ON ing.mes = meses.mes
        LEFT JOIN (
            SELECT
                DATE_FORMAT(fecha_inicio, '%Y-%m') AS mes,
                SUM(monto_pagado)                  AS recaudado_mensualidades
            FROM mensualidades
            GROUP BY DATE_FORMAT(fecha_inicio, '%Y-%m')
        ) men ON men.mes = meses.mes
        ORDER BY meses.mes
    """
    return con_total(run_query(sql))


# ============================================================
#  RF5 — Disponibilidad de espacios
# ============================================================

@app.get("/espacios/libres")
def espacios_libres(id_tipo: int):
    """
    RF5 — Espacios LIBRES compatibles con un tipo de vehículo.
    Ejemplo:  /espacios/libres?id_tipo=1
    """
    sql = """
        SELECT e.id_espacio, e.numero
        FROM espacios e
        JOIN espacio_tipo_permitido etp ON etp.id_espacio = e.id_espacio
        WHERE e.estado = 'LIBRE'
          AND etp.id_tipo = %s
        ORDER BY e.numero
    """
    return con_total(run_query(sql, (id_tipo,)))


# ============================================================
#  Mensualidad de una placa (apoyo a RF1/RF2)
# ============================================================

@app.get("/vehiculos/{placa}/mensualidad")
def mensualidad_de_placa(placa: str):
    """
    ¿La placa tiene mensualidad ACTIVA hoy?
    Devuelve la(s) mensualidad(es) vigente(s). Lista vacía = es ocasional.
    Ejemplo:  /vehiculos/BCD890/mensualidad
    """
    sql = """
        SELECT m.id_mensualidad, m.id_espacio, m.fecha_inicio, m.fecha_fin,
               c.nombre_completo
        FROM mensualidades m
        JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
        JOIN clientes c               ON c.id_cliente = m.id_cliente
        WHERE mv.placa = %s
          AND m.estado = 'ACTIVA'
          AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin
    """
    return con_total(run_query(sql, (placa,)))


# ============================================================
#  RF1 — Registrar la ENTRADA de un vehículo   (POST = escribe)
# ============================================================

class EntradaIn(BaseModel):
    """Datos que el operador envía para registrar una entrada."""
    placa: str
    id_tipo: int              # tipo del vehículo (para crearlo si es su primera vez)
    id_espacio: int           # espacio elegido (se ignora si el vehículo es mensual)
    color: str | None = None  # opcional: solo se usa al crear el vehículo por 1ra vez
    marca: str | None = None  # opcional: idem

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        """La placa SIEMPRE se guarda en MAYÚSCULAS y sin espacios sobrantes."""
        v = v.strip().upper()
        if not v:
            raise ValueError("La placa no puede estar vacía.")
        return v


# Formato de placa esperado según el tipo de vehículo (estándar colombiano).
# nombre_tipo -> (expresión regular, descripción legible, ejemplo)
FORMATOS_PLACA = {
    "Carro":     (r"^[A-Z]{3}[0-9]{3}$", "3 letras y 3 números", "ABC123"),
    "Camioneta": (r"^[A-Z]{3}[0-9]{3}$", "3 letras y 3 números", "ABC123"),
    "Camión":    (r"^[A-Z]{3}[0-9]{3}$", "3 letras y 3 números", "ABC123"),
    "Moto":      (r"^[A-Z]{3}[0-9]{2}[A-Z]$", "3 letras, 2 números y 1 letra", "ABC12D"),
    "Bicicleta": (r"^BIC[0-9]{3}$", "código interno BIC + 3 números (la bici no lleva placa)", "BIC001"),
}


def validar_formato_placa(placa: str, nombre_tipo: str) -> None:
    """
    Verifica que la placa tenga el formato correcto para su tipo.
    Evita registros sin sentido (placa de carro en una moto, placa en una bici, etc.).
    Si el tipo no tiene una regla definida, no se valida el formato.
    """
    regla = FORMATOS_PLACA.get(nombre_tipo)
    if regla is None:
        return
    patron, descripcion, ejemplo = regla
    if not re.match(patron, placa):
        raise HTTPException(
            status_code=422,
            detail=f"La placa '{placa}' no tiene el formato válido para {nombre_tipo}: "
                   f"{descripcion} (ej. {ejemplo}).",
        )


@app.post("/ingresos")
def registrar_entrada(entrada: EntradaIn):
    """
    RF1 — Registra la entrada de un vehículo.
      - Si la placa tiene mensualidad activa -> entra a SU espacio reservado, sin cobro.
      - Si no -> es ocasional: valida que el espacio esté libre y sea compatible,
        y le asigna la tarifa vigente de su tipo.
    Todo ocurre dentro de una transacción: o se hace completo, o no se hace nada.
    """
    with transaccion() as cur:
        # 1) El TIPO de vehículo debe existir (su nombre se reutiliza en mensajes)
        cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (entrada.id_tipo,))
        tipo = cur.fetchone()
        if not tipo:
            raise HTTPException(
                status_code=404,
                detail=f"No existe un tipo de vehículo con id {entrada.id_tipo}. Consulta los tipos en GET /tipos.",
            )
        nombre_tipo = tipo["nombre"]

        # 2) El ESPACIO debe existir (traemos su número y estado para los mensajes)
        cur.execute("SELECT numero, estado FROM espacios WHERE id_espacio = %s", (entrada.id_espacio,))
        espacio = cur.fetchone()
        if not espacio:
            raise HTTPException(
                status_code=404,
                detail=f"No existe un espacio con id {entrada.id_espacio}. Revisa GET /espacios/libres.",
            )

        # 3) ¿Ya está dentro? (evita dos entradas abiertas de la misma placa)
        cur.execute(
            "SELECT id_ingreso FROM ingresos WHERE placa = %s AND fecha_hora_salida IS NULL",
            (entrada.placa,),
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"El vehículo {entrada.placa} ya está registrado dentro del parqueadero.",
            )

        # 4) Tipo EFECTIVO: si la placa ya existe, manda el tipo guardado en la BD
        cur.execute("SELECT id_tipo FROM vehiculos WHERE placa = %s", (entrada.placa,))
        veh = cur.fetchone()
        if veh:
            if veh["id_tipo"] != entrada.id_tipo:
                cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (veh["id_tipo"],))
                tipo_real = cur.fetchone()["nombre"]
                raise HTTPException(
                    status_code=409,
                    detail=f"La placa {entrada.placa} ya está registrada como '{tipo_real}', no '{nombre_tipo}'.",
                )
            id_tipo_efectivo = veh["id_tipo"]
        else:
            # Primera vez que vemos esta placa -> validamos su formato y la creamos
            validar_formato_placa(entrada.placa, nombre_tipo)
            cur.execute(
                "INSERT INTO vehiculos (placa, id_tipo, color, marca) VALUES (%s, %s, %s, %s)",
                (entrada.placa, entrada.id_tipo, entrada.color, entrada.marca),
            )
            id_tipo_efectivo = entrada.id_tipo

        # 5) ¿Tiene mensualidad activa HOY?
        cur.execute(
            """
            SELECT m.id_mensualidad, m.id_espacio
            FROM mensualidades m
            JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
            WHERE mv.placa = %s AND m.estado = 'ACTIVA'
              AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin
            """,
            (entrada.placa,),
        )
        mensualidad = cur.fetchone()

        if mensualidad:
            # --- MENSUAL: entra a su espacio reservado, SIN tarifa por hora ---
            id_espacio = mensualidad["id_espacio"]
            cur.execute("SELECT numero, estado FROM espacios WHERE id_espacio = %s", (id_espacio,))
            esp_mensual = cur.fetchone()
            if esp_mensual["estado"] == "OCUPADO":
                raise HTTPException(
                    status_code=409,
                    detail=f"Tu cupo mensual (espacio N° {esp_mensual['numero']}) ya está ocupado por otro de tus vehículos.",
                )
            cur.execute(
                """
                INSERT INTO ingresos (placa, id_espacio, fecha_hora_entrada, es_mensual, id_mensualidad)
                VALUES (%s, %s, NOW(), 1, %s)
                """,
                (entrada.placa, id_espacio, mensualidad["id_mensualidad"]),
            )
            id_ingreso = cur.lastrowid
            cur.execute("UPDATE espacios SET estado = 'OCUPADO' WHERE id_espacio = %s", (id_espacio,))
            numero_espacio = esp_mensual["numero"]
            modalidad = "MENSUAL"
        else:
            # --- OCASIONAL: tres validaciones SEPARADAS, cada una con su mensaje ---
            # (a) ¿El espacio está libre?
            if espacio["estado"] != "LIBRE":
                raise HTTPException(
                    status_code=409,
                    detail=f"El espacio N° {espacio['numero']} no está disponible (estado actual: {espacio['estado']}).",
                )
            # (b) ¿El espacio admite este tipo de vehículo?
            cur.execute(
                "SELECT 1 FROM espacio_tipo_permitido WHERE id_espacio = %s AND id_tipo = %s",
                (entrada.id_espacio, id_tipo_efectivo),
            )
            if not cur.fetchone():
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"El espacio N° {espacio['numero']} no admite vehículos de tipo '{nombre_tipo}'. "
                        f"Mira GET /espacios/libres?id_tipo={id_tipo_efectivo}."
                    ),
                )
            # (c) ¿Hay tarifa activa para este tipo?
            cur.execute(
                "SELECT id_tarifa FROM tarifas WHERE id_tipo = %s AND activa = 1 LIMIT 1",
                (id_tipo_efectivo,),
            )
            tarifa = cur.fetchone()
            if not tarifa:
                raise HTTPException(
                    status_code=409,
                    detail=f"No hay una tarifa activa para el tipo '{nombre_tipo}'.",
                )
            cur.execute(
                """
                INSERT INTO ingresos (placa, id_espacio, fecha_hora_entrada, es_mensual, id_tarifa)
                VALUES (%s, %s, NOW(), 0, %s)
                """,
                (entrada.placa, entrada.id_espacio, tarifa["id_tarifa"]),
            )
            id_ingreso = cur.lastrowid
            cur.execute("UPDATE espacios SET estado = 'OCUPADO' WHERE id_espacio = %s", (entrada.id_espacio,))
            id_espacio = entrada.id_espacio
            numero_espacio = espacio["numero"]
            modalidad = "OCASIONAL"

    # Si llegamos aquí, la transacción se confirmó (commit) sin errores.
    return {
        "mensaje": "Entrada registrada",
        "id_ingreso": id_ingreso,
        "placa": entrada.placa,
        "modalidad": modalidad,
        "id_espacio": id_espacio,
        "numero_espacio": numero_espacio,
    }


# ============================================================
#  RF2 — Registrar la SALIDA de un vehículo + cobro   (POST)
# ============================================================

@app.post("/ingresos/{id_ingreso}/salida")
def registrar_salida(id_ingreso: int):
    """
    RF2 — Cierra un ingreso abierto y calcula el cobro.
      - Ocasional: monto = horas (redondeadas hacia arriba) × tarifa vigente del ingreso.
      - Mensual: sin cobro por hora (ya pagó la mensualidad).
    Libera el espacio: ocasional -> LIBRE; mensual -> RESERVADO (sigue siendo su cupo).
    """
    with transaccion() as cur:
        # 1) Buscar el ingreso y validar que esté ABIERTO (sin salida)
        cur.execute(
            """
            SELECT i.id_ingreso, i.placa, i.id_espacio, i.es_mensual, i.id_tarifa,
                   i.fecha_hora_entrada, i.fecha_hora_salida,
                   tv.nombre AS tipo_vehiculo
            FROM ingresos i
            JOIN vehiculos v       ON v.placa = i.placa
            JOIN tipo_vehiculo tv ON tv.id_tipo = v.id_tipo
            WHERE i.id_ingreso = %s
            """,
            (id_ingreso,),
        )
        ing = cur.fetchone()
        if not ing:
            raise HTTPException(status_code=404, detail=f"No existe un ingreso con id {id_ingreso}.")
        if ing["fecha_hora_salida"] is not None:
            raise HTTPException(
                status_code=409,
                detail=f"El ingreso {id_ingreso} ya tiene una salida registrada.",
            )

        if ing["es_mensual"]:
            # --- MENSUAL: sin cobro por hora; el cupo vuelve a RESERVADO ---
            cur.execute("UPDATE ingresos SET fecha_hora_salida = NOW() WHERE id_ingreso = %s", (id_ingreso,))
            cur.execute("UPDATE espacios SET estado = 'RESERVADO' WHERE id_espacio = %s", (ing["id_espacio"],))
            modalidad = "MENSUAL"
        else:
            # --- OCASIONAL: cobro = CEIL(minutos / 60) × valor_hora de su tarifa ---
            cur.execute("SELECT valor_hora FROM tarifas WHERE id_tarifa = %s", (ing["id_tarifa"],))
            valor_hora = cur.fetchone()["valor_hora"]
            # NOW() es constante dentro de UNA sentencia: la hora de salida y el
            # cálculo del cobro usan exactamente el mismo instante.
            cur.execute(
                """
                UPDATE ingresos
                SET fecha_hora_salida = NOW(),
                    monto_cobrado = CEIL(TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, NOW()) / 60) * %s
                WHERE id_ingreso = %s
                """,
                (valor_hora, id_ingreso),
            )
            cur.execute("UPDATE espacios SET estado = 'LIBRE' WHERE id_espacio = %s", (ing["id_espacio"],))
            modalidad = "OCASIONAL"

        # 2) Leer el resultado final para devolver un resumen claro
        cur.execute(
            """
            SELECT
                TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, fecha_hora_salida)      AS minutos,
                CEIL(TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, fecha_hora_salida) / 60) AS horas,
                monto_cobrado
            FROM ingresos WHERE id_ingreso = %s
            """,
            (id_ingreso,),
        )
        r = cur.fetchone()

    respuesta = {
        "mensaje": "Salida registrada",
        "id_ingreso": id_ingreso,
        "placa": ing["placa"],
        "tipo_vehiculo": ing["tipo_vehiculo"],
        "modalidad": modalidad,
        "minutos_dentro": r["minutos"],
    }
    if modalidad == "OCASIONAL":
        respuesta["horas_cobradas"] = int(r["horas"])
        respuesta["monto_cobrado"] = float(r["monto_cobrado"])
    else:
        respuesta["monto_cobrado"] = None
        respuesta["nota"] = "Sin cargo por hora: incluido en la mensualidad."
    return respuesta


# ============================================================
#  RF3 — Configurar TARIFAS (con histórico)
# ============================================================

class TarifaIn(BaseModel):
    """Nueva tarifa por hora para un tipo de vehículo."""
    id_tipo: int
    valor_hora: float
    vigente_desde: date | None = None   # si no se indica, se usa la fecha de hoy


@app.post("/tarifas")
def crear_tarifa(tarifa: TarifaIn):
    """
    RF3 — Configura una nueva tarifa para un tipo de vehículo.
    No se EDITA la tarifa anterior (alteraría cobros históricos): se crea una nueva
    versión activa y se jubila la anterior (activa = 0). Así se preserva el histórico.
    """
    if tarifa.valor_hora < 0:
        raise HTTPException(status_code=422, detail="El valor por hora no puede ser negativo.")
    with transaccion() as cur:
        cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (tarifa.id_tipo,))
        tipo = cur.fetchone()
        if not tipo:
            raise HTTPException(status_code=404, detail=f"No existe un tipo de vehículo con id {tarifa.id_tipo}.")
        # Jubilar la tarifa activa actual de ese tipo y crear la nueva vigente
        cur.execute("UPDATE tarifas SET activa = 0 WHERE id_tipo = %s AND activa = 1", (tarifa.id_tipo,))
        vigente = tarifa.vigente_desde or date.today()
        cur.execute(
            "INSERT INTO tarifas (id_tipo, valor_hora, vigente_desde, activa) VALUES (%s, %s, %s, 1)",
            (tarifa.id_tipo, tarifa.valor_hora, vigente),
        )
        id_tarifa = cur.lastrowid
    return {
        "mensaje": "Tarifa configurada",
        "id_tarifa": id_tarifa,
        "tipo": tipo["nombre"],
        "valor_hora": tarifa.valor_hora,
        "vigente_desde": str(vigente),
    }


@app.get("/tarifas/historico")
def tarifas_historico(id_tipo: int):
    """RF3 — Histórico de tarifas de un tipo (activas e inactivas)."""
    sql = """
        SELECT t.id_tarifa, tv.nombre AS tipo, t.valor_hora, t.vigente_desde, t.activa
        FROM tarifas t
        JOIN tipo_vehiculo tv ON tv.id_tipo = t.id_tipo
        WHERE t.id_tipo = %s
        ORDER BY t.vigente_desde DESC, t.id_tarifa DESC
    """
    return con_total(run_query(sql, (id_tipo,)))


# ============================================================
#  RF4 — CLIENTES
# ============================================================

class ClienteIn(BaseModel):
    """Datos de un cliente (persona dueña de mensualidades)."""
    documento: str
    nombre_completo: str
    telefono: str | None = None
    email: str | None = None


@app.get("/clientes")
def listar_clientes():
    """RF4 — Lista de clientes."""
    return con_total(run_query(
        "SELECT id_cliente, documento, nombre_completo, telefono, email FROM clientes ORDER BY nombre_completo"
    ))


# ============================================================
#  RF4 — MENSUALIDADES
# ============================================================

class VehiculoMensualIn(BaseModel):
    """Un vehículo cubierto por la mensualidad (se crea si no existe)."""
    placa: str
    id_tipo: int

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("La placa no puede estar vacía.")
        return v


class MensualidadIn(BaseModel):
    """Alta de una mensualidad: cliente + cupo + período + vehículos."""
    cliente: ClienteIn
    id_espacio: int
    fecha_inicio: date
    fecha_fin: date
    monto_pagado: float
    vehiculos: list[VehiculoMensualIn]


@app.post("/mensualidades")
def crear_mensualidad(m: MensualidadIn):
    """
    RF4 — Da de alta una mensualidad con su cupo (espacio reservado) y vehículos.
    Los vehículos se crean al vuelo si no existen (con validación de formato de placa).
    """
    if m.fecha_fin < m.fecha_inicio:
        raise HTTPException(status_code=422, detail="La fecha de fin no puede ser anterior a la de inicio.")
    if not m.vehiculos:
        raise HTTPException(status_code=422, detail="La mensualidad debe cubrir al menos un vehículo.")
    if m.monto_pagado < 0:
        raise HTTPException(status_code=422, detail="El monto pagado no puede ser negativo.")

    with transaccion() as cur:
        # 1) Cliente: lo reutilizamos por documento, o lo creamos si no existe.
        #    Las tablas siguen separadas (3FN); solo unificamos la OPERACIÓN.
        cur.execute("SELECT id_cliente FROM clientes WHERE documento = %s", (m.cliente.documento,))
        fila = cur.fetchone()
        if fila:
            id_cliente = fila["id_cliente"]
            cliente_nuevo = False
        else:
            cur.execute(
                "INSERT INTO clientes (documento, nombre_completo, telefono, email) VALUES (%s, %s, %s, %s)",
                (m.cliente.documento, m.cliente.nombre_completo, m.cliente.telefono, m.cliente.email),
            )
            id_cliente = cur.lastrowid
            cliente_nuevo = True

        # 2) El espacio debe existir
        cur.execute("SELECT numero, estado FROM espacios WHERE id_espacio = %s", (m.id_espacio,))
        espacio = cur.fetchone()
        if not espacio:
            raise HTTPException(status_code=404, detail=f"No existe un espacio con id {m.id_espacio}.")

        # 2) El cupo no puede estar ya asignado a otra mensualidad activa que se solape
        cur.execute(
            """
            SELECT id_mensualidad FROM mensualidades
            WHERE id_espacio = %s AND estado = 'ACTIVA'
              AND fecha_inicio <= %s AND fecha_fin >= %s
            """,
            (m.id_espacio, m.fecha_fin, m.fecha_inicio),
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"El espacio N° {espacio['numero']} ya está asignado a otra mensualidad activa en esas fechas.",
            )

        # 3) Crear los vehículos que no existan (validando formato)
        for veh in m.vehiculos:
            cur.execute("SELECT id_tipo FROM vehiculos WHERE placa = %s", (veh.placa,))
            existente = cur.fetchone()
            if existente:
                if existente["id_tipo"] != veh.id_tipo:
                    raise HTTPException(
                        status_code=409,
                        detail=f"La placa {veh.placa} ya está registrada con otro tipo de vehículo.",
                    )
            else:
                cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (veh.id_tipo,))
                tipo = cur.fetchone()
                if not tipo:
                    raise HTTPException(status_code=404, detail=f"No existe un tipo de vehículo con id {veh.id_tipo}.")
                validar_formato_placa(veh.placa, tipo["nombre"])
                cur.execute("INSERT INTO vehiculos (placa, id_tipo) VALUES (%s, %s)", (veh.placa, veh.id_tipo))

        # 4) Insertar la mensualidad y asociar los vehículos
        cur.execute(
            """
            INSERT INTO mensualidades (id_cliente, id_espacio, fecha_inicio, fecha_fin, monto_pagado, estado)
            VALUES (%s, %s, %s, %s, %s, 'ACTIVA')
            """,
            (id_cliente, m.id_espacio, m.fecha_inicio, m.fecha_fin, m.monto_pagado),
        )
        id_mensualidad = cur.lastrowid
        for veh in m.vehiculos:
            cur.execute(
                "INSERT INTO mensualidad_vehiculo (id_mensualidad, placa) VALUES (%s, %s)",
                (id_mensualidad, veh.placa),
            )

        # 5) Reservar el cupo
        cur.execute("UPDATE espacios SET estado = 'RESERVADO' WHERE id_espacio = %s", (m.id_espacio,))

    return {
        "mensaje": "Mensualidad creada",
        "id_mensualidad": id_mensualidad,
        "id_cliente": id_cliente,
        "cliente_nuevo": cliente_nuevo,
        "numero_espacio": espacio["numero"],
        "vehiculos": [v.placa for v in m.vehiculos],
    }


@app.get("/mensualidades")
def listar_mensualidades():
    """RF4 — Mensualidades con su cliente, cupo, estado, fechas y placas."""
    sql = """
        SELECT
            m.id_mensualidad,
            c.nombre_completo                        AS cliente,
            e.numero                                 AS numero_espacio,
            m.estado,
            m.fecha_inicio,
            m.fecha_fin,
            m.monto_pagado,
            GROUP_CONCAT(mv.placa ORDER BY mv.placa) AS placas
        FROM mensualidades m
        JOIN clientes c  ON c.id_cliente = m.id_cliente
        JOIN espacios e  ON e.id_espacio = m.id_espacio
        LEFT JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
        GROUP BY m.id_mensualidad, c.nombre_completo, e.numero, m.estado,
                 m.fecha_inicio, m.fecha_fin, m.monto_pagado
        ORDER BY m.fecha_inicio DESC
    """
    filas = run_query(sql)
    for f in filas:
        # "ABC123,DEF45G" -> ["ABC123", "DEF45G"]  (lista vacía si no tiene vehículos)
        f["placas"] = f["placas"].split(",") if f["placas"] else []
    return con_total(filas)


class CancelacionIn(BaseModel):
    """Confirmación explícita para cancelar (evita cancelaciones accidentales)."""
    confirmar: bool = False


@app.put("/mensualidades/{id_mensualidad}/cancelar")
def cancelar_mensualidad(id_mensualidad: int, datos: CancelacionIn):
    """
    RF4 — Cancela una mensualidad y libera su cupo (espacio -> LIBRE).
    Requiere doble confirmación: la primera llamada (sin 'confirmar': true) solo
    avisa qué se va a cancelar; hay que reenviar con 'confirmar': true para ejecutar.
    """
    with transaccion() as cur:
        cur.execute(
            """
            SELECT m.id_espacio, m.estado, e.numero, c.nombre_completo
            FROM mensualidades m
            JOIN espacios e  ON e.id_espacio = m.id_espacio
            JOIN clientes c  ON c.id_cliente = m.id_cliente
            WHERE m.id_mensualidad = %s
            """,
            (id_mensualidad,),
        )
        men = cur.fetchone()
        if not men:
            raise HTTPException(status_code=404, detail=f"No existe una mensualidad con id {id_mensualidad}.")
        if men["estado"] == "CANCELADA":
            raise HTTPException(status_code=409, detail="La mensualidad ya está cancelada.")

        # Doble confirmación: sin 'confirmar': true no se ejecuta, solo se avisa.
        if not datos.confirmar:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Vas a cancelar la mensualidad de {men['nombre_completo']} (cupo N° {men['numero']}). "
                    f"Se liberará el cupo y NO se puede deshacer. "
                    f'Para confirmar, reenvía la petición con "confirmar": true.'
                ),
            )

        # No liberar el cupo si hay un vehículo dentro en ese espacio
        cur.execute("SELECT estado FROM espacios WHERE id_espacio = %s", (men["id_espacio"],))
        if cur.fetchone()["estado"] == "OCUPADO":
            raise HTTPException(
                status_code=409,
                detail="Hay un vehículo dentro en ese cupo. Registra primero su salida.",
            )
        cur.execute("UPDATE mensualidades SET estado = 'CANCELADA' WHERE id_mensualidad = %s", (id_mensualidad,))
        cur.execute("UPDATE espacios SET estado = 'LIBRE' WHERE id_espacio = %s", (men["id_espacio"],))
    return {"mensaje": "Mensualidad cancelada", "id_mensualidad": id_mensualidad}


@app.post("/mensualidades/vencer-expiradas")
def vencer_mensualidades():
    """
    RF4 — Barrido: marca VENCIDA las mensualidades ACTIVA cuya fecha_fin ya pasó
    y libera sus cupos (RESERVADO -> LIBRE). Devuelve cuántas se vencieron.
    """
    with transaccion() as cur:
        # Primero libera los espacios reservados de las que van a vencer
        cur.execute(
            """
            UPDATE espacios e
            JOIN mensualidades m ON m.id_espacio = e.id_espacio
            SET e.estado = 'LIBRE'
            WHERE m.estado = 'ACTIVA' AND m.fecha_fin < CURDATE() AND e.estado = 'RESERVADO'
            """
        )
        cur.execute(
            "UPDATE mensualidades SET estado = 'VENCIDA' WHERE estado = 'ACTIVA' AND fecha_fin < CURDATE()"
        )
        vencidas = cur.rowcount
    return {"mensaje": "Barrido completado", "mensualidades_vencidas": vencidas}










































# Permite arrancar el servidor con:  python main.py
# Lee el puerto desde .env (APP_PORT); si no está, usa 8001 por defecto.
if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("APP_PORT", "8001"))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
