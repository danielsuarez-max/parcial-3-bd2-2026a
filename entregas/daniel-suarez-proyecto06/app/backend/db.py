"""
db.py — Capa de acceso a datos.
Centraliza la conexión a MySQL para que el resto del backend
no tenga que repetir credenciales ni lógica de conexión.
"""
import os
from dotenv import load_dotenv
import mysql.connector

# Lee el archivo .env y carga sus variables al entorno del proceso
load_dotenv()

# Parámetros de conexión leídos desde .env (con valor por defecto por si falta)
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "parqueadero"),
}


def get_connection():
    """Abre y devuelve una conexión nueva a MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


def run_query(sql, params=None):
    """
    Ejecuta un SELECT y devuelve las filas como lista de diccionarios.
    `params` pasa los valores de forma segura (evita inyección SQL).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)   # filas como dict en vez de tupla
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()      # cerramos el cursor pase lo que pase...
        conn.close()        # ...y la conexión, para no dejar recursos abiertos


# Si ejecutas "python db.py" directamente, prueba la conexión:
if __name__ == "__main__":
    print("Probando conexión a MySQL...")
    filas = run_query("SELECT COUNT(*) AS total FROM espacio")
    print("Conexión OK ✅  -> espacios en la BD:", filas[0]["total"])
