# Proyecto N°6 — Control de parqueadero

Aplicativo web para controlar entradas y salidas de vehículos en un parqueadero
de ~100 espacios numerados. Calcula el cobro por tiempo de permanencia, gestiona
clientes mensuales con cupo reservado y produce reportes de ingresos, con
persistencia en una base de datos relacional.

**Autor:** Daniel Suárez

---

## 1. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Base de datos | MySQL 8.0+ / MariaDB 10.5+ (operada con DBeaver) |
| Backend | Python 3.10+ · FastAPI · mysql-connector-python |
| Frontend | Angular 21 (SPA) |

---

## 2. Estructura del proyecto

```
daniel-suarez-proyecto06/
├── ddl/                      Scripts SQL (crear BD, datos de prueba, consultas)
│   ├── 01-crear-bd.sql       DDL: crea las 10 tablas con PK, FK, CHECK e índices
│   ├── 02-datos-prueba.sql   Datos de prueba (tipos, tarifas, espacios, clientes…)
│   └── 03-consultas.sql      Consultas/reportes que cubren RF5, RF6 y RF7
├── mer/
│   ├── parqueadero.png       Diagrama Entidad–Relación (PK, FK, cardinalidades)
│   └── notas-normalizacion.md  Verificación 1FN / 2FN / 3FN tabla por tabla
├── app/
│   ├── backend/              API FastAPI (main.py, db.py, requirements.txt)
│   └── frontend/             Aplicación Angular
└── README.md                 Este archivo
```

---

## 3. Prerrequisitos

Antes de empezar, tener instalado:

- **MySQL 8.0+** (o MariaDB 10.5+) en ejecución.
- **DBeaver** (para ejecutar los scripts `.sql`).
- **Python 3.10 o superior** — `python --version`
- **Node.js 20 o superior** y npm — `node --version`
- **Angular CLI** — si no lo tienes: `npm install -g @angular/cli`

---

## 4. Puesta en marcha

El orden es: **(1) base de datos → (2) backend → (3) frontend.**

### 4.1 Base de datos (en DBeaver)

1. Abrir una conexión a tu servidor MySQL en DBeaver.
2. Abrir y ejecutar los scripts **en este orden**:

   | Orden | Script | Qué hace |
   |---|---|---|
   | 1 | `ddl/01-crear-bd.sql` | Crea la BD `parqueadero` y sus 10 tablas. |
   | 2 | `ddl/02-datos-prueba.sql` | Inserta todos los datos de prueba (incluidas las tarifas mensuales). |

   > El script `01` borra la BD `parqueadero` si ya existe (`DROP DATABASE IF
   > EXISTS`) para partir de un estado limpio. Ejecutarlo solo en desarrollo.

3. *(Opcional)* Ejecutar `ddl/03-consultas.sql` para ver los reportes (RF5–RF7)
   directamente en SQL. Es solo lectura, no modifica datos.

### 4.2 Backend (FastAPI)

Desde una terminal, ubicado en `app/backend/`:

```bash
# 1. Crear y activar un entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows (PowerShell/CMD)
# source venv/bin/activate    # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la conexión a la BD
#    Copiar .env.example a .env y ajustar usuario/contraseña de MySQL
copy .env.example .env        # Windows
# cp .env.example .env         # Linux / macOS

# 4. Levantar el servidor
python main.py
```

El backend queda escuchando en **http://localhost:8001**.
Documentación interactiva (Swagger) en **http://localhost:8001/docs**.

> **Importante:** el frontend espera el backend en el puerto **8001**.
> No cambies `APP_PORT` en `.env` salvo que también lo ajustes en
> `app/frontend/src/app/services/api.ts`.

#### Variables del archivo `.env`

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DB_HOST` | `localhost` | Host de MySQL |
| `DB_PORT` | `3306` | Puerto de MySQL |
| `DB_USER` | `root` | Usuario de MySQL |
| `DB_PASSWORD` | *(vacío)* | Contraseña de MySQL |
| `DB_NAME` | `parqueadero` | Nombre de la BD |
| `APP_PORT` | `8001` | Puerto del backend |

### 4.3 Frontend (Angular)

En otra terminal, ubicado en `app/frontend/`:

```bash
# 1. Instalar dependencias
npm install

# 2. Levantar la aplicación
ng serve
```

Abrir el navegador en **http://localhost:4200**.

> El backend debe estar corriendo antes de usar la aplicación, de lo contrario
> las pantallas no cargarán datos.

---

## 5. Cobertura de requisitos funcionales

| RF | Descripción | Dónde se cumple |
|---|---|---|
| RF1 | Registrar entrada de un vehículo | Pantalla *Registrar entrada* |
| RF2 | Registrar salida y calcular tarifa por tiempo | Pantalla *Vehículos dentro* (botón salida) |
| RF3 | Configurar tarifas por tipo de vehículo | Pantalla *Tarifas* |
| RF4 | Gestionar clientes mensuales con cupo y vigencia | Pantalla *Mensualidades* |
| RF5 | Validar disponibilidad de espacios antes de un ingreso | Validación al registrar entrada |
| RF6 | Reporte de ingresos por día y por mes (ocasional/mensual) | Pantalla *Reportes* |
| RF7 | Consultar qué vehículos están actualmente dentro | Pantalla *Vehículos dentro* / *Ocupación* |

---

## 6. Datos de prueba incluidos

Tras ejecutar los scripts, la BD queda poblada con:

- 5 tipos de vehículo (Carro, Camioneta, Camión, Moto, Bicicleta)
- 100 espacios numerados con sus tipos permitidos
- Clientes y mensualidades activas con cupo asignado
- 60 ingresos (50 cerrados con su salida + 10 actualmente dentro)
- Tarifas por hora (con histórico) y tarifas mensuales por tipo

---

## 7. Modelo de datos

El diagrama Entidad–Relación está en **`mer/parqueadero.png`** y la verificación
de normalización hasta 3FN en **`mer/notas-normalizacion.md`**. El modelo consta
de 10 tablas (catálogos, maestras, transaccionales y dos tablas puente N–M).
