"""
main.py — Capa de API (FastAPI).
Define los endpoints HTTP que el frontend (Angular) consumirá.
Cada endpoint ejecuta una consulta en la BD y devuelve JSON.
"""
import re

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
        FROM ingreso i
        JOIN vehiculo v        ON v.placa = i.placa
        JOIN tipo_vehiculo tv  ON tv.id_tipo = v.id_tipo
        JOIN espacio e         ON e.id_espacio = i.id_espacio
        LEFT JOIN mensualidad m ON m.id_mensualidad = i.id_mensualidad
        LEFT JOIN cliente c     ON c.id_cliente = m.id_cliente
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
        FROM tarifa t
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
            (SELECT COUNT(*) FROM espacio)                            AS total_espacios,
            (SELECT COUNT(*) FROM espacio WHERE estado = 'LIBRE')     AS libres,
            (SELECT COUNT(*) FROM espacio WHERE estado = 'OCUPADO')   AS ocupados,
            (SELECT COUNT(*) FROM espacio WHERE estado = 'RESERVADO') AS reservados,
            ROUND(
                (SELECT COUNT(*) FROM espacio WHERE estado = 'OCUPADO') * 100.0
                / (SELECT COUNT(*) FROM espacio), 2
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
        FROM ingreso i
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
        FROM espacio e
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
        FROM mensualidad m
        JOIN mensualidad_vehiculo mv ON mv.id_mensualidad = m.id_mensualidad
        JOIN cliente c               ON c.id_cliente = m.id_cliente
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
        cur.execute("SELECT numero, estado FROM espacio WHERE id_espacio = %s", (entrada.id_espacio,))
        espacio = cur.fetchone()
        if not espacio:
            raise HTTPException(
                status_code=404,
                detail=f"No existe un espacio con id {entrada.id_espacio}. Revisa GET /espacios/libres.",
            )

        # 3) ¿Ya está dentro? (evita dos entradas abiertas de la misma placa)
        cur.execute(
            "SELECT id_ingreso FROM ingreso WHERE placa = %s AND fecha_hora_salida IS NULL",
            (entrada.placa,),
        )
        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"El vehículo {entrada.placa} ya está registrado dentro del parqueadero.",
            )

        # 4) Tipo EFECTIVO: si la placa ya existe, manda el tipo guardado en la BD
        cur.execute("SELECT id_tipo FROM vehiculo WHERE placa = %s", (entrada.placa,))
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
                "INSERT INTO vehiculo (placa, id_tipo, color, marca) VALUES (%s, %s, %s, %s)",
                (entrada.placa, entrada.id_tipo, entrada.color, entrada.marca),
            )
            id_tipo_efectivo = entrada.id_tipo

        # 5) ¿Tiene mensualidad activa HOY?
        cur.execute(
            """
            SELECT m.id_mensualidad, m.id_espacio
            FROM mensualidad m
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
            cur.execute("SELECT numero, estado FROM espacio WHERE id_espacio = %s", (id_espacio,))
            esp_mensual = cur.fetchone()
            if esp_mensual["estado"] == "OCUPADO":
                raise HTTPException(
                    status_code=409,
                    detail=f"Tu cupo mensual (espacio N° {esp_mensual['numero']}) ya está ocupado por otro de tus vehículos.",
                )
            cur.execute(
                """
                INSERT INTO ingreso (placa, id_espacio, fecha_hora_entrada, es_mensual, id_mensualidad)
                VALUES (%s, %s, NOW(), 1, %s)
                """,
                (entrada.placa, id_espacio, mensualidad["id_mensualidad"]),
            )
            id_ingreso = cur.lastrowid
            cur.execute("UPDATE espacio SET estado = 'OCUPADO' WHERE id_espacio = %s", (id_espacio,))
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
                "SELECT id_tarifa FROM tarifa WHERE id_tipo = %s AND activa = 1 LIMIT 1",
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
                INSERT INTO ingreso (placa, id_espacio, fecha_hora_entrada, es_mensual, id_tarifa)
                VALUES (%s, %s, NOW(), 0, %s)
                """,
                (entrada.placa, entrada.id_espacio, tarifa["id_tarifa"]),
            )
            id_ingreso = cur.lastrowid
            cur.execute("UPDATE espacio SET estado = 'OCUPADO' WHERE id_espacio = %s", (entrada.id_espacio,))
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
            SELECT id_ingreso, placa, id_espacio, es_mensual, id_tarifa,
                   fecha_hora_entrada, fecha_hora_salida
            FROM ingreso WHERE id_ingreso = %s
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
            cur.execute("UPDATE ingreso SET fecha_hora_salida = NOW() WHERE id_ingreso = %s", (id_ingreso,))
            cur.execute("UPDATE espacio SET estado = 'RESERVADO' WHERE id_espacio = %s", (ing["id_espacio"],))
            modalidad = "MENSUAL"
        else:
            # --- OCASIONAL: cobro = CEIL(minutos / 60) × valor_hora de su tarifa ---
            cur.execute("SELECT valor_hora FROM tarifa WHERE id_tarifa = %s", (ing["id_tarifa"],))
            valor_hora = cur.fetchone()["valor_hora"]
            # NOW() es constante dentro de UNA sentencia: la hora de salida y el
            # cálculo del cobro usan exactamente el mismo instante.
            cur.execute(
                """
                UPDATE ingreso
                SET fecha_hora_salida = NOW(),
                    monto_cobrado = CEIL(TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, NOW()) / 60) * %s
                WHERE id_ingreso = %s
                """,
                (valor_hora, id_ingreso),
            )
            cur.execute("UPDATE espacio SET estado = 'LIBRE' WHERE id_espacio = %s", (ing["id_espacio"],))
            modalidad = "OCASIONAL"

        # 2) Leer el resultado final para devolver un resumen claro
        cur.execute(
            """
            SELECT
                TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, fecha_hora_salida)      AS minutos,
                CEIL(TIMESTAMPDIFF(MINUTE, fecha_hora_entrada, fecha_hora_salida) / 60) AS horas,
                monto_cobrado
            FROM ingreso WHERE id_ingreso = %s
            """,
            (id_ingreso,),
        )
        r = cur.fetchone()

    respuesta = {
        "mensaje": "Salida registrada",
        "id_ingreso": id_ingreso,
        "placa": ing["placa"],
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










































# Permite arrancar el servidor con:  python main.py
# Lee el puerto desde .env (APP_PORT); si no está, usa 8001 por defecto.
if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("APP_PORT", "8001"))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
