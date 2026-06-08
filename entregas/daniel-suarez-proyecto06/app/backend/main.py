"""
main.py — Capa de API (FastAPI).
Define los endpoints HTTP que el frontend (Angular) consumirá.
Cada endpoint ejecuta una consulta en la BD y devuelve JSON.
"""
import re
import calendar
from datetime import date
from enum import IntEnum

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


def sumar_un_mes(d: date) -> date:
    """
    Devuelve la fecha del mismo día del MES siguiente.
    Si ese día no existe en el mes destino (ej. 31-ene -> febrero), usa el
    último día válido (28/29-feb). Maneja el cambio de año (diciembre -> enero).
    """
    mes = d.month + 1
    anio = d.year
    if mes > 12:
        mes = 1
        anio += 1
    ultimo_dia = calendar.monthrange(anio, mes)[1]   # cuántos días tiene ese mes
    return date(anio, mes, min(d.day, ultimo_dia))


def validar_espacio_para_tipo(cur, id_espacio, id_tipo):
    """
    Valida el cupo de UN vehículo: el espacio debe existir, estar LIBRE y admitir
    ese tipo (espacio_tipo_permitido). Lanza 404/409 con mensaje claro.
    Devuelve el número visible del espacio.
    """
    cur.execute("SELECT numero, estado FROM espacios WHERE id_espacio = %s", (id_espacio,))
    esp = cur.fetchone()
    if not esp:
        raise HTTPException(status_code=404, detail=f"No existe un espacio con id {id_espacio}.")
    if esp["estado"] != "LIBRE":
        raise HTTPException(
            status_code=409,
            detail=f"El espacio N° {esp['numero']} no está libre (estado: {esp['estado']}).",
        )
    cur.execute(
        "SELECT 1 FROM espacio_tipo_permitido WHERE id_espacio = %s AND id_tipo = %s",
        (id_espacio, id_tipo),
    )
    if not cur.fetchone():
        cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (id_tipo,))
        nom = cur.fetchone()
        raise HTTPException(
            status_code=409,
            detail=f"El espacio N° {esp['numero']} no admite vehículos de tipo "
                   f"'{nom['nombre'] if nom else id_tipo}'.",
        )
    return esp["numero"]


# Catálogo fijo de tipos de vehículo (coincide con los IDs de la tabla tipo_vehiculo).
# Al usarlo como tipo de un campo, Swagger lo muestra como un MENÚ DESPLEGABLE
# y solo acepta estos valores -> imposible mandar un id_tipo inválido.
class TipoVehiculo(IntEnum):
    # El orden DEBE coincidir con la tabla tipo_vehiculo de la BD.
    CARRO = 1
    CAMIONETA = 2
    CAMION = 3
    MOTO = 4
    BICICLETA = 5


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


@app.get("/ingresos")
def historial_ingresos(placa: str | None = None, modalidad: str | None = None):
    """
    Historial de TODOS los ingresos (dentro y ya salidos), más reciente primero.
    Filtros opcionales y combinables:
      - ?placa=ABC123          -> solo ese vehículo.
      - ?modalidad=OCASIONAL    -> solo ocasionales (es_mensual = 0).
      - ?modalidad=MENSUAL      -> solo mensuales   (es_mensual = 1).
    A diferencia de /ingresos/dentro, este NO filtra por salida: muestra todo.
    """
    sql = """
        SELECT
            i.id_ingreso,
            v.placa,
            tv.nombre                          AS tipo_vehiculo,
            e.numero                           AS numero_espacio,
            i.fecha_hora_entrada,
            i.fecha_hora_salida,
            CASE WHEN i.fecha_hora_salida IS NULL THEN 'DENTRO' ELSE 'SALIÓ' END AS estado,
            CASE WHEN i.es_mensual = 1 THEN 'MENSUAL' ELSE 'OCASIONAL' END        AS modalidad,
            c.nombre_completo                  AS cliente_mensual,
            i.monto_cobrado,
            TIMESTAMPDIFF(MINUTE, i.fecha_hora_entrada,
                          COALESCE(i.fecha_hora_salida, NOW()))  AS minutos
        FROM ingresos i
        JOIN vehiculos v        ON v.placa = i.placa
        JOIN tipo_vehiculo tv  ON tv.id_tipo = v.id_tipo
        JOIN espacios e         ON e.id_espacio = i.id_espacio
        LEFT JOIN mensualidades m ON m.id_mensualidad = i.id_mensualidad
        LEFT JOIN clientes c     ON c.id_cliente = m.id_cliente
    """
    # Construimos el WHERE juntando las condiciones que sí lleguen.
    condiciones: list[str] = []
    valores: list = []
    if placa:
        condiciones.append("i.placa = %s")
        valores.append(placa.strip().upper())
    if modalidad:
        m = modalidad.strip().upper()
        if m == "MENSUAL":
            condiciones.append("i.es_mensual = 1")
        elif m == "OCASIONAL":
            condiciones.append("i.es_mensual = 0")
        # cualquier otro valor se ignora (no filtra)
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY i.fecha_hora_entrada DESC"
    return con_total(run_query(sql, tuple(valores)))

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
        ORDER BY t.id_tipo
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

@app.get("/espacios")
def listar_espacios():
    """
    RF5/RF7 — Mapa del parqueadero: TODOS los espacios con su estado.
    Para los OCUPADOS trae la placa del vehículo dentro; para los RESERVADOS,
    el cliente dueño del cupo. Sirve para pintar el plano visual del parqueadero.
    """
    sql = """
        SELECT
            e.id_espacio,
            e.numero,
            e.estado,
            i.placa            AS placa,            -- vehículo dentro ahora (si lo hay)
            r.nombre_completo  AS reservado_para    -- dueño del cupo (si está reservado)
        FROM espacios e
        LEFT JOIN ingresos i
               ON i.id_espacio = e.id_espacio
              AND i.fecha_hora_salida IS NULL       -- solo el ingreso ABIERTO
        LEFT JOIN (
            -- Reserva ACTIVA de cada espacio (un cupo solo puede tener una a la vez)
            SELECT mv.id_espacio, c.nombre_completo
            FROM mensualidad_vehiculo mv
            JOIN mensualidades m ON m.id_mensualidad = mv.id_mensualidad
             AND m.estado = 'ACTIVA'
             AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin
            JOIN clientes c ON c.id_cliente = m.id_cliente
        ) r ON r.id_espacio = e.id_espacio
        ORDER BY e.numero
    """
    return con_total(run_query(sql))


@app.get("/espacios/libres")
def espacios_libres(id_tipo: TipoVehiculo):
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
        SELECT m.id_mensualidad, mv.id_espacio, e.numero AS numero_espacio,
               m.fecha_inicio, m.fecha_fin, c.nombre_completo
        FROM mensualidades m
        JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
        JOIN clientes c               ON c.id_cliente = m.id_cliente
        JOIN espacios e               ON e.id_espacio = mv.id_espacio
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
    id_tipo: TipoVehiculo     # menú desplegable en Swagger (Carro, Moto, ...)
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
    "Bicicleta": (r"^BIC[0-9]{2}$", "código interno BIC + 2 números (la bici no lleva placa)", "BIC01"),
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

        # 5) ¿Tiene mensualidad activa HOY?  (el cupo es el de ESTA placa)
        cur.execute(
            """
            SELECT m.id_mensualidad, mv.id_espacio
            FROM mensualidades m
            JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
            WHERE mv.placa = %s AND m.estado = 'ACTIVA'
              AND CURDATE() BETWEEN m.fecha_inicio AND m.fecha_fin
            """,
            (entrada.placa,),
        )
        mensualidad = cur.fetchone()

        if mensualidad:
            # --- MENSUAL: entra a SU espacio reservado, SIN tarifa por hora ---
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
    id_tipo: TipoVehiculo
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


@app.get("/tarifas-mensuales")
def tarifas_mensuales():
    """RF4 — Catálogo del valor mensual estipulado por tipo de vehículo."""
    sql = """
        SELECT tm.id_tipo, tv.nombre AS tipo, tm.valor_mes
        FROM tarifa_mensual tm
        JOIN tipo_vehiculo tv ON tv.id_tipo = tm.id_tipo
        ORDER BY tm.id_tipo
    """
    return con_total(run_query(sql))


class TarifaMensualIn(BaseModel):
    """Nuevo valor mensual para un tipo de vehículo."""
    id_tipo: TipoVehiculo
    valor_mes: float


@app.put("/tarifas-mensuales")
def actualizar_tarifa_mensual(t: TarifaMensualIn):
    """
    RF4 — Cambia el valor mensual de un tipo de vehículo.
    A diferencia de las tarifas por hora (que versionan para preservar cobros),
    este es un catálogo simple sin histórico: se SOBRESCRIBE el valor (UPSERT).
    El histórico se preserva porque cada mensualidad ya guarda su monto_pagado.
    """
    if t.valor_mes < 0:
        raise HTTPException(status_code=422, detail="El valor mensual no puede ser negativo.")
    with transaccion() as cur:
        cur.execute("SELECT nombre FROM tipo_vehiculo WHERE id_tipo = %s", (t.id_tipo,))
        tipo = cur.fetchone()
        if not tipo:
            raise HTTPException(status_code=404, detail=f"No existe un tipo de vehículo con id {t.id_tipo}.")
        cur.execute(
            "INSERT INTO tarifa_mensual (id_tipo, valor_mes) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE valor_mes = VALUES(valor_mes)",
            (t.id_tipo, t.valor_mes),
        )
    return {
        "mensaje": "Tarifa mensual actualizada",
        "id_tipo": int(t.id_tipo),
        "tipo": tipo["nombre"],
        "valor_mes": t.valor_mes,
    }


@app.get("/tarifas/historico")
def tarifas_historico(id_tipo: TipoVehiculo):
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
    """Un vehículo cubierto por la mensualidad (se crea si no existe), con SU cupo."""
    placa: str
    id_tipo: TipoVehiculo
    id_espacio: int           # cupo reservado para ESTE vehículo

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("La placa no puede estar vacía.")
        return v


class MensualidadIn(BaseModel):
    """
    Alta de una mensualidad: cliente + fecha de inicio + vehículos (cada uno con
    su espacio). La fecha de fin y el monto NO se reciben: los calcula el backend
    (fin = inicio + 1 mes; monto = suma del valor mensual de cada vehículo).
    """
    cliente: ClienteIn
    fecha_inicio: date
    vehiculos: list[VehiculoMensualIn]


@app.post("/mensualidades")
def crear_mensualidad(m: MensualidadIn):
    """
    RF4 — Da de alta una mensualidad con su cupo (espacio reservado) y vehículos.
    Los vehículos se crean al vuelo si no existen (con validación de formato de placa).
    La duración es de 1 mes y el monto se calcula desde el catálogo tarifa_mensual.
    """
    if not m.vehiculos:
        raise HTTPException(status_code=422, detail="La mensualidad debe cubrir al menos un vehículo.")

    fecha_fin = sumar_un_mes(m.fecha_inicio)   # duración fija de 1 mes

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

        # 2) No se puede repetir el mismo espacio entre dos vehículos
        espacios_pedidos = [veh.id_espacio for veh in m.vehiculos]
        if len(espacios_pedidos) != len(set(espacios_pedidos)):
            raise HTTPException(status_code=409, detail="Cada vehículo debe tener un espacio distinto.")

        monto = 0
        numeros = []   # números de espacio asignados (para el mensaje)
        for veh in m.vehiculos:
            # 3) Crear el vehículo si no existe (validando formato y coherencia de tipo)
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

            # 4) Validar el espacio de ESE vehículo (existe + LIBRE + compatible)
            numeros.append(validar_espacio_para_tipo(cur, veh.id_espacio, veh.id_tipo))

            # 5) Sumar el valor mensual del tipo (catálogo)
            cur.execute("SELECT valor_mes FROM tarifa_mensual WHERE id_tipo = %s", (veh.id_tipo,))
            fila_tarifa = cur.fetchone()
            if not fila_tarifa:
                raise HTTPException(
                    status_code=409,
                    detail=f"No hay tarifa mensual configurada para el tipo con id {veh.id_tipo}.",
                )
            monto += float(fila_tarifa["valor_mes"])

        # 6) Insertar la mensualidad (sin espacio) y las asociaciones (placa + su cupo)
        cur.execute(
            """
            INSERT INTO mensualidades (id_cliente, fecha_inicio, fecha_fin, monto_pagado, estado)
            VALUES (%s, %s, %s, %s, 'ACTIVA')
            """,
            (id_cliente, m.fecha_inicio, fecha_fin, monto),
        )
        id_mensualidad = cur.lastrowid
        for veh in m.vehiculos:
            cur.execute(
                "INSERT INTO mensualidad_vehiculo (id_mensualidad, placa, id_espacio) VALUES (%s, %s, %s)",
                (id_mensualidad, veh.placa, veh.id_espacio),
            )
            # 7) Reservar el cupo de ese vehículo
            cur.execute("UPDATE espacios SET estado = 'RESERVADO' WHERE id_espacio = %s", (veh.id_espacio,))

    return {
        "mensaje": "Mensualidad creada",
        "id_mensualidad": id_mensualidad,
        "id_cliente": id_cliente,
        "cliente_nuevo": cliente_nuevo,
        "numeros_espacio": numeros,
        "fecha_fin": str(fecha_fin),
        "monto": monto,
        "vehiculos": [v.placa for v in m.vehiculos],
    }


@app.get("/mensualidades")
def listar_mensualidades():
    """RF4 — Mensualidades con su cliente, estado, fechas, monto y vehículos (cada
    uno con SU cupo). 'vehiculos' es una lista de {placa, numero_espacio}."""
    sql = """
        SELECT
            m.id_mensualidad,
            c.nombre_completo                                          AS cliente,
            m.estado,
            m.fecha_inicio,
            m.fecha_fin,
            m.monto_pagado,
            GROUP_CONCAT(CONCAT(mv.placa, ':', e.numero) ORDER BY mv.placa) AS veh
        FROM mensualidades m
        JOIN clientes c  ON c.id_cliente = m.id_cliente
        LEFT JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
        LEFT JOIN espacios e ON e.id_espacio = mv.id_espacio
        GROUP BY m.id_mensualidad, c.nombre_completo, m.estado,
                 m.fecha_inicio, m.fecha_fin, m.monto_pagado
        ORDER BY m.fecha_inicio DESC
    """
    filas = run_query(sql)
    for f in filas:
        # "ABC123:1,ABC12D:71" -> [{placa, numero_espacio}, ...]
        vehiculos = []
        if f["veh"]:
            for par in f["veh"].split(","):
                placa, numero = par.split(":")
                vehiculos.append({"placa": placa, "numero_espacio": int(numero)})
        f["vehiculos"] = vehiculos
        del f["veh"]
    return con_total(filas)


@app.get("/mensualidades/{id_mensualidad}/vehiculos")
def vehiculos_de_mensualidad(id_mensualidad: int):
    """RF4 — Vehículos cubiertos por una mensualidad (para precargar la renovación)."""
    sql = """
        SELECT v.placa, v.id_tipo, tv.nombre AS tipo,
               mv.id_espacio, e.numero AS numero_espacio
        FROM mensualidad_vehiculo mv
        JOIN vehiculos v       ON v.placa = mv.placa
        JOIN tipo_vehiculo tv ON tv.id_tipo = v.id_tipo
        JOIN espacios e        ON e.id_espacio = mv.id_espacio
        WHERE mv.id_mensualidad = %s
        ORDER BY v.placa
    """
    return con_total(run_query(sql, (id_mensualidad,)))


class RenovacionIn(BaseModel):
    """Renovación: el set de vehículos que cubrirá el mes renovado."""
    vehiculos: list[VehiculoMensualIn]


@app.post("/mensualidades/{id_mensualidad}/renovar")
def renovar_mensualidad(id_mensualidad: int, datos: RenovacionIn):
    """
    RF4 — Renueva una mensualidad VENCIDA creando un NUEVO período (fila nueva).
      - Reusa el cliente y el cupo de la mensualidad vencida.
      - Inicia hoy y dura 1 mes; el monto se calcula desde tarifa_mensual.
      - Permite editar los vehículos cubiertos (se precargan en el front).
      - La fila vencida NO se toca: queda como historial (el historial crece).
    """
    if not datos.vehiculos:
        raise HTTPException(status_code=422, detail="La renovación debe cubrir al menos un vehículo.")

    with transaccion() as cur:
        # 1) La mensualidad origen debe existir y estar VENCIDA (de ella tomamos el cliente)
        cur.execute(
            "SELECT id_cliente, estado FROM mensualidades WHERE id_mensualidad = %s",
            (id_mensualidad,),
        )
        men = cur.fetchone()
        if not men:
            raise HTTPException(status_code=404, detail=f"No existe una mensualidad con id {id_mensualidad}.")
        if men["estado"] != "VENCIDA":
            raise HTTPException(
                status_code=409,
                detail=f"Solo se pueden renovar mensualidades VENCIDAS (esta está {men['estado']}).",
            )
        id_cliente = men["id_cliente"]

        # 2) Nuevas fechas: inicia hoy, dura 1 mes
        fecha_inicio = date.today()
        fecha_fin = sumar_un_mes(fecha_inicio)

        # 3) Espacios distintos entre vehículos
        espacios_pedidos = [veh.id_espacio for veh in datos.vehiculos]
        if len(espacios_pedidos) != len(set(espacios_pedidos)):
            raise HTTPException(status_code=409, detail="Cada vehículo debe tener un espacio distinto.")

        monto = 0
        numeros = []
        for veh in datos.vehiculos:
            # 4) Crear el vehículo si no existe (validando formato y coherencia de tipo)
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

            # 5) Validar el espacio de ese vehículo (existe + LIBRE + compatible)
            numeros.append(validar_espacio_para_tipo(cur, veh.id_espacio, veh.id_tipo))

            # 6) Sumar el valor mensual del tipo (catálogo)
            cur.execute("SELECT valor_mes FROM tarifa_mensual WHERE id_tipo = %s", (veh.id_tipo,))
            fila_tarifa = cur.fetchone()
            if not fila_tarifa:
                raise HTTPException(
                    status_code=409,
                    detail=f"No hay tarifa mensual configurada para el tipo con id {veh.id_tipo}.",
                )
            monto += float(fila_tarifa["valor_mes"])

        # 7) Insertar la NUEVA mensualidad (período nuevo) y sus vehículos con su cupo
        cur.execute(
            """
            INSERT INTO mensualidades (id_cliente, fecha_inicio, fecha_fin, monto_pagado, estado)
            VALUES (%s, %s, %s, %s, 'ACTIVA')
            """,
            (id_cliente, fecha_inicio, fecha_fin, monto),
        )
        nuevo_id = cur.lastrowid
        for veh in datos.vehiculos:
            cur.execute(
                "INSERT INTO mensualidad_vehiculo (id_mensualidad, placa, id_espacio) VALUES (%s, %s, %s)",
                (nuevo_id, veh.placa, veh.id_espacio),
            )
            cur.execute("UPDATE espacios SET estado = 'RESERVADO' WHERE id_espacio = %s", (veh.id_espacio,))

    return {
        "mensaje": "Mensualidad renovada (nuevo período)",
        "nuevo_id_mensualidad": nuevo_id,
        "id_mensualidad_origen": id_mensualidad,
        "fecha_inicio": str(fecha_inicio),
        "fecha_fin": str(fecha_fin),
        "monto": monto,
    }


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
            SELECT m.estado, c.nombre_completo
            FROM mensualidades m
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

        # Cupos de TODOS los vehículos de la mensualidad
        cur.execute(
            """
            SELECT mv.id_espacio, e.numero, e.estado
            FROM mensualidad_vehiculo mv
            JOIN espacios e ON e.id_espacio = mv.id_espacio
            WHERE mv.id_mensualidad = %s
            """,
            (id_mensualidad,),
        )
        cupos = cur.fetchall()

        # Doble confirmación: sin 'confirmar': true no se ejecuta, solo se avisa.
        if not datos.confirmar:
            nums = ", ".join(f"N° {c['numero']}" for c in cupos)
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Vas a cancelar la mensualidad de {men['nombre_completo']} (cupos {nums}). "
                    f"Se liberarán los cupos y NO se puede deshacer. "
                    f'Para confirmar, reenvía la petición con "confirmar": true.'
                ),
            )

        # No cancelar si algún cupo tiene un vehículo dentro
        ocupados = [c["numero"] for c in cupos if c["estado"] == "OCUPADO"]
        if ocupados:
            raise HTTPException(
                status_code=409,
                detail=f"Hay un vehículo dentro en el/los cupo(s) N° {', '.join(map(str, ocupados))}. "
                       f"Registra primero su salida.",
            )

        cur.execute("UPDATE mensualidades SET estado = 'CANCELADA' WHERE id_mensualidad = %s", (id_mensualidad,))
        for c in cupos:
            cur.execute("UPDATE espacios SET estado = 'LIBRE' WHERE id_espacio = %s", (c["id_espacio"],))
    return {"mensaje": "Mensualidad cancelada", "id_mensualidad": id_mensualidad}


@app.post("/mensualidades/vencer-expiradas")
def vencer_mensualidades():
    """
    RF4 — Barrido: marca VENCIDA las mensualidades ACTIVA cuya fecha_fin ya pasó
    y libera sus cupos (RESERVADO -> LIBRE). Devuelve cuántas se vencieron.
    """
    with transaccion() as cur:
        # Primero libera los cupos (de cada vehículo) de las que van a vencer
        cur.execute(
            """
            UPDATE espacios e
            JOIN mensualidad_vehiculo mv ON mv.id_espacio = e.id_espacio
            JOIN mensualidades m          ON m.id_mensualidad = mv.id_mensualidad
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
