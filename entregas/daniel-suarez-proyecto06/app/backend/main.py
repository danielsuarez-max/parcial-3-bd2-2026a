"""
main.py — Capa de API (FastAPI).
Define los endpoints HTTP que el frontend (Angular) consumirá.
Cada endpoint ejecuta una consulta en la BD y devuelve JSON.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import run_query   # reutilizamos la capa de datos (db.py)

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
    return run_query(sql)


# Permite arrancar el servidor con:  python main.py
# Lee el puerto desde .env (APP_PORT); si no está, usa 8001 por defecto.
if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("APP_PORT", "8001"))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
