# Software para la Procuraduría Agraria (PA)

## Objetivo
Repositorio para organizar el desarrollo y pruebas del proyecto de liberación de derechos de vía.

## Arquitectura y Tecnologías
El proyecto ha sido modernizado y ahora está completamente contenerizado usando **Docker**.

- **Frontend**: React.js con Vite (conservando el diseño original en HTML/CSS puro).
- **Backend**: Python con FastAPI y SQLAlchemy.
- **Base de Datos**: PostgreSQL con extensión PostGIS para datos geoespaciales.
- **Gestor DB**: PgAdmin4.
- **Orquestación**: Docker Compose.

## Estructura del Proyecto
- `backend/`: Código fuente de la API en FastAPI, modelos de datos, migraciones espaciales y scripts ETL.
- `frontend/`: Interfaz de usuario en React, vistas principales (Dashboard, Login, Mapa) y configuración de Vite.
- `docs/`: Documentación técnica y decisiones de arquitectura.
- `docker-compose.yml`: Archivo maestro para levantar toda la infraestructura de desarrollo.

## ¿Cómo ejecutar el proyecto?
Ya no es necesario instalar Python, Node.js ni bases de datos de forma local. Todo el entorno se levanta automáticamente.

1. Asegúrate de tener **Docker** y **Docker Compose** instalados.
2. Abre una terminal en la raíz del proyecto y ejecuta:
   ```bash
   docker-compose up -d --build
   ```
3. Una vez finalizado el proceso, los servicios estarán disponibles en:
   - **Frontend (Aplicación)**: [http://localhost:5173](http://localhost:5173)
   - **Backend (Documentación API)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PgAdmin (Gestor de BD)**: [http://localhost:5050](http://localhost:5050)

### Credenciales por Defecto
- **PgAdmin**: `fredy0505.sanchez@gmail.com` / `L3cl3rc1614sf90`
- **Base de Datos**: Usuario: `alfredo` / Password: `L3cl3rc1614+` / DB: `db_trenes` / Host: `db`
- **Sistema (Admin)**: `admin@sistema.com` / `Admin123!`

## Reglas de Colaboración (IMPORTANTE)
- No trabajar directo en la rama `main`.
- Cada rama debe tener su tarea específica (ej. `feature/nombre-tarea`).
- Los commits deben seguir convenciones ordenadas (`feat:`, `fix:`, `docs:`, etc.).
- Documentar en la carpeta `docs/` cada decisión importante de diseño.

## Creado por
- Jonathan Ponce
- Alfredo Cruz
