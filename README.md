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
Ya no es necesario instalar Python, Node.js ni bases de datos de forma local. Todo el entorno se levanta automáticamente mediante contenedores.

### Requisitos Previos
- **Para Windows**: Instalar [Docker Desktop](https://www.docker.com/products/docker-desktop/). Asegúrate de tener habilitado WSL2 en la configuración de Docker.
- **Para Linux**: Instalar Docker Engine y Docker Compose. (Si no tienes a tu usuario en el grupo `docker`, deberás anteponer `sudo` a los siguientes comandos).

### Pasos de Despliegue
1. Abre una terminal (o PowerShell en Windows) en la raíz del proyecto.
2. Crea tu archivo de variables de entorno copiando el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```
3. Ejecuta el comando para construir y levantar toda la infraestructura:
   ```bash
   docker-compose up -d --build
   ```
   *(Nota en Linux: Si tienes problemas de permisos, usa `sudo docker-compose up -d --build`)*
4. Una vez finalizado el proceso, los servicios estarán disponibles en:
   - **Frontend (Aplicación)**: [http://localhost:5173](http://localhost:5173)
   - **Backend (Documentación API)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PgAdmin (Gestor de BD)**: [http://localhost:5050](http://localhost:5050)

### Comandos Útiles (Docker)
Si necesitas administrar el entorno o diagnosticar algún problema, puedes usar estos comandos en la terminal (desde la raíz del proyecto):
- **Ver los logs en tiempo real:** `docker-compose logs -f`
- **Detener los servicios sin borrar datos:** `docker-compose stop`
- **Apagar servicios por completo:** `docker-compose down`
- **Reiniciar base de datos desde cero (borrar volúmenes):** `docker-compose down -v`

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
