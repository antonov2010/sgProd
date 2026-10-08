# SG-Prod

Sistema de gestión de producción: asignación de personal, captura de calidad y tablero de KPIs. Está hecho con **Django 5.2** y **PostgreSQL**; la base de datos corre en Docker.

Este README sirve para tener tu ambiente local listo en unos 20 minutos. Si algo falla o quieres el detalle de cada paso, consulta la guía completa:

- [Guía del ambiente de desarrollo](docs/00_guia_ambiente_desarrollo.md): paso a paso, checklist y solución de problemas (§14).
- [Alcance del proyecto](docs/01_alcance_del_proyecto.md).

---

## 1. Requisitos

| Herramienta | Versión | Verificar |
| :--- | :--- | :--- |
| Python | 3.12 | `py -0p` (Windows) · `python3.12 --version` (Linux/macOS) |
| Git | cualquiera reciente | `git --version` |
| Docker Desktop (Windows/macOS) o Docker Engine (Linux) | con `docker compose` | `docker run --rm hello-world` |

> **Windows:** Docker Desktop debe estar **abierto** antes de cualquier comando `docker`. Necesitas al menos **10 GB libres** en disco. Si el disco se llena mientras Docker descarga imágenes, estas se corrompen (ver [Problemas comunes](#7-problemas-comunes)).

Configuración de una sola vez en Windows, para evitar problemas de fin de línea:

```powershell
git config --global core.autocrlf input
```

---

## 2. Clonar y crear el entorno virtual

```powershell
git clone https://github.com/antonov2010/sgProd.git
cd sgProd
git checkout dev

# Windows 11 (PowerShell)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
```

```bash
# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements/dev.txt
```

> Si PowerShell dice que *"la ejecución de scripts está deshabilitada"*, ejecuta una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (guía §14.13).

---

## 3. Crear tus dos archivos `.env`

El proyecto usa **dos** `.env`. Ninguno se sube a git: cada quien pone sus propios valores a partir de las plantillas `.env.example`.

| Archivo | Lo lee | Plantilla |
| :--- | :--- | :--- |
| `postgresql/.env` | Docker Compose (contenedor de PostgreSQL y pgAdmin) | `postgresql/.env.example` |
| `.env` (raíz) | Django | `.env.example` |

```powershell
Copy-Item postgresql\.env.example postgresql\.env   # Linux/macOS: cp postgresql/.env.example postgresql/.env
Copy-Item .env.example .env                         # Linux/macOS: cp .env.example .env
```

Después abre los dos archivos y reemplaza cada `your_...` con tus valores.

### `postgresql/.env`

| Variable | Qué poner |
| :--- | :--- |
| `POSTGRES_DB` | Nombre de **tu** base, por ejemplo `sgprod_dev_<tunombre>` |
| `DB_USR` | Usuario de PostgreSQL que tú elijas |
| `DB_PWD` | Contraseña que tú elijas |
| `PGADMIN_DEFAULT_EMAIL` | Tu correo (solo para entrar a pgAdmin local) |
| `PGADMIN_DEFAULT_PASSWORD` | Contraseña que tú elijas para pgAdmin |

### `.env` (raíz)

| Variable | Qué poner |
| :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` |
| `DJANGO_SECRET_KEY` | Una llave propia. Genérala con el comando de abajo |
| `DJANGO_DEBUG` | `True` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` |
| `DB_NAME` | **Igual** a `POSTGRES_DB` |
| `DB_USER` | **Igual** a `DB_USR` |
| `DB_PASSWORD` | **Igual** a `DB_PWD` |
| `DB_HOST` | `127.0.0.1` (en Windows **no** uses `localhost`) |
| `DB_PORT` | `5432` |
| `DB_CONN_MAX_AGE` | `60` |
| `TZ` | `America/Tijuana` |

Para generar tu `DJANGO_SECRET_KEY` (con el `.venv` activo):

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

> **La regla más importante:** `DB_NAME`, `DB_USER` y `DB_PASSWORD` del `.env` de la raíz deben coincidir **exactamente** con `POSTGRES_DB`, `DB_USR` y `DB_PWD` de `postgresql/.env`. Si no coinciden, Django no se conecta (guía §7.4).

---

## 4. Levantar PostgreSQL

```powershell
cd postgresql
docker compose up -d
docker compose ps        # espera a que pgsql diga (healthy); tarda menos de un minuto
cd ..
```

Prueba directa a la base (cambia el usuario y la base por los tuyos):

```powershell
docker exec -it pgsql psql -U <DB_USR> -d <POSTGRES_DB> -c "SELECT 1;"
```

pgAdmin queda en <http://localhost:8888>. Para registrar el servidor dentro de pgAdmin, usa **host `pgsql`**, puerto `5432`, y tu usuario y contraseña.

---

## 5. Migrar y arrancar Django

Desde la **raíz** del repositorio, con el `.venv` activo:

```powershell
python manage.py check --database default   # debe decir: no issues
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre <http://127.0.0.1:8000/admin/> e inicia sesión con tu superusuario. **Si entras, tu ambiente está listo.**

Verificación final de calidad:

```powershell
pytest            # debe correr sin fallos
ruff check .      # debe decir: All checks passed!
```

---

## 6. Día a día

```powershell
# Al empezar (Windows: primero abre Docker Desktop)
.\.venv\Scripts\Activate.ps1
git checkout dev; git pull
docker compose -f postgresql/docker-compose.yml up -d
python manage.py migrate          # por si alguien subió migraciones nuevas
python manage.py runserver

# Al terminar
# Ctrl+C para detener el servidor
docker compose -f postgresql/docker-compose.yml stop
```

### Flujo de trabajo con git

1. Crea una rama desde `dev`: `git checkout -b feat/<lo-que-haces>`.
2. Haz commit de tus cambios. Si cambias modelos, incluye las migraciones en el **mismo** commit.
3. Abre un PR hacia `dev` y pide revisión.
4. **Nunca** subas `.env`, `postgresql/.env` ni `postgresql/db-data/` (el `.gitignore` ya los excluye).
5. Avisa en el canal antes de tocar `config/settings/`, `docker-compose.yml` o `requirements/`.

---

## 7. Problemas comunes

| Síntoma | Solución |
| :--- | :--- |
| `failed to connect to the docker API` / `dockerDesktopLinuxEngine` | Docker Desktop no está abierto. Ábrelo y espera a que diga *Engine running*. |
| `port is already allocated` en el 5432 | Tienes otro PostgreSQL instalado en tu equipo. Detén ese servicio (guía §14.3). |
| `pgsql` se reinicia en bucle con `invalid user name 'postgres'` o `Bus error` | La imagen se descargó corrupta, normalmente porque el disco se llenó. Libera espacio y ejecuta `docker compose down`, luego `docker system prune -a`, luego `docker compose up -d`. |
| Docker Desktop muestra *"There was a problem with WSL"* tras llenarse el disco | Cierra Docker Desktop, ejecuta `wsl --shutdown` y vuelve a abrirlo. Si sigue fallando: *Troubleshoot → Clean / Purge data*. |
| `password authentication failed` | Tu `.env` de la raíz no coincide con `postgresql/.env` (sección 3). |
| `database "..." does not exist` | `DB_NAME` no coincide con `POSTGRES_DB`, o cambiaste `POSTGRES_DB` después de crear el contenedor (guía §14.6 y §14.9). |
| `No module named django` | No activaste el `.venv` (sección 2). |
| `connection timeout expired` al migrar | El contenedor no está arriba o aún no está `healthy` (sección 4). |

Para cualquier otro error, consulta la [§14 de la guía](docs/00_guia_ambiente_desarrollo.md#14-problemas-comunes-how-to-solve-them).

---

## 8. Estructura del proyecto

```text
sgProd/
├── manage.py
├── .env.example            # plantilla de variables de Django (sin valores)
├── requirements/           # base.txt, dev.txt
├── config/                 # proyecto Django
│   ├── settings/           # base.py, dev.py, prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/               # autenticación QR/PIN
│   ├── personal/           # empleados, estaciones, skill matrix (Módulo 1)
│   ├── calidad/            # captura horaria, defectos (Módulo 2)
│   └── dashboard/          # KPIs, bonos, capacitación (Módulo 3)
├── templates/              # base.html (paquete de diseño)
├── static/css/theme.css    # estilos compartidos (paquete de diseño)
├── postgresql/             # docker-compose.yml + .env.example del contenedor
├── SG-Prod_diseno/         # paquete de diseño original y guía de estilo
└── docs/                   # guía del ambiente, alcance del proyecto
```
