# SG-Prod

Sistema de gestión de producción: asignación de personal, captura de calidad y tablero de KPIs. Está hecho con **Django 5.2** y **PostgreSQL**; la base de datos corre en Docker.

Este README sirve para tener tu ambiente local listo en unos 20 minutos. Si algo falla o quieres el detalle de cada paso, consulta la guía completa:

- [Guía del ambiente de desarrollo](docs/00_guia_ambiente_desarrollo.md): paso a paso, checklist y solución de problemas (§14).
- [Alcance del proyecto](docs/01_alcance_del_proyecto.md).
- [Guía para probar US-05](docs/02_guia_pruebas_us05.md): pruebas automáticas y verificación manual de empleados, estaciones y la relación Jefe de Línea ↔ Línea.
- [Guía de la API REST y Swagger](docs/03_guia_api_swagger.md): autenticación, endpoints y cómo documentar uno nuevo.

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
python manage.py check_db  # base y migraciones en sync
pytest                     # debe correr sin fallos
ruff check .               # no debe introducir errores nuevos
```

### 5.1 Datos de demo (US-04)

Para cargar el escenario maestro de demostración:

```powershell
python manage.py seed_demo --reset
```

Carga **5 líneas, 40 estaciones, 200 empleados**, metas, catálogo de defectos y
matriz de habilidades desde [`data/seed/demo_sgprod.json`](data/seed/demo_sgprod.json).
El PIN de demo es `123456` y las credenciales se imprimen al terminar.

El comando **no** crea asignaciones ni registros de producción: esa lógica se
conecta en historias posteriores. Para una carga rápida o para simular menos
personal:

```powershell
python manage.py seed_demo --empleados 80 --reset
python manage.py seed_demo --archivo data/seed/demo_sgprod.json --reset
```

> `--reset` borra **todos los datos de dominio** de esa base (empleados, líneas,
> estaciones, habilidades, metas, defectos, asignaciones y registros), no solo
> los de demo. Úsalo solo en tu base local.
>
> Sin `--reset`, el comando actualiza y crea registros, pero **no elimina** los
> que ya existían. Para un volumen exacto, combina `--reset --empleados N`.

### 5.2 Revisar que la base coincide con la rama

> **Si acabas de clonar el repositorio y nunca usaste otra rama, no necesitas
> una base nueva.** Crea tu base personal normal, corre `migrate`, `seed_demo
> --reset` y `check_db`. La base adicional es solo para quien ya tiene una base
> contaminada por otra rama con modelos distintos, o para quien quiere conservar
> esa base vieja mientras prueba otra rama.

Antes de culpar al código, revisa el estado de la base. El siguiente comando es
**solo lectura** y no modifica nada:

```powershell
python manage.py check_db
```

Comprueba que existan las tablas y columnas de esta rama, que no haya
migraciones aplicadas por otra rama y muestra cuántos datos de demo hay.
Devuelve código de salida `1` si el esquema o las migraciones no coinciden.

Si ves un error como:

```text
psycopg.errors.UndefinedColumn: column calidad_registrocalidadhorario.asignacion_id does not exist
```

la base quedó con el esquema de otra rama (por ejemplo, la rama vieja del MVP).
`python manage.py migrate` no lo corrige, porque las migraciones de esa rama ya
no existen en este checkout. La guía tiene el procedimiento completo en
[§14.8.1](docs/00_guia_ambiente_desarrollo.md#1481-errores-de-columna-al-cambiar-de-rama).

Resumen:

```powershell
# Opción recomendada: crear una base nueva y conservar la anterior
docker exec -it pgsql psql -U <usuario> -d postgres -c "CREATE DATABASE sgprod_dev_ui;"
# Cambia solo DB_NAME en el .env de la raíz a sgprod_dev_ui.
# POSTGRES_DB no cambia: el contenedor ya creó su base inicial.
python manage.py migrate
python manage.py check_db
python manage.py seed_demo --reset

# Alternativa destructiva: reiniciar el esquema de la base actual
docker exec -it pgsql psql -U <usuario> -d <tu_base> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python manage.py migrate
python manage.py check_db
```

> No uses `migrate --fake` ni borres archivos de migración para “arreglar” esto.
> Una base debe corresponder a una sola rama con modelos compatibles.

### 5.3 Admin de personal: empleados y estaciones (US-05)

El Admin de Django es la pantalla de consulta y administración de empleados y
estaciones (RF-1.1). Un superusuario ve todas las líneas y estaciones, y la
lista completa de empleados con su estado.

Desde la corrección de US-06 el modelo ya tiene la relación que faltaba:

- `Empleado.linea`: línea a la que pertenece el empleado.
- `Linea.jefe_linea`: Jefe de Línea responsable de esa línea.

Aplica la migración:

```bash
python manage.py migrate
```

La asignación de líneas del escenario demo queda a cargo de la historia de
seed (Karen). Mientras tanto, puedes asignar `Empleado.linea` y
`Linea.jefe_linea` desde el Admin.

Para que un **Jefe de Línea** vea únicamente su línea en el Admin:

1. Crea el usuario del jefe y marca **Staff status**; otórgale los permisos de
   consulta de empleados, estaciones, líneas y habilidades.
2. Asígnalo al grupo de su línea en *Authentication and Authorization → Groups*
   (`Línea 3`, `Línea 4`, …).
3. En *Personal → Empleados*, verifica que el personal tenga su **Línea**
   asignada; en *Personal → Líneas*, que la línea tenga a su
   **Jefe de línea**.

Con eso, el jefe solo ve al personal activo, las estaciones, su línea y la
matriz de habilidades de su línea. Un usuario sin grupo de línea no ve datos de
planta.

El paso a paso para verificar la historia (pruebas automáticas, usuarios de
prueba y los criterios de aceptación) está en la
[guía para probar US-05](docs/02_guia_pruebas_us05.md). La verificación de la
corrección US-06 en la UI, con los conteos esperados por línea, está en la
[§8 de esa misma guía](docs/02_guia_pruebas_us05.md).

---

## 6. Día a día

```powershell
# Al empezar (Windows: primero abre Docker Desktop; PostgreSQL arranca solo)
.\.venv\Scripts\Activate.ps1
git checkout dev; git pull
python -m pip install -r requirements/dev.txt
python manage.py migrate          # por si alguien subió migraciones nuevas
python manage.py check_db         # ¿la base coincide con esta rama?
python manage.py runserver

# Al terminar: Ctrl+C para detener el servidor
```

> No hace falta levantar PostgreSQL cada día: el compose usa `restart: unless-stopped`, así que `pgsql` y `pgadmin` arrancan solos al abrir Docker Desktop. Solo vuelven a requerir `docker compose up -d` si los detuviste con `docker compose stop`.

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
| `column ... does not exist` o errores raros de columnas | La base quedó de otra rama. Corre `python manage.py check_db` y sigue la guía §14.8.1. |

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
│   ├── dashboard/          # KPIs, bonos, capacitación (Módulo 3)
│   └── api/                # API REST + Swagger (docs/03)
├── templates/              # base.html (paquete de diseño)
├── static/css/theme.css    # estilos compartidos (paquete de diseño)
├── data/seed/              # dataset JSON de demo (US-04)
├── postgresql/             # docker-compose.yml + .env.example del contenedor
├── SG-Prod_diseno/         # paquete de diseño original y guía de estilo
└── docs/                   # guías del ambiente, alcance y pruebas por historia
```

---

## 9. API REST y Swagger

El proyecto expone una API REST de solo lectura (empleados, estaciones, matriz de
habilidades, calidad y KPIs) más un `POST` para la matriz, documentada con
OpenAPI 3. La interfaz interactiva vive en `/api/docs/`.

```bash
python manage.py runserver
# abre http://127.0.0.1:8000/api/docs/  (inicia sesión antes en /admin/)
```

> Las colecciones requieren un **usuario de Django** (`User`), no el login de
> planta. El PIN de los empleados nunca se devuelve por la API.

- Rutas: `/api/docs/` (Swagger UI) · `/api/redoc/` · `/api/schema/`
- Guía completa, autenticación y cómo documentar endpoints nuevos:
  [docs/03_guia_api_swagger.md](docs/03_guia_api_swagger.md).
- Se usa [`drf-spectacular`](https://drf-spectacular.readthedocs.io/), no
  `django-rest-swagger`: ese último está archivado y no corre en Django 5.2
  (explicación en la [§0 de la guía](docs/03_guia_api_swagger.md#0-antes-de-empezar-por-qué-no-django-rest-swagger)).

