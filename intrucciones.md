Proyecto integrador — Parcial 3
Bases de Datos 2 · Unipaz · Cuarto semestre
Este repositorio contiene los 12 enunciados de proyecto del corte 3 de la asignatura Bases de Datos 2, junto con las normas de entrega y el flujo de trabajo con GitHub.

1. Propósito
Integrar lo aprendido este semestre (DDL, DML, normalización hasta 3FN) con lo visto en semestres anteriores (lógica computacional, POO, estructuras de datos y bases de datos 1) en un aplicativo funcional que use una base de datos relacional real.

2. Modalidad
24 estudiantes, 12 proyectos, modalidad individual.
Cada proyecto será desarrollado por dos estudiantes distintos, generando dos versiones independientes del mismo enunciado.
Habrá doble evaluación:
Calificación docente (técnica y de la asignatura): centrada en BD.
Calificación apreciativa entre pares: el grupo elige la mejor versión de cada proyecto.
3. Reglas técnicas
Motor de BD obligatorio: MySQL o PostgreSQL. Nada de SQLite ni archivos planos.
Lenguaje del aplicativo: libre (Java, Python, C#, JavaScript/Node, PHP, etc.).
Tipo de aplicación: libre (escritorio o web).
El aplicativo debe usar realmente la BD (lecturas y escrituras durante la sustentación).
Normalización mínima exigida: 3FN.
4. Entregables (los 12 por igual)
Aplicativo funcionando ejecutable durante la sustentación.
Diagrama MER completo, con entidades, atributos, PK, FK y cardinalidades.
Script DDL (.sql) que crea la base de datos desde cero.
Datos de prueba mínimos (script DML) que permitan sustentar el aplicativo.
README propio dentro de la carpeta de entrega, con instrucciones de instalación y ejecución.
5. Rúbrica de evaluación docente
Criterio	Peso
MER completo, correcto y normalizado hasta 3FN (PK, FK, cardinalidades)	40%
Aplicativo funcionando y usando realmente la BD	35%
Cumplimiento de los requisitos funcionales mínimos del enunciado	20%
Sustentación clara del diseño de BD	5%
El código en sí no es el foco de la evaluación: lo importante es que el aplicativo funcione y que la BD esté bien diseñada y usada.

6. Listado de proyectos
Los enunciados completos están en la carpeta proyectos/. Lectura obligatoria del enunciado asignado.

#	Proyecto	Resumen
01	Inmobiliaria de arrendamientos	Inmuebles, propietarios, arrendatarios, contratos, cuotas y mora.
02	Farmacia de barrio	Productos, lotes con vencimiento, ventas y compras a proveedores.
03	Reservas de restaurante	Mesas, reservas con validación de horario, órdenes y carta.
04	Citas médicas en consultorio	Pacientes, médicos por especialidad, agenda y consultas.
05	Venta de boletos de cine	Películas, salas, funciones y venta de boletos por butaca.
06	Control de parqueadero	Ingresos, cobro por tiempo y clientes mensuales con cupo.
07	Gestión de gimnasio	Afiliados, membresías, clases dirigidas y asistencia.
08	Hotel pequeño	Habitaciones, reservas por rango, check-in/out y consumos.
09	Gestión de eventos académicos	Eventos, ponentes, asistentes, asistencia y certificados.
10	Tienda online básica	Catálogo, carrito, pedidos y estados de pedido.
11	Taller mecánico	Vehículos, órdenes de trabajo, mecánicos y repuestos.
12	Veterinaria	Mascotas, consultas, aplicación de vacunas y tratamientos.
7. Flujo de trabajo con GitHub
El trabajo se entrega mediante fork + rama + pull request.

Paso a paso para el estudiante
Hacer fork de este repositorio a tu cuenta personal de GitHub.
Clonar tu fork localmente:
git clone https://github.com/<tu-usuario>/parcial-3-bd2.git
cd parcial-3-bd2
Crear una rama con un nombre claro:
git checkout -b entrega/nombre-apellido-proyectoXX
Ejemplo: entrega/juan-perez-proyecto03.
Crear tu carpeta dentro de entregas/:
entregas/nombre-apellido-proyectoXX/
Trabajar tu proyecto dentro de esa carpeta (ver estructura sugerida abajo).
Hacer commits frecuentes con mensajes claros:
git add entregas/nombre-apellido-proyectoXX
git commit -m "DDL inicial: tablas principales con PK y FK"
git push origin entrega/nombre-apellido-proyectoXX
Abrir un Pull Request desde tu rama hacia la rama main del repositorio original cuando hayas terminado.
El PR debe titularse: Entrega - Nombre Apellido - Proyecto XX.
Estructura sugerida dentro de tu carpeta
entregas/nombre-apellido-proyectoXX/
├── README.md         ← cómo instalar y correr TU aplicativo
├── mer/
│   ├── diagrama.png  (o .pdf)
│   └── notas-normalizacion.md
├── ddl/
│   ├── 01-crear-bd.sql
│   └── 02-datos-prueba.sql
└── app/
    └── (código fuente del aplicativo)
Reglas para tu PR
Solo modifica archivos dentro de tu carpeta. No edites los enunciados ni la entrega de otro estudiante.
No subas binarios pesados, ejecutables compilados, ni la BD .mysql/.pgdata. Sí el script .sql.
No subas archivos de configuración local con contraseñas (.env, config.json con credenciales).
Incluye en el README.md de tu entrega: cómo crear la BD, cómo cargar datos de prueba, cómo correr el aplicativo y un usuario de prueba para la sustentación.
8. Calificación apreciativa entre pares
Al cierre del corte, cada estudiante verá las dos versiones de cada proyecto (la suya y la del compañero asignado al mismo enunciado) revisando los forks o las carpetas en entregas/. El grupo votará la mejor versión por proyecto. Este puntaje complementa la calificación docente.

9. Fechas y plazos
Asignación de proyectos: por confirmar.
Fecha límite de PR: por confirmar.
Sustentaciones: por confirmar.
Las fechas se publicarán en este mismo README.

10. Preguntas
Cualquier duda sobre un enunciado, abrir un issue en este repositorio (no por mensaje privado). Esto permite que la respuesta llegue a todo el grupo.

