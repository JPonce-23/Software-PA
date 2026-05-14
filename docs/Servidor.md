# Servidor del proyecto SSALFER

## 1. Información general

- Sistema operativo: Ubuntu 24.04.3 LTS
- Kernel: Linux 6.8.0-111-generic
- Arquitectura: x86_64
- Usuario de trabajo: trenes
- IP interna: 172.16.1.215
- Memoria RAM: 7.6 GiB aprox.
- CPU: 4 vCPU
- Almacenamiento actual: 97 GB
- Espacio disponible actual: 86 GB aprox.

## 2. Estado inicial


```bash

Fecha de revisión: 14/05/2026

Comandos usados para revisar el servidor:

df -h
lscpu
free -h
whoami
lsb_release -a
uname -a
```

## 3. Actualización del sistema

```bash

Se ejecutaron los siguientes comandos para actualizar el servidor:

sudo apt update
sudo apt upgrade -y
```

 ## 4. Instalación de herramientas base


```bash
Se instalaron las herramientas necesarias para el desarrollo y despliegue del sistema:

sudo apt install git curl wget unzip nginx python3 python3-pip python3-venv -y
sudo apt install ufw -y
```

## 5. Verificación de Nginx

Se verificó el estado del servicio Nginx con el comando:

```bash
sudo systemctl status nginx
```

## 6. Instalación de PostgreSQL

Se instaló PostgreSQL y herramientas adicionales mediante:

```bash
sudo apt install postgresql postgresql-contrib -y
```

## 7. Verificación de PostgreSQL

Se verificó el acceso al motor PostgreSQL mediante:

```bash
sudo -u postgres psql
```

## 8. Carpeta principal del proyecto

Se creó la carpeta principal del sistema en:

```bash
/opt/ssalfer
```

## 9. Entorno virtual de Python

Se creó un entorno virtual dentro del proyecto para aislar dependencias del sistema.

Comandos utilizados:

```bash
python3 -m venv .venv
source .venv/bin/activate
```
## 10. Entorno virtual de Python

Se creó un entorno virtual dentro del proyecto para aislar dependencias del sistema.

Comandos utilizados:

```bash
python3 -m venv .venv
source .venv/bin/activate
