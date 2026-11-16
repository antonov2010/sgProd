# SG-Prod · Guía de configuración del ambiente de desarrollo

**Proyecto:** SG-Prod — Tablero de mando gerencial para piso de manufactura
**Stack:** Python 3.12/3.13 · Django 5.2 LTS · PostgreSQL en contenedor Docker **local, uno por persona** · virtualenv + pip
**Equipo:** 7 personas (Rocío, Martha, Eduardo, Ángela, Karen, Mariana, Iván) — perfiles junior
**Tiempo disponible:** 10 semanas / 5 sprints (ver sección C del documento de ideas)
**Sprint responsable de esta guía:** Sprint 1 (Sem 1–2) — *Bases & Autenticación*
**Tiempo estimado de ejecución completa:** 60–90 min por persona (hacerlo en parejas, ver §13)

> **Objetivo de esta guía:** que cada integrante tenga el mismo ambiente local funcionando —PostgreSQL propia en Docker, Django conectado, migraciones aplicadas y Admin accesible—. Al terminar el §10 todas y todos deben ver la misma pantalla, **sin depender de nadie más para tener base de datos**.

---

## 0. Resumen del flujo (para imprimir o pegar en el pizarrón)

```
1. Requisitos previos (Python 3.12/3.13, git, Docker)
   Windows 11: instalar Python 3.12, git y Docker Desktop (§1.2 y §1.3)
2. Clonar el repositorio
3. Crear el virtualenv                 -> python -m venv .venv
4. Activar el virtualenv               -> source .venv/bin/activate  |  .\.venv\Scripts\Activate.ps1
5. Actualizar pip
6. Instalar dependencias               -> pip install -r requirements/dev.txt
7. Crear los dos .env                 -> postgresql/.env y el .env de Django
8. Levantar PostgreSQL en Docker       -> cd postgresql && docker compose up -d
9. Verificar la conexión a la BD       -> python manage.py check --database default
10. Migrar, revisar la BD y crear superusuario -> migrate / check_db / createsuperuser
11. Levantar el servidor y validar     -> runserver + /admin/
12. Equivalencias de comandos          -> Windows 11 (PowerShell) <-> Linux / macOS
13. Reparto de responsabilidades y acuerdos de equipo
14. Problemas comunes y how to solve them
15. Referencia rápida del día a día
16. Siguientes pasos (historias de usuario)
```
**Regla de oro 1:** nunca instalar paquetes con `pip install` *fuera* del virtualenv. Si el prompt no muestra `(.venv)`, el virtualenv no está activo.

**Regla de oro 2:** la base de datos es **personal e intransferible**. Cada quien levanta su propio contenedor en su máquina; nadie depende de la base de otra persona y nadie más puede romper la tuya.

### 0.1 Cómo leer esta guía según tu sistema operativo

La guía es **multiplataforma**: Windows 11 (PowerShell), Linux y macOS. Los bloques de código incluyen el equivalente para cada sistema.

| Convención | Significado |
| :---- | :---- |
| Bloque `bash` | Terminal de Linux, macOS o Git Bash |
| Bloque `powershell` | **Windows 11 → PowerShell** (no CMD) |
| Comentario `# PowerShell:` | Línea alternativa dentro de un bloque `bash` |
| `python3` | En Windows suele ser `python` o `py -3.12` (ver §1.2) |

> **Windows 11: usen PowerShell**, no el Símbolo del sistema (CMD). PowerShell es la terminal por defecto de Windows 11 y todos los comandos de esta guía están probados con ella. Anclar PowerShell a la barra de tareas y abrirlo con clic derecho → **Ejecutar como administrador** solo cuando se indique.

**Ruta rápida si estás en Windows 11:**

```text
§1.2 Instalar Python 3.12 + git        (winget o instalador oficial)
§1.3 Instalar Docker Desktop (WSL 2)
§3   python -m venv .venv
§4   .\.venv\Scripts\Activate.ps1      (si falla: §14.13)
§6.3 python -m pip install -r requirements/dev.txt
§7.4 Copy-Item .env.example .env       (en la raíz y en postgresql\)
§8.2 cd postgresql, docker compose up -d (con Docker Desktop abierto)
§9   python manage.py migrate
§12  Tabla de equivalencias de comandos
§14  Problemas comunes (la mayoría son de Windows: 14.13 a 14.16)
```

---

## 1. Requisitos previos

| Herramienta | Versión requerida | Cómo verificar (Linux/macOS) | Cómo verificar (Windows 11 + PowerShell) |
| :---- | :---- | :---- | :---- |
| Python | **3.12 o 3.13** | `python3 --version` | `py -0p` y `python --version` |
| pip | el que trae Python | `python3 -m pip --version` | `python -m pip --version` |
| virtualenv/venv | incluido en Python | `python3 -m venv --help` | `python -m venv --help` |
| git | 2.30+ | `git --version` | `git --version` |
| Docker + Compose v2 | 24+ / v2 | `docker --version`, `docker compose version` | Igual (Docker Desktop, §1.3) |
| Cliente PostgreSQL | 15+ | `psql --version` | Opcional (`psql --version` si instalaron el cliente) |
| Editor | VS Code (recomendado) | — | Extensiones: Python, Pylance, Ruff, Docker |

> ⚠️ **Advertencia importante sobre la versión de Python.**
> Django 5.2 LTS soporta oficialmente Python **3.10 a 3.13**. Si en la máquina hay Python 3.14 (o superior), Django y `psycopg` pueden fallar al instalar o al arrancar. **Todo el equipo debe usar la misma versión menor**: se acuerda **Python 3.12** como versión oficial del proyecto.
> Si no tienen 3.12 en el sistema, instálenlo con el gestor de su distribución (Linux), con el instalador oficial (Windows, §1.2) o con `pyenv` (macOS/Linux) — ver §14.1. No sigan adelante con 3.14.

### 1.1 Docker: qué se necesita y qué no

Cada integrante corre **su propia** PostgreSQL en un contenedor. No hay servidor compartido, no hay credenciales que pedirle a nadie y no hay riesgo de pisar los datos de otra persona.

El contenedor **ya está definido en el repositorio**, no hay que inventarlo:

| Archivo | Qué contiene |
| :---- | :---- |
| [`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>) | PostgreSQL + **pgAdmin** (interfaz web para ver la base) |
| [`postgresql/.env.example`](<postgresql/.env.example>) | Plantilla de las variables que ese compose necesita |

```bash
# Verificar que Docker está instalado y funcionando (Linux/macOS)
docker --version
docker compose version
docker run --rm hello-world     # si esto falla, Docker no está listo
```

```powershell
# Windows 11 (PowerShell) — idéntico, la diferencia es que Docker Desktop debe estar abierto
docker --version
docker compose version
docker run --rm hello-world
```

En Linux, si `docker` marca error de permisos, agreguen su usuario al grupo:

```bash
sudo usermod -aG docker $USER
# Cerrar sesión y volver a entrar (o: newgrp docker)
```

> **Anécdota frecuente:** en algunas máquinas el puerto **5432 ya está ocupado** por otra instalación de PostgreSQL. En ese caso cada quien debe elegir **un puerto distinto** para su contenedor (por ejemplo 5432, 5433, 5434…). Eso se define en [`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>) y en el `.env` de Django; el instructivo está en §8.2 y §14.3.

### 1.2 Windows 11: instalar Python 3.12 y git (PowerShell)

El equipo de Windows no puede usar el `python3` del sistema: Windows no trae Python. Se instala **3.12** explícitamente.

**Opción A — Instalador oficial (recomendada para juniors):**

1. Descargar de <https://www.python.org/downloads/release/python-3127/> el instalador *Windows installer (64-bit)*.
2. En la **primera pantalla** marcar:
   - ☑ **Add python.exe to PATH** ← crítico, sin esto nada funciona
   - ☑ **Use admin privileges when installing py.exe**
3. Clic en *Install Now* y esperar.
4. **Cerrar y reabrir PowerShell** (las variables de PATH no se refrescan solas).

**Opción B — Con `winget` (más rápido si ya lo tienen):**

```powershell
# Un solo comando; abrir PowerShell como administrador
winget install --id Python.Python.3.12 --source winget

# git, si no lo tienen
winget install --id Git.Git --source winget
```

**Verificación (obligatoria antes de seguir):**

```powershell
# Ver todas las versiones de Python instaladas y su ruta
py -0p

# Confirmar la versión que se usará
python --version          # debe decir Python 3.12.x
py -3.12 --version

# git
git --version
```

Salida esperada de `py -0p`:

```text
 -V:3.12 *        C:\Users\tu-usuario\AppData\Local\Programs\Python\Python312\python.exe
```

> **Si `python --version` responde 3.14 o abre la Microsoft Store:** es el alias falso de Windows. Solución en §14.14.
> **Regla práctica:** a partir de aquí, donde la guía diga `python3`, escriban `python` en PowerShell.

### 1.3 Windows 11: instalar Docker Desktop

1. Descargar **Docker Desktop for Windows**: <https://www.docker.com/products/docker-desktop/>
2. Requisitos: **WSL 2** activo y virtualización habilitada en la BIOS/UEFI.
3. Durante la instalación, dejar marcada la opción **Use WSL 2 instead of Hyper-V**.
4. Reiniciar la computadora cuando lo pida.
5. Abrir **Docker Desktop** y esperar a que el ícono de la ballena deje de estar gris o animado. **El motor de Docker solo funciona mientras Docker Desktop esté abierto.**
6. En *Settings → General*, activar **Start Docker Desktop when you sign in to your computer** para no olvidarlo cada mañana.

```powershell
# Verificar WSL 2 (si falta, instalar con el comando de la derecha)
wsl --version
wsl --status

# Instalar/actualizar WSL 2 si hace falta (PowerShell como administrador)
wsl --install
wsl --update
```

```powershell
# Verificar que el motor responde
docker --version
docker compose version
docker run --rm hello-world
```

> **Nota para Windows 11 Home:** funciona igual, siempre que sea versión 22H2 o superior y con WSL 2.
> **Laptops de la planta con VPN corporativa:** algunas VPN rompen la red de Docker. Si `docker run hello-world` falla solo cuando la VPN está conectada, avisen al canal del equipo (hay solución: cambiar el DNS de Docker Desktop a `8.8.8.8`).

---

## 2. Clonar el repositorio

```bash
# Sustituyan <url-del-repo> por la URL real que les comparta Rocío
git clone <url-del-repo> sg-prod
cd sg-prod
```

**Convención de ramas (acuerdo de equipo, no negociable):**

- `main` → solo código que ya pasó revisión y funciona. Nadie hace push directo.
- `dev` → rama de integración del sprint; aquí se juntan las tareas terminadas.
- `feat/rf-1-2-skill-matrix`, `fix/login-qr-pin`, `docs/guia-ambiente` → ramas de trabajo, **una por historia de usuario**.
- Flujo: `git switch dev` → `git pull` → `git switch -c feat/mi-historia` → trabajar → `git push` → Pull Request hacia `dev` → revisión de otra persona → merge.

---

## 3. Crear el virtualenv

Un virtualenv es una carpeta con una copia aislada de Python y sus paquetes. **No se sube a git.**

```bash
# Linux / macOS / Git Bash — desde la raíz del proyecto
python3 -m venv .venv
```

```powershell
# Windows 11 (PowerShell) — desde la raíz del proyecto
python -m venv .venv

# Alternativa si tienen varias versiones instaladas y quieren forzar 3.12:
py -3.12 -m venv .venv
```

- Se crea la carpeta `.venv/` en la raíz del repositorio.
- Un solo virtualenv por proyecto. Nunca dentro de otra carpeta como `src/`.
- En Windows, `Get-ChildItem -Force` debe mostrar `.venv` y dentro existir `.venv\Scripts\` (en Linux/macOS la ruta interna es `.venv/bin/`).

**Alternativa (solo si `venv` falla):** `python3 -m virtualenv .venv` (Linux/macOS) o `python -m virtualenv .venv` (Windows), con `pip install virtualenv` a nivel de usuario. Con Python 3.12 `venv` es suficiente.

---

## 4. Activar el virtualenv

El comando depende del sistema operativo. **Debe repetirse cada vez que abran una terminal nueva.**

| Sistema | Activar | Desactivar |
| :---- | :---- | :---- |
| **Windows 11 + PowerShell** | `.\.venv\Scripts\Activate.ps1` | `deactivate` |
| Windows 11 + CMD | `.venv\Scripts\activate.bat` | `deactivate` |
| Git Bash en Windows | `source .venv/Scripts/activate` | `deactivate` |
| Linux / macOS (bash, zsh) | `source .venv/bin/activate` | `deactivate` |

```powershell
# Windows 11 (PowerShell), desde la raíz del proyecto
.\.venv\Scripts\Activate.ps1
```

> ⚠️ **En PowerShell la barra invertida y el punto inicial importan.** `.\.venv\Scripts\Activate.ps1` sí funciona; `.venv\Scripts\Activate.ps1` **no**, porque PowerShell no ejecuta rutas relativas sin anteponer `.\`.
> Si aparece *"no se puede cargar el archivo porque la ejecución de scripts está deshabilitada"*, ver §14.13.

**¿Cómo sé que funcionó?** El prompt debe mostrar el nombre del ambiente entre paréntesis:

```bash
(.venv) usuario@equipo:~/sg-prod$        # Linux / macOS / Git Bash
```

```powershell
(.venv) PS C:\Users\tu-usuario\sg-prod>   # Windows 11 PowerShell
```

Verificación explícita (debe apuntar a la carpeta del proyecto, no al sistema):

```bash
# Linux / macOS
which python
python -c "import sys; print(sys.prefix)"
```

```powershell
# Windows 11
Get-Command python | Select-Object -ExpandProperty Source
python -c "import sys; print(sys.prefix)"
```

Salida esperada en Windows:

```text
C:\Users\tu-usuario\sg-prod\.venv\Scripts\python.exe
C:\Users\tu-usuario\sg-prod\.venv
```

Si `sys.prefix` apunta al Python del sistema (`C:\Users\...\Python312`) o a `/usr`, el virtualenv **no** está activo.

> **Atajo de VS Code (todos los sistemas):** `Ctrl+Shift+P` → *Python: Select Interpreter* → elegir el intérprete que dice `./.venv`. VS Code activa el ambiente automáticamente en su terminal integrada.
> Para no escribir la ruta cada día en Windows, agreguen un alias al perfil de PowerShell:
> ```powershell
> # Abrir el perfil: notepad $PROFILE  (si no existe: New-Item -Path $PROFILE -Type File -Force)
> function venv { . .\.venv\Scripts\Activate.ps1 }
> ```
> Después basta escribir `venv` dentro de la carpeta del proyecto.

Para salir: `deactivate` (funciona igual en todos los sistemas).

---

## 5. Actualizar pip y herramientas base

Dentro del virtualenv activo (el comando es idéntico en todos los sistemas; en Windows se usa `python` en lugar de `python3`):

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip --version   # debe responder desde la ruta .venv
```

```powershell
# Windows 11
python -m pip install --upgrade pip setuptools wheel
python -m pip --version
```

En Windows, la ruta de respuesta debe empezar con `C:\Users\...\sg-prod\.venv\`:

---

## 6. Estructura de dependencias e instalación

### 6.1 Estructura de carpetas propuesta

```text
sg-prod/
├── .venv/                     # NO se sube a git
├── .env                       # NO se sube a git · variables de DJANGO (personal de cada quien)
├── .env.example               # SÍ se sube · plantilla de Django
├── .gitignore
├── manage.py
├── postgresql/                # ← YA EXISTE en el repositorio
│   ├── docker-compose.yml     #   PostgreSQL (pgsql) + pgAdmin
│   ├── .env                   #   NO se sube a git · variables del contenedor (cada quien el suyo)
│   ├── .env.example           #   SÍ se sube · plantilla del contenedor
│   ├── db-data/               #   datos de PostgreSQL (NO se sube a git)
│   └── pgadmin-data/          #   datos de pgAdmin (NO se sube a git)
├── requirements/
│   ├── base.txt               # Django, psycopg, etc.
│   ├── dev.txt                # base + herramientas de desarrollo
│   └── prod.txt               # base + gunicorn/whitenoise (Sprint 5)
├── config/                    # proyecto Django (settings, urls, wsgi)
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/                  # autenticación QR/PIN (RNF-1)
│   ├── personal/              # empleados, estaciones, skill matrix (Módulo 1)
│   ├── calidad/               # captura horaria, defectos (Módulo 2)
│   └── dashboard/             # KPIs, bonos, capacitación (Módulo 3)
├── data/seed/                 # dataset JSON de demo (US-04)
├── templates/                 # base.html y pantallas (paquete de Martha)
├── static/                    # css/theme.css (paquete de Martha)
└── docs/                      # esta guía, historias de usuario, MER
```

> **Ojo con los dos `.env`:** hay uno en la **raíz** (lo lee Django) y otro en **`postgresql/`** (lo lee Docker Compose). Son archivos distintos, con variables distintas y **ninguno se sube a git**. El detalle está en el §7.4.

### 6.2 Contenido de los archivos de requirements

`requirements/base.txt`

```txt
Django==5.2.*
psycopg[binary]==3.2.*
django-environ==0.11.*
qrcode[pil]==8.*
Pillow==11.*
```

`requirements/dev.txt`

```txt
-r base.txt
pytest==8.*
pytest-django==4.*
ruff==0.9.*
django-extensions==3.*
```

> **Nota:** no se usa `psycopg2-binary`; el driver oficial actual es **psycopg 3**, que es el que Django 5.x recomienda.

### 6.3 Instalar

```bash
# Linux / macOS
python -m pip install -r requirements/dev.txt
python -m pip list        # verificar Django, psycopg, pytest, ruff
python -m django --version
```

```powershell
# Windows 11 (PowerShell) — idéntico; cambia solo el nombre del ejecutable
python -m pip install -r requirements/dev.txt
python -m pip list
python -m django --version
```

> **Si `psycopg` falla al compilar en Windows** (raro, porque usamos la rueda binaria `psycopg[binary]`), ver §14.12. No instalen Visual Studio Build Tools: primero revisen que estén usando `psycopg[binary]` y Python 3.12 de 64 bits.

**Regla de equipo:** si alguien necesita una librería nueva, la agrega a `requirements/`, la instala, y avisa por el canal del equipo. Así nadie se queda con un ambiente incompleto.

---

## 7. Variables de entorno: los dos `.env` del proyecto

**Nunca** se escriben credenciales en `settings.py` ni se suben al repositorio.

En este proyecto hay **dos** archivos `.env`, y esta es la confusión número uno del equipo:

| Archivo | Quién lo lee | Para qué sirve |
| :---- | :---- | :---- |
| `sg-prod/.env` | **Django** (vía `django-environ`) | Cómo conectarse a la base desde Python |
| `sg-prod/postgresql/.env` | **Docker Compose** | Cómo se crea el contenedor de PostgreSQL y pgAdmin |

Los dos deben ser **coherentes entre sí**: el usuario y la contraseña del contenedor tienen que ser los mismos que Django usa para conectarse. Ver §7.4.

### 7.1 Crear `.env.example` de Django (sí se sube a git)

En la **raíz** del repositorio:

```ini
# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=cambien-esta-llave-en-su-.env-local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL LOCAL (contenedor de postgresql/docker-compose.yml)
# Estos valores DEBEN coincidir con los de postgresql/.env
DB_NAME=sgprod_dev_tunombre
DB_USER=sgprod
DB_PASSWORD=sgprod_dev_pass
DB_HOST=127.0.0.1
DB_PORT=5432
DB_CONN_MAX_AGE=60

# Zona horaria de planta
TZ=America/Tijuana
```

> El `.env.example` **no lleva secretos reales**: es la plantilla que se versiona. Los valores de este proyecto son de desarrollo local, así que pueden ser visibles sin problema; aun así, el `.env` de cada persona no se sube (ver §7.3).

### 7.2 Crear el `.env` de Django

```bash
# Linux / macOS / Git Bash
cp .env.example .env
```

```powershell
# Windows 11 (PowerShell)
Copy-Item .env.example .env

# Para editarlo rápido:
notepad .env
# o, si tienen VS Code instalado:
code .env
```

En ambos casos: cambiar `DB_NAME` y, si el 5432 está ocupado, `DB_PORT`. **Guardar el archivo en UTF-8** (Notepad de Windows 11 lo hace por defecto).

Reglas de personalización:

| Variable | Regla |
| :---- | :---- |
| `DB_NAME` | **Único por persona**: `sgprod_dev_rocio`, `sgprod_dev_angela`, `sgprod_dev_ivan`… |
| `DB_PORT` | **Único por persona si hay choque**: 5432, 5433, 5434… debe coincidir con el `docker-compose.yml` |
| `DB_USER`, `DB_PASSWORD` | Deben ser **idénticos** a `DB_USR` y `DB_PWD` de `postgresql/.env` (ojo con los nombres) |
| `DJANGO_SECRET_KEY` | **Distinta por persona**, generada con el comando de abajo |

Generar una `SECRET_KEY` distinta por persona:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

### 7.3 `.gitignore` (crear si no existe)

```gitignore
.venv/
.env                 # el .env de Django (raíz)
*.pyc
__pycache__/
*.sqlite3
staticfiles/
.pytest_cache/
.ruff_cache/
media/

# Datos y secretos del contenedor de PostgreSQL
postgresql/.env
postgresql/db-data/
postgresql/pgadmin-data/
```

> **Urgente:** `postgresql/db-data/` puede llegar a pesar cientos de MB y contiene la base completa. Si alguien lo sube por accidente, el repositorio se vuelve inmanejable para los 7.

Verificar que **ambos** `.env` estén ignorados:

```bash
git check-ignore -v .env postgresql/.env
git check-ignore -v postgresql/db-data/
```

Debe imprimir una regla de `.gitignore` para cada uno. Si no imprime nada, ese archivo **sí se va a subir** y hay que corregir el `.gitignore` antes de hacer `git add`.

### 7.4 Cómo se relacionan los dos `.env` (leer con atención)

El compose de [`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>) usa **otros nombres** de variable que Django:

| `postgresql/.env` (Docker) | `/.env` (Django) | Valor de ejemplo | Regla |
| :---- | :---- | :---- | :---- |
| `POSTGRES_DB` | `DB_NAME` | `sgprod_dev_rocio` | **El mismo nombre de base** |
| `DB_USR` | `DB_USER` | `sgprod` | **El mismo usuario** — cuidado: uno dice `USR` y el otro `USER` |
| `DB_PWD` | `DB_PASSWORD` | `sgprod_dev_pass` | **La misma contraseña** — igual: `PWD` vs `PASSWORD` |
| `PGADMIN_DEFAULT_EMAIL` | — | `tu-correo@ejemplo.com` | Solo pgAdmin |
| `PGADMIN_DEFAULT_PASSWORD` | — | `pgadmin_dev_pass` | Solo pgAdmin |

Así se ve el `postgresql/.env` de cada persona:

```ini
# PostgreSQL Environment Variables
POSTGRES_DB=sgprod_dev_tunombre
DB_USR=sgprod
DB_PWD=sgprod_dev_pass

# PGADMIN Environment Variables
PGADMIN_DEFAULT_EMAIL=tu-correo@ejemplo.com
PGADMIN_DEFAULT_PASSWORD=pgadmin_dev_pass
```

```bash
# Linux / macOS / Git Bash — crear el .env del contenedor
cd postgresql
cp .env.example .env
cd ..
```

```powershell
# Windows 11 (PowerShell)
Set-Location postgresql
Copy-Item .env.example .env
Set-Location ..
```

> **Regla de oro para no enloquecer:** si cambian un valor en `postgresql/.env`, cámbienlo también en el `.env` de la raíz (y viceversa). `POSTGRES_DB` ↔ `DB_NAME`, `DB_USR` ↔ `DB_USER`, `DB_PWD` ↔ `DB_PASSWORD`.
> **Importante:** Docker Compose **lee el `.env` al crear el contenedor**. Si cambian `postgresql/.env` después de haber arrancado, el cambio de usuario o contraseña **no se aplica** al contenedor existente: hay que recrearlo (§14.9).

---

## 8. PostgreSQL local en Docker (una por persona) y conexión desde Django

Cada integrante levanta **su propia** PostgreSQL con Docker en su computadora. No hay base compartida ni credenciales que pedir: el `docker-compose.yml` **ya está en el repositorio** y es igual para todos; lo único que cambia por persona es la base de datos (`POSTGRES_DB` / `DB_NAME`).

### 8.1 El `docker-compose.yml` del repositorio (ya existe, no lo creen)

**No hay que escribir este archivo.** Ya está versionado en [`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>) y trae dos servicios: **PostgreSQL** y **pgAdmin**.

```yaml
services:
  db:
    container_name: pgsql
    image: postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${DB_USR}
      POSTGRES_PASSWORD: ${DB_PWD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - ./db-data:/var/lib/postgresql
    command:
      - "postgres"
      - "-c"
      - "ssl=on"
      - "-c"
      - "ssl_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem"
      - "-c"
      - "ssl_key_file=/etc/ssl/private/ssl-cert-snakeoil.key"
      - "-c"
      - "max_connections=100"
      - "-c"
      - "shared_buffers=256MB"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USR} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  pgadmin:
    image: dpage/pgadmin4:8
    container_name: pgadmin
    restart: unless-stopped
    ports:
      - "8888:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_DEFAULT_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_DEFAULT_PASSWORD}
      PGADMIN_CONFIG_SERVER_MODE: "False"
      PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED: "False"
    volumes:
      - ./pgadmin-data:/var/lib/pgadmin
```

Cosas que deben saber de este archivo antes de tocarlo:

| Detalle | Qué significa para nosotros |
| :---- | :---- |
| `container_name: pgsql` | El contenedor se llama `pgsql`. Los comandos `docker exec` pueden usar ese nombre: `docker exec -it pgsql psql -U sgprod -d sgprod_dev` |
| `image: postgres` (**sin versión**) | Cada quien puede bajar una versión distinta. **Recomendado fijarla** a `postgres:16-alpine` para que los 7 tengamos la misma (ver §8.7) |
| `volumes: ./db-data:/var/lib/postgresql` | **Los datos viven en la carpeta del repositorio**, no en un volumen de Docker. Por eso `postgresql/db-data/` **tiene que estar en `.gitignore`** (§7.3) |
| `ssl=on` + certificados *snakeoil* | Configuración traída de una instalación de Debian. Si el contenedor falla al arrancar con un error de certificados, ver §14.17 |
| `ports: "5432:5432"` | Puerto fijo. Si ya está ocupado, se edita **aquí** (columna izquierda) y se ajusta `DB_PORT` en el `.env` de Django, §14.3 |
| `${POSTGRES_DB}`, `${DB_USR}`, `${DB_PWD}` | Se leen de `postgresql/.env`, que **cada quien debe crear** a partir de `postgresql/.env.example` (§7.4) |
| Servicio `pgadmin` | Interfaz web para ver tablas y datos sin `psql`: <http://localhost:8888> |

> **Windows:** este archivo debe conservar finales de línea **LF**. Si lo editan con Notepad, verifiquen que la barra inferior diga `Unix (LF)`. Además, configuren git una vez:
> ```powershell
> git config --global core.autocrlf input
> ```
> Motivo: un `docker-compose.yml` con CRLF rompe Docker.

### 8.2 Levantar la base de datos

**Todos los comandos se ejecutan desde la carpeta `postgresql/`**, porque ahí está el compose:

```bash
# Linux / macOS / Git Bash
cd postgresql
docker compose up -d             # levanta PostgreSQL y pgAdmin
docker compose ps                # ¿están healthy/running?
docker compose logs -f db        # ver qué pasa si no arranca (Ctrl+C para salir)
```

```powershell
# Windows 11 (PowerShell) — primero: ¿Docker Desktop está abierto?
Set-Location postgresql
docker compose up -d
docker compose ps
docker compose logs -f db
```

Salida esperada de `docker compose ps` (ojo: `start_period: 40s`, así que el `healthy` tarda):

```text
NAME      IMAGE             COMMAND                  SERVICE   STATUS                        PORTS
pgsql     postgres          "docker-entrypoint.s…"   db        Up 30 seconds (health: starting)   0.0.0.0:5432->5432/tcp
pgadmin   dpage/pgadmin4:8  "/entrypoint.sh"         pgadmin   Up 30 seconds                 0.0.0.0:8888->80/tcp
```

Esperen a que `pgsql` diga `(healthy)`. Mientras diga `(health: starting)` es normal.

> **Alternativa sin `cd`:** desde la raíz del repositorio también funciona:
> ```bash
> docker compose -f postgresql/docker-compose.yml up -d
> ```
> En ese caso Docker toma el `.env` y las rutas relativas (`./db-data`) a partir de la carpeta del compose, así que los datos caen en el lugar correcto. **Aun así, esta guía usa siempre `cd postgresql`** porque además de ser más corto, evita confusiones entre los dos `.env`.
>
> **El `healthy` tarda:** el compose tiene `interval: 30s` y `start_period: 40s`. Es normal que al principio `docker compose ps` muestre `(health: starting)`; no arranquen Django hasta ver `(healthy)`.

Verificación de que responde (evita depender de tener `psql` instalado en Windows):

```bash
# Con el nombre del contenedor (funciona desde cualquier carpeta)
docker exec -it pgsql psql -U sgprod -d sgprod_dev_tunombre -c "SELECT version();"
```

> El usuario y la base deben ser **los de su `postgresql/.env`** (`DB_USR` y `POSTGRES_DB`). Si aún no lo han creado, este comando fallará: ver §7.4.

> **Si en Windows ven el error `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`**, Docker Desktop no está corriendo o todavía está arrancando. Ábranlo y esperen a que el ícono esté estable; luego repitan el comando.

### 8.3 Crear la base de datos personal

El contenedor crea **una sola** base, la que diga `POSTGRES_DB` en `postgresql/.env`. Como cada persona tiene su propio contenedor, lo más simple es que **`POSTGRES_DB` sea ya su base personal** y no crear nada extra:

```ini
# postgresql/.env
POSTGRES_DB=sgprod_dev_tunombre
```

Y en el `.env` de Django, el mismo nombre:

```ini
# .env (raíz)
DB_NAME=sgprod_dev_tunombre
```

> **Excepción útil:** si crean una base adicional para otra rama (por ejemplo,
> `sgprod_dev_ui`), el contenedor ya creó la base de `POSTGRES_DB` y **no hace
> falta cambiarla**. Solo apunten `DB_NAME` a la base nueva. La regla de que
> ambos nombres coincidan aplica a la base inicial del contenedor, no impide
> tener bases separadas para ramas con modelos distintos.

Si en cambio prefieren una base por proyecto/sprint sobre el mismo contenedor, se crea así:

```bash
# Linux / macOS / Git Bash
docker exec -it pgsql psql -U sgprod -d postgres -c "CREATE DATABASE sgprod_dev_tunombre;"

# O con docker compose, desde la carpeta postgresql/
docker compose exec db psql -U sgprod -d postgres -c "CREATE DATABASE sgprod_dev_tunombre;"
```

```powershell
# Windows 11 (PowerShell) — una sola línea, sin continuaciones
docker exec -it pgsql psql -U sgprod -d postgres -c "CREATE DATABASE sgprod_dev_tunombre;"
```

> **Windows + Git Bash:** si `docker exec -it` responde *"the input device is not a TTY"*, quiten la `-t`: `docker exec -i pgsql psql ...`.

Comandos útiles de `psql` dentro del contenedor:

```bash
docker exec -it pgsql psql -U sgprod -d sgprod_dev -c "\l"    # listar bases
docker exec -it pgsql psql -U sgprod -d sgprod_dev            # sesión interactiva (salir con \q)
```

### 8.4 Opcional pero recomendado: pgAdmin

El compose ya incluye **pgAdmin 4** en <http://localhost:8888>. Sirve para inspeccionar tablas, revisar que las migraciones realmente se aplicaron y cargar datos a mano.

1. Abrir <http://localhost:8888> y entrar con `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` de `postgresql/.env`.
2. Clic derecho en *Servers → Register → Server*.
3. Pestaña *General*: nombre `SG-Prod local`.
4. Pestaña *Connection*:
   - Host: **`pgsql`** (nombre del contenedor; **no** `localhost`, porque pgAdmin vive dentro de la red de Docker)
   - Port: `5432`
   - Maintenance database: `postgres`
   - Username: el `DB_USR` de su `postgresql/.env`
   - Password: el `DB_PWD` de su `postgresql/.env`
5. *Save*. Ya pueden ver las bases y tablas.

> **Error típico:** si en *Host* ponen `localhost`, pgAdmin busca la base **dentro de su propio contenedor** y falla con *"could not connect to server"*. Debe ser `pgsql`.

### 8.5 Crear el proyecto y las apps

```bash
# Linux / macOS / Git Bash
django-admin startproject config .

mkdir -p apps && touch apps/__init__.py

python manage.py startapp core apps/core
python manage.py startapp personal apps/personal
python manage.py startapp calidad apps/calidad
python manage.py startapp dashboard apps/dashboard
```

```powershell
# Windows 11 (PowerShell) — ojo: mkdir y el archivo vacío se hacen distinto
django-admin startproject config .

New-Item -ItemType Directory -Path apps -Force | Out-Null
New-Item -ItemType File -Path apps\__init__.py -Force | Out-Null

python manage.py startapp core apps/core
python manage.py startapp personal apps/personal
python manage.py startapp calidad apps/calidad
python manage.py startapp dashboard apps/dashboard
```

> **Windows:** `django-admin` debe existir en el virtualenv activo. Si PowerShell responde *"no se reconoce el término 'django-admin'"*, usen la forma larga: `python -m django startproject config .`

Al terminar, en el `apps.py` de cada app ajusten el nombre para que coincida con la ruta:

```python
class PersonalConfig(AppConfig):
    name = "apps.personal"      # no solo "personal"
```

> Esto se hace **una sola vez**, y quien lo haga avisa al equipo antes de tocar la estructura: si alguien crea las apps en otra ruta, los `INSTALLED_APPS` y las migraciones se rompen para todos.

### 8.6 Ajustes mínimos en `config/settings/base.py`

```python
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    # ... apps de Django ...
    "django_extensions",
    "apps.core",
    "apps.personal",
    "apps.calidad",
    "apps.dashboard",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}

LANGUAGE_CODE = "es-mx"
TIME_ZONE = env("TZ", default="America/Tijuana")
USE_TZ = True

TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]      # paquete de diseño de Martha
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_URL = "static/"
```

### 8.7 Dos mejoras recomendadas al compose (acordar en equipo antes de tocar)

Estos dos cambios **no son obligatorios para arrancar**, pero conviene decidirlos en el Sprint 1 y hacerlos en **un solo PR** para que los 7 tengan el mismo entorno.

**1. Fijar la versión de PostgreSQL.** El archivo dice `image: postgres`, que significa *la última versión disponible en el momento en que cada quien haga `pull`*. Eso garantiza diferencias entre máquinas (una persona tendrá 17, otra 16) y errores del tipo *"a mí sí me funciona"*:

```yaml
  db:
    # image: postgres          # antes
    image: postgres:16-alpine  # después: misma versión para todo el equipo
```

**2. Confirmar que SSL funciona en el contenedor.** El compose arranca PostgreSQL con `ssl=on` y apunta a certificados *snakeoil* (`ssl-cert-snakeoil.pem`), que existen en las imágenes basadas en Debian/Ubuntu pero **pueden no existir** en la imagen oficial `postgres`. Si el contenedor no arranca, ver §14.17. Dos caminos posibles:

- **Quitar SSL** (lo más simple en desarrollo local, porque nunca salimos de `localhost`): eliminar las tres líneas `-c ssl=...` del `command`.
- **Mantener SSL** y montar certificados propios en `/etc/ssl/certs` y `/etc/ssl/private`.

> **No lo cambien cada quien por su cuenta.** Si una persona edita el compose y las otras no, los comandos de la guía dejan de coincidir y el diagnóstico de errores se vuelve adivinanza.

### 8.8 Probar la conexión antes de migrar

Los comandos son iguales en Windows 11, Linux y macOS (en Windows, con Docker Desktop abierto). Si ya hicieron `cd postgresql`, usen `docker compose`; si están en la raíz, usen `docker exec` con el nombre del contenedor:

```bash
# 1) ¿Los contenedores están arriba y sanos? (desde postgresql/)
docker compose ps

# 2) Prueba directa a la base (aísla el problema de Django)
docker exec -it pgsql psql -U sgprod -d sgprod_dev_tunombre -c "SELECT 1;"

# 3) Prueba desde Django (desde la raíz del repositorio)
python manage.py check --database default
```

Interpretación de resultados:

| Síntoma | Dónde está el problema |
| :---- | :---- |
| (1) y (2) fallan | Docker apagado, puerto ocupado o contenedor mal configurado |
| (1) y (2) funcionan, (3) falla | El `.env` de Django (nombre de base, puerto, usuario) o `DJANGO_SETTINGS_MODULE` |
| (2) funciona y (3) falla con *"password authentication failed"* | El `.env` de la raíz no coincide con `postgresql/.env` (§7.4) |
| Todo funciona pero el `runserver` viejo no ve los cambios | Reinicien el servidor: el `.env` se lee solo al arrancar |
| En Windows: `check` falla con `Name or service not known` | En el `.env`, `DB_HOST` debe ser `127.0.0.1`, **no** `localhost` (IPv6) ni `pgsql` |

---

## 9. Migraciones, superusuario y arranque

Antes de migrar, confirmen que **su** contenedor está arriba (`docker compose ps` debe mostrar `healthy`). Las migraciones se aplican a la base de su máquina, no a la de nadie más.

```bash
# Linux / macOS / Git Bash
python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser      # con su correo y una contraseña conocida
python manage.py runserver
```

```powershell
# Windows 11 (PowerShell) — idéntico
python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser
python manage.py runserver
```

> **Windows:** si PowerShell bloquea la ejecución de `manage.py` por la política de scripts, no pasa nada: el comando correcto siempre es `python manage.py ...` (que es el que usamos). El problema de la *ExecutionPolicy* solo aparece al activar el virtualenv (§14.13).
>
> **Al terminar el día:** `Ctrl+C` para detener el servidor y, desde `postgresql/`, `docker compose stop` para liberar memoria y batería. Los datos quedan guardados en `postgresql/db-data/`.

Validación final: abrir <http://127.0.0.1:8000/admin/> e iniciar sesión.

**Sugerencia de higiene (no obligatoria en Sprint 1):** para no mezclar cambios de modelos entre 7 personas, antes de `makemigrations` hagan `git pull` de `dev`, y suban las migraciones **en el mismo commit** que el cambio del modelo. Recuerden que cada quien tiene su propia base: si alguien más agrega una migración, ustedes solo necesitan `git pull` + `python manage.py migrate` en su contenedor.

### 9.1 Revisar que la base coincide con la rama

> **Para un clon nuevo no hace falta crear una base extra.** La base personal
> normal (§8.3) es suficiente: `migrate`, `check_db` y, si quieren demo,
> `seed_demo --reset`. La opción de una base nueva (§14.8.1) solo aplica si la
> base actual ya quedó con el esquema de otra rama o si quieren conservarla
> mientras prueban una rama con modelos incompatibles.

Antes de investigar un error raro, ejecuten este diagnóstico de **solo lectura** desde la raíz:

```bash
python manage.py check_db
```

El comando revisa:

1. que existan las tablas de `personal`, `calidad` y `dashboard`;
2. que cada tabla tenga las columnas que esperan los modelos actuales;
3. que no haya migraciones aplicadas por otra rama que ya no existe en este checkout;
4. que no queden migraciones pendientes;
5. cuántos datos de demo hay cargados.

Si todo coincide, termina con `Base sincronizada con esta rama.` y código de salida `0`. Si encuentra un problema, muestra `[ERROR]`, explica qué hacer y termina con código `1`. **No borra ni modifica nada.**

La regla del equipo es simple: **una base corresponde a una rama con modelos compatibles**. Si cambias de una rama con modelos/migraciones distintas, no reutilices la misma base “a ver si funciona”; crea una base nueva o reinicia su esquema. El procedimiento está en §14.8.1.

### 9.2 Cargar los datos de demo

Después de migrar una base limpia, el escenario de demo se carga con:

```bash
python manage.py seed_demo --reset
```

Carga 5 líneas, 40 estaciones, 200 empleados, metas, defectos y matriz de habilidades desde [`data/seed/demo_sgprod.json`](<../data/seed/demo_sgprod.json>). El comando imprime las credenciales; el PIN es `123456`.

Para la prueba manual de US-15 (elegibles a bono por cero defectos) usa el
escenario completo:

```bash
python manage.py seed_demo --reset --us15
```

Agrega 14 días de asignaciones y registros horarios (560 asignaciones y 4 480
registros), asigna cada línea a su Jefe y cada operador a una línea, y deja
activa una configuración de bono de 14 días. Al terminar imprime los tres casos
por línea: elegible, defecto antiguo y defecto reciente. El paso a paso para
Rocío está en la [guía de prueba manual de US-15](04_guia_pruebas_us15.md).

> **Cuidado:** `--reset` borra **todos los datos de dominio** de la base (no solo los de demo). Úsalo únicamente en tu base local. Sin `--reset`, el comando no elimina los registros que ya existían; para un volumen exacto usa `--reset --empleados N`. `--us15` exige `--reset` para que los casos sean reproducibles.

---

## 10. Checklist de "ambiente listo" (cada persona lo llena y lo reporta)

Aplica igual en Windows 11, Linux y macOS. En Windows, todos los comandos se ejecutan en **PowerShell** con el virtualenv activo (`.\.venv\Scripts\Activate.ps1`).

- [ ] Python 3.12.x (o 3.13.x) confirmado — Windows: `py -0p` y `python --version`
- [ ] `git clone` hecho y rama `dev` actualizada
- [ ] `.venv/` creado y **activo** (el prompt muestra `(.venv)`; la ruta de Python apunta al proyecto)
- [ ] `python -m pip list` muestra Django, psycopg, pytest, ruff
- [ ] `.env` creado en la raíz con **mi** `DB_NAME` personalizado y **no** aparece en `git status`
- [ ] `postgresql/.env` creado a partir de `postgresql/.env.example` y **no** aparece en `git status`
- [ ] `postgresql/.env` y el `.env` de la raíz son **coherentes** (`POSTGRES_DB`↔`DB_NAME`, `DB_USR`↔`DB_USER`, `DB_PWD`↔`DB_PASSWORD`)
- [ ] `postgresql/db-data/` está en `.gitignore` y `git check-ignore -v postgresql/db-data/` lo confirma
- [ ] Windows: `git config --global core.autocrlf input` aplicado
- [ ] Docker instalado y funcionando (`docker run --rm hello-world`); en Windows, Docker Desktop abierto
- [ ] `docker compose up -d` (desde `postgresql/`) levanta `pgsql` y `pgadmin`
- [ ] `docker compose ps` (desde `postgresql/`) muestra `pgsql` como `healthy`
- [ ] `docker exec -it pgsql psql -U <usuario> -d <mi_base> -c "SELECT 1;"` responde
- [ ] (Opcional) pgAdmin abre en <http://localhost:8888> y se conecta a la base con host `pgsql`
- [ ] `python manage.py check` sin errores
- [ ] `python manage.py migrate` aplica sin errores
- [ ] `python manage.py check_db` termina en `Base sincronizada con esta rama.`
- [ ] (Opcional, para demo) `python manage.py seed_demo --reset` carga 200 empleados
- [ ] `runserver` levanta y `/admin/` carga con el superusuario
- [ ] `templates/base.html` y `static/css/theme.css` del paquete de diseño copiados
- [ ] `pytest` corre sin fallos
- [ ] `ruff check .` corre sin errores nuevos

Cuando todo esté marcado, se avisa en el canal del equipo y **se cierra la tarea de Sprint 1 "Entorno Django/PostgreSQL"**.

> **Nota para el reporte:** al avisar en el canal, indiquen su sistema operativo. Con 7 personas es muy probable que haya una mayoría en Windows 11 y una minoría en Linux: los *padrinos de ambiente* (Eduardo e Iván) deben cubrir **ambos** sistemas, no solo el suyo.

---

## 11. Poner en orden el repositorio del equipo

El compose de PostgreSQL **ya existe** ([`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>)), así que el trabajo de infraestructura ya está hecho. Lo que falta es **cerrar los huecos** que hoy impedirían que los 7 trabajen sin pisarse: el `.gitignore`, el `.env.example` de Django y el esqueleto de `config/`.

**Responsables:** Ángela cierra el tema de base de datos y Docker; Iván cierra el tema de entorno. **Tiempo:** 1–2 horas del Sprint 1.

### 11.1 Qué falta crear y quién lo revisa

| Archivo | Estado | Quién | Revisa |
| :---- | :---- | :---- | :---- |
| `postgresql/docker-compose.yml` | **Ya existe** | — | — |
| `postgresql/.env.example` | **Ya existe** | — | — |
| `.gitignore` en la raíz | **Falta** (§7.3) | Iván | Eduardo |
| `.env.example` de Django en la raíz | **Falta** (§7.1) | Iván | Rocío |
| `requirements/base.txt` y `dev.txt` (§6.2) | Falta | Iván | Ángela |
| `config/settings/{base,dev,prod}.py` (§8.6) | Falta | Ángela | Mariana |
| Ajuste de versión/SSL en el compose (§8.7) | **Por decidir en equipo** | Ángela | Karen (en su máquina) |
| `templates/base.html` + `static/css/theme.css` | Falta (Martha ya los tiene) | Martha | Eduardo |
| `README.md` (arranque en 5 líneas) | Falta | Rocío | todo el equipo |

### 11.2 Orden de las operaciones (evita conflictos)

1. **Primero y antes que nada: `.gitignore`.** Si alguien hace `docker compose up` antes de que exista, se crea `postgresql/db-data/` con la base completa dentro del repositorio y corre riesgo de subirse. Es un PR de 10 minutos y desbloquea todo lo demás.
2. Los demás hacen `git pull`, crean sus dos `.env` (§7.2 y §7.4) y levantan su contenedor con `cd postgresql && docker compose up -d`.
3. Ángela crea el esqueleto de `config/` y los `settings` en un PR.
4. Iván agrega `requirements/` y el `.env.example` de Django en otro PR.
5. Martha sube `templates/` y `static/` en un tercer PR.
6. Si el equipo decide fijar la versión de PostgreSQL o quitar SSL (§8.7), va en **un solo PR** y avisando en el canal.
7. **Nadie toca `settings.py`, `models.py` ni el compose sin avisar.**

> **Por qué el orden importa:** si dos personas suben `settings.py` con `INSTALLED_APPS` distintos al mismo tiempo, el merge rompe el arranque para los 7. Mientras que `db-data/` subido por error puede tardar horas en revertirse (hay que reescribir el historial de git).

### 11.3 Definición de "terminado" (Definition of Done) para el Sprint 1

Una tarea del Sprint 1 se considera terminada solo si cumple **todo** esto:

- [ ] El código está en una rama `feat/...` con PR hacia `dev` y **una** revisión aprobada.
- [ ] `python manage.py check` y `python manage.py migrate` corren sin errores en una base vacía (comprobado por alguien más).
- [ ] `ruff check .` sin errores nuevos y `pytest` en verde.
- [ ] Si tocó modelos, las migraciones van **en el mismo PR**.
- [ ] Si agregó variables nuevas, `.env.example` quedó actualizado.
- [ ] El *seeding* de Karen reproduce lo que la pantalla necesita para verse.
- [ ] Rocío registró el acuerdo o la regla de negocio aplicada en `docs/`.

---

## 12. Equivalencias de comandos: Windows 11 (PowerShell) ↔ Linux / macOS

### 12.1 Tabla de equivalencias: resumen en una sola vista

Guarden esta tabla: es la que más se va a consultar durante el Sprint 1.

| Acción | Linux / macOS / Git Bash | Windows 11 + PowerShell |
| :---- | :---- | :---- |
| Intérprete de Python | `python3` | `python` o `py -3.12` |
| Crear virtualenv | `python3 -m venv .venv` | `python -m venv .venv` |
| Activar virtualenv | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Ruta del python del venv | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| Desactivar | `deactivate` | `deactivate` |
| Ver qué python se usa | `which python` | `Get-Command python \| Select-Object Source` |
| Copiar el `.env` | `cp .env.example .env` | `Copy-Item .env.example .env` |
| Crear carpeta + archivo | `mkdir -p apps && touch apps/__init__.py` | `New-Item -ItemType Directory apps -Force; New-Item -ItemType File apps\__init__.py -Force` |
| Editar un archivo | `nano .env` | `notepad .env` o `code .env` |
| Variable de entorno temporal | `export TZ=America/Tijuana` | `$env:TZ = "America/Tijuana"` |
| Ver una variable | `echo $DB_PORT` | `$env:DB_PORT` o `echo $env:DB_PORT` |
| Buscar texto en archivos | `grep -rn "DB_NAME" .` | `Select-String -Path .\* -Pattern "DB_NAME" -Recurse` |
| Listar archivos (incl. ocultos) | `ls -la` | `Get-ChildItem -Force` |
| **Cambiar de carpeta** | `cd postgresql` | `Set-Location postgresql` (o `cd postgresql`) |
| **Volver a la raíz** | `cd ..` | `Set-Location ..` (o `cd ..`) |
| Levantar los contenedores | `cd postgresql && docker compose up -d` | `Set-Location postgresql; docker compose up -d` |
| Ver estado de los contenedores | `docker compose ps` | `docker compose ps` |
| Consola SQL | `docker exec -it pgsql psql -U sgprod -d <base>` | Igual (si falla por TTY: quitar `-t`) |
| Ver procesos por puerto | `sudo ss -ltnp \| grep 5432` | `Get-NetTCPConnection -LocalPort 5432 -State Listen` |
| Detener un servicio | `sudo systemctl stop postgresql` | `Stop-Service -Name "postgresql-x64-16"` |
| Borrar una carpeta con datos | `rm -rf db-data` | `Remove-Item -Recurse -Force db-data` |
| Permisos de Docker | `sudo usermod -aG docker $USER` | No aplica: abrir Docker Desktop |
| Continuación de línea | `\` al final | No usar; escribir **una sola línea** |
| Separador de rutas | `/` | `\` (aunque `/` también funciona en Python y git) |

> **Regla para no equivocarse:** en PowerShell las rutas usan `\` y **doble barra** al ejecutar algo del directorio actual (`.\`). Los comandos de `docker`, `git` y `python manage.py` son **idénticos** en todos los sistemas.
>
> **Los dos comandos que más se confunden:** `docker compose up -d` **solo** funciona dentro de `postgresql/`; `python manage.py migrate` **solo** funciona en la raíz del repositorio.

---

## 13. Reparto de responsabilidades (7 personas, tiempo limitado)

El cronograma es de 10 semanas: **no hay tiempo para que cada quien descubra sus errores solo**. Se trabaja en parejas y con *copiloto*.

**Supuesto de partida (cambió respecto al plan original):** cada integrante tiene **su propia PostgreSQL en Docker** en su computadora. Por lo tanto **no existe un servidor compartido, no hay credenciales que distribuir y nadie administra la base de otra persona**. Lo único compartido es el `docker-compose.yml` del repositorio, que es idéntico para todos y se versiona una sola vez.

| Persona | Rol en la configuración del ambiente | Entregable concreto |
| :---- | :---- | :---- |
| **Rocío** | Gestión de información y alineación | **No administra infraestructura.** Redacta y mantiene los acuerdos del equipo en `docs/`; recopila reglas de negocio (bonos, catálogo de defectos, semáforos de calidad); da seguimiento al checklist del §10 y reporta quién falta cada viernes |
| **Ángela** | Base de datos (líder) | **Dueña del `postgresql/docker-compose.yml`**: decide con el equipo si se fija la versión de PostgreSQL y si se mantiene SSL (§8.7); diseña el MER; define `models.py`; **dueña de las migraciones** del Sprint 1; valida que `migrate` corra limpio partiendo de `db-data/` borrada |
| **Karen** | Base de datos (acompañante) | Apoya el MER; escribe el *seeding* de datos de prueba; verifica índices y restricciones; **valida el compose en una máquina distinta a la de Ángela** (si funciona en una y no en la otra, el problema está en el compose) |
| **Martha** | UI/UX (líder) | Integra `base.html`, `theme.css` y `templates/`; deja `STATICFILES_DIRS` y `TEMPLATES` funcionando; define la guía de estilo compartida |
| **Eduardo** | UI/UX + Módulo 1 | Verifica que la plantilla base se extienda correctamente; apoya el arranque de las vistas; **padrino de ambiente** de quien se atore |
| **Mariana** | Módulo 1 (líder) | Configura el Admin de Django; crea el primer modelo de prueba y hace la migración *piloto* del equipo (para que todos vean el flujo completo) |
| **Iván** | Módulo 2 (líder) | Propone la estructura de `requirements/`, `.env.example` y `.gitignore`; valida el rendimiento de la conexión a la BD local (RNF-2); **padrino de ambiente** de quien se atore |

**Reglas de convivencia técnica:**

1. **Una persona dueña de las migraciones por sprint** (Sprint 1: Ángela). Evita colisiones de `000X_*.py` en el repositorio.
2. **Pull Request obligatorio** hacia `dev`, con al menos 1 revisión.
3. **En parejas para instalar el ambiente**: quien ya lo tiene, se sienta con quien no. Meta: **nadie termina la Semana 1 sin ambiente**.
4. **Bloqueo de más de 30 minutos → preguntar al equipo**, no seguir peleando con el error.
5. Todo acuerdo técnico se anota en `docs/`.
6. **La base de datos es personal:** lo que cada quien haga en su contenedor (borrar volumen, recargar *seeding*, romper datos) **no afecta a nadie más**. Para reproducir un problema de otra persona, se reproduce con el *seeding* versionado, no conectándose a su base.
7. **Mezcla de sistemas operativos:** si hay personas en Windows 11 y en Linux, los *padrinos de ambiente* deben ser uno de cada sistema. Un error de rutas o de Docker Desktop en Windows no lo va a reproducir alguien en Linux.

### 13.1 Cómo evitar conflictos al trabajar en paralelo

Como hay 7 personas y 10 semanas, el riesgo real no es la base de datos: es **el repositorio**.

| Riesgo | Mitigación |
| :---- | :---- |
| Dos personas editan el mismo modelo | Una historia de usuario = una rama = un dueño; avisar en el canal antes de tocar `models.py` de un módulo ajeno |
| Migraciones con el mismo número | Solo Ángela genera migraciones en Sprint 1; en sprints siguientes, la persona dueña del módulo avisa antes de `makemigrations` |
| Datos distintos en cada base y "a mí sí me funciona" | El *seeding* (Karen) es la fuente de verdad: `python manage.py seed_demo --reset` debe reproducir el mismo escenario en cualquier máquina |
| Alguien sube su `.env` por accidente | `git check-ignore -v .env` en el checklist del §10; revisión obligatoria en el PR |
| Ambiente desactualizado | Después de cada `git pull`: `python -m pip install -r requirements/dev.txt`, `python manage.py migrate`, `python manage.py check_db` y, si cambió el compose, `cd postgresql && docker compose up -d` |
| Alguien sube `postgresql/db-data/` por error | Verificar `git check-ignore -v postgresql/db-data/` antes del primer `docker compose up`, y revisarlo en el PR |
| Los dos `.env` se desincronizan | Regla del §7.4: `POSTGRES_DB`↔`DB_NAME`, `DB_USR`↔`DB_USER`, `DB_PWD`↔`DB_PASSWORD` siempre iguales |

---

## 14. Problemas comunes (how to solve them)

### 14.1 No tengo Python 3.12

```bash
# Opción A: gestor de paquetes de la distribución (Fedora/RHEL)
sudo dnf install python3.12 python3.12-devel

# Opción B: pyenv (no requiere sudo y permite varias versiones)
curl https://pyenv.run | bash
pyenv install 3.12.7
cd ~/sg-prod && pyenv local 3.12.7
python --version
```

Después, **borren y recreeen el virtualenv** con la versión correcta.

### 14.2 Docker: `Cannot connect to the Docker daemon`

El servicio de Docker no está corriendo o su usuario no tiene permisos.

```bash
# Linux: arrancar el servicio
sudo systemctl start docker
sudo systemctl enable docker      # para que arranque solo

# Permisos (requiere cerrar sesión y volver a entrar)
sudo usermod -aG docker $USER
```

En Windows/macOS: abrir **Docker Desktop** y esperar a que el ícono deje de estar gris.

### 14.3 `port is already allocated` / `bind: address already in use`

Otro programa (u otro PostgreSQL instalado en su máquina) ya usa el **5432**.

```bash
# Linux
sudo ss -ltnp | grep 5432
# macOS
lsof -i :5432

# ¿Es OTRO contenedor viejo?
docker ps -a --filter "publish=5432"
```

```powershell
# Windows 11 (PowerShell) — qué proceso tiene el puerto
Get-NetTCPConnection -LocalPort 5432 -State Listen |
  Select-Object LocalAddress, LocalPort, OwningProcess

# Ver el nombre del programa que lo ocupa
Get-Process -Id (Get-NetTCPConnection -LocalPort 5432 -State Listen).OwningProcess |
  Select-Object Id, ProcessName, Path

# ¿Es otro contenedor viejo?
docker ps -a --filter "publish=5432"
```

**Solución A — usar otro puerto (la más rápida).** Editen [`postgresql/docker-compose.yml`](<postgresql/docker-compose.yml>) y el `.env` de Django en conjunto:

```yaml
    ports:
      - "5433:5432"      # 5433 en tu máquina -> 5432 dentro del contenedor
```

```ini
# .env (raíz)
DB_PORT=5433
```

Luego, desde `postgresql/`: `docker compose up -d` y reinicien `runserver`.

**Solución B — Windows: el culpable suele ser un PostgreSQL instalado como servicio.**

```powershell
# Ver servicios de PostgreSQL instalados
Get-Service -Name "*postgres*"

# Detenerlo (ejemplo: servicio postgresql-x64-16) — PowerShell como administrador
Stop-Service -Name "postgresql-x64-16"

# Que no vuelva a arrancar solo (opcional pero recomendado)
Set-Service -Name "postgresql-x64-16" -StartupType Manual
```

Si no lo usan, también pueden desinstalarlo desde *Configuración → Aplicaciones*. La base del proyecto vive en Docker; no necesitan PostgreSQL nativo en Windows.

**Solución C — liberar el puerto del contenedor viejo:**

```bash
docker ps -a --filter "publish=5432"     # identificar
docker rm -f pgsql                       # eliminar el contenedor pgsql viejo
cd postgresql && docker compose up -d
```

### 14.4 El contenedor arranca y se reinicia en bucle (`docker compose ps` no llega a `healthy`)

```bash
cd postgresql
docker compose logs -f db
```

Causas típicas:

- **Error de certificados SSL** (`ssl-cert-snakeoil.pem` no existe en la imagen) → §14.17.
- `postgresql/.env` no existe o tiene variables vacías (`${POSTGRES_DB}` sin definir).
- La carpeta `db-data/` quedó corrupta o fue creada con otra versión de PostgreSQL → §14.9.
- Falta memoria disponible en la máquina.

### 14.5 `django.db.utils.OperationalError: connection refused`

1. ¿El contenedor está arriba? `docker compose ps` (desde `postgresql/`) debe decir `running` / `healthy`.
2. ¿El puerto del `.env` de Django coincide con el del `docker-compose.yml`?
3. `DB_HOST` debe ser **`127.0.0.1`** (no `pgsql`, no `db`, no `localhost` con IPv6 mal resuelto): Django corre en su máquina, **fuera** de la red de Docker.
4. Prueben la conexión directa: `docker exec -it pgsql psql -U <usuario> -d <tu_base> -c "SELECT 1;"`.
5. Recuerden que el `.env` se lee al arrancar: reinicien `runserver` después de cambiarlo.

### 14.6 `FATAL: database "sgprod_dev_xxx" does not exist`

La base no existe: o `POSTGRES_DB` en `postgresql/.env` tiene un typo, o crearon el contenedor antes de definirlo.

```bash
docker exec -it pgsql psql -U <usuario> -d postgres -c "\l"     # listar bases existentes
docker exec -it pgsql psql -U <usuario> -d postgres -c "CREATE DATABASE sgprod_dev_tunombre;"
```

Si el `POSTGRES_DB` que querían **no** aparece, cambió después de crear el contenedor: Docker solo lo aplica la primera vez → §14.9.

### 14.7 `FATAL: password authentication failed for user "..."`

1. Los dos `.env` no coinciden. Revisen la tabla del §7.4: `DB_USR`↔`DB_USER`, `DB_PWD`↔`DB_PASSWORD`, `POSTGRES_DB`↔`DB_NAME`.
2. **La contraseña del contenedor se fija en `db-data/` la primera vez que arranca.** Si luego la cambian en `postgresql/.env`, no se actualiza sola → §14.9 (nivel 2).
3. Escapado en el `.env` de Django: si la contraseña tiene `#`, espacios o `$`, escríbanla entre comillas dobles: `DB_PASSWORD="mi#pass"`. En el `.env` del compose, **no** usen comillas.

### 14.8 `You have N unapplied migration(s)`

```bash
python manage.py migrate
```

Si persiste, probablemente dos personas generaron migraciones con el mismo número: hagan `git pull`, revisen `git status`, y **consulten a Ángela** antes de borrar nada.

### 14.8.1 Errores de columna al cambiar de rama

Ejemplo real:

```text
psycopg.errors.UndefinedColumn: column calidad_registrocalidadhorario.asignacion_id does not exist
```

o, al abrir el admin/alguna pantalla:

```text
django.db.utils.ProgrammingError: column personal_empleado.pin does not exist
```

**Qué pasó:** tu base fue migrada con otra rama que tenía modelos distintos. Por ejemplo, la rama vieja del MVP aplicó `personal.0003_alineacion_mvp`, `calidad.0002_alineacion_mvp` y `dashboard.0002_alineacion_mvp`. Esas migraciones ya no existen en este checkout, así que `python manage.py migrate` dice *“No planned migration operations”* y no puede corregir las tablas.

Primero confirma el diagnóstico (no modifica nada):

```bash
python manage.py check_db
```

Si reporta columnas faltantes o migraciones de otra rama, tienes dos caminos.

#### Opción A (recomendada): crear una base nueva y conservar la anterior

La base anterior queda intacta; solo cambias `DB_NAME` para este checkout.

```bash
# Crear la base dentro del mismo contenedor. Usa tu usuario de postgresql/.env
docker exec -it pgsql psql -U <usuario> -d postgres -c "CREATE DATABASE sgprod_dev_ui;"

# En el .env de la RAÍZ:
# DB_NAME=sgprod_dev_ui
# POSTGRES_DB no cambia: el contenedor ya creó su base inicial.

python manage.py migrate
python manage.py check_db
python manage.py seed_demo --reset   # opcional, para datos de demo
```

En Windows/PowerShell el comando de Docker es una sola línea, igual que arriba. Si `docker exec -it` dice *“the input device is not a TTY”*, quita la `-t`.

#### Opción B: reiniciar el esquema de la base actual

**Esto borra todos los datos de esa base.** Úsalo solo si no necesitas conservarlos.

```bash
docker exec -it pgsql psql -U <usuario> -d <tu_base> \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

python manage.py migrate
python manage.py check_db
python manage.py seed_demo --reset   # opcional
```

En PowerShell, pon el `-c` en una sola línea:

```powershell
docker exec -it pgsql psql -U <usuario> -d <tu_base> -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

> **No hagas esto para “arreglar” una migración puntual:** no uses `migrate --fake`, no borres archivos de `migrations/` y no edites `django_migrations` a mano. Si dos ramas tienen modelos distintos, necesitan bases distintas o un reinicio completo del esquema.
>
> Una vez que `check_db` diga `Base sincronizada con esta rama.`, puedes volver a `runserver`. Si vas a cambiar de rama con modelos incompatibles, repite el procedimiento o usa otra base.

### 14.9 Quiero empezar de cero mi base de datos de desarrollo

Como la base es **suya y solo suya**, no necesitan autorización de nadie. La diferencia importante en este proyecto: los datos **no viven en un volumen de Docker**, viven en la carpeta `postgresql/db-data/` del repositorio. Así que hay tres niveles:

```bash
# Nivel 1: borrar solo los datos, conservar contenedor, usuario y base
docker exec -it pgsql psql -U <usuario> -d <tu_base> \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python manage.py migrate     # desde la raíz
```

```bash
# Nivel 2: recrear la BASE (útil si cambiaron POSTGRES_DB en postgresql/.env)
docker exec -it pgsql psql -U <usuario> -d postgres -c "DROP DATABASE sgprod_dev_viejo;"
docker exec -it pgsql psql -U <usuario> -d postgres -c "CREATE DATABASE sgprod_dev_tunombre;"
python manage.py migrate
```

```bash
# Nivel 3: borrar TODO, incluida la carpeta de datos (útil si cambiaron usuario/password
#           o si db-data quedó corrupto). OJO: borra los datos de los 7 si se hace en otra máquina.
cd postgresql
docker compose down
rm -rf db-data          # PowerShell: Remove-Item -Recurse -Force db-data
docker compose up -d    # recrea la base con los valores actuales de postgresql/.env
cd ..
python manage.py migrate
```

> **`rm -rf db-data` destruye los datos de forma irreversible.** Está bien en desarrollo local y en **tu** máquina. Nunca lo ejecuten en una carpeta compartida ni en un servidor.
> En Windows, si Docker Desktop tiene el archivo bloqueado, primero `docker compose down` y luego borrar: `Remove-Item -Recurse -Force db-data`.

### 14.10 No puedo ejecutar comandos de `docker compose` por permisos

En **Linux**, agregar el usuario al grupo `docker`:

```bash
sudo usermod -aG docker $USER
newgrp docker       # o cerrar sesión y volver a entrar
docker compose ps
```

En **Windows 11** este error no existe como tal: si `docker` no responde, el problema es que **Docker Desktop no está abierto** o no terminó de arrancar. Ábranlo, esperen a que el ícono quede estable y reintenten. Si el error persiste, reinicien Docker Desktop desde el ícono de la bandeja del sistema → *Restart*.

### 14.11 "No module named django" aunque instalé Django

El virtualenv no está activo. Reactívenlo en esa terminal:

```bash
# Linux / macOS / Git Bash
source .venv/bin/activate
which python        # debe apuntar a .venv/bin/python
```

```powershell
# Windows 11
.\.venv\Scripts\Activate.ps1
Get-Command python | Select-Object -ExpandProperty Source
```

> En Windows, otra causa frecuente: **abrieron una terminal nueva** y olvidaron activar el ambiente. No hay activación automática.
> Con VS Code, seleccionen el intérprete `./.venv` una vez (`Ctrl+Shift+P` → *Python: Select Interpreter*) y su terminal integrada lo activará sola.

### 14.12 Error al instalar `psycopg` (falta `pg_config`)

Usen la rueda binaria `psycopg[binary]` (ya está en `base.txt`). Si aun así falla:

```bash
# Linux — Fedora/RHEL
sudo dnf install postgresql-devel gcc
# Linux — Debian/Ubuntu
sudo apt install libpq-dev gcc
```

```powershell
# Windows 11 — normalmente NO hace falta nada de esto.
# 1) Confirmar que están en el Python correcto (3.12, 64 bits)
python --version
python -c "import struct; print(struct.calcsize('P') * 8, 'bits')"

# 2) Reinstalar forzando la rueda binaria
python -m pip install --upgrade --force-reinstall "psycopg[binary]"
```

Si en Windows insiste el error de compilación, es casi siempre por una de estas razones: instalaron Python de **32 bits**, están usando **3.14** en lugar de 3.12, o el `pip` que corre no es el del virtualenv. Revisen las tres antes de instalar *Build Tools*.

Luego, en cualquier sistema: `python -m pip install --upgrade --force-reinstall "psycopg[binary]"`.

### 14.13 Windows: "la ejecución de scripts está deshabilitada" al activar el virtualenv

Mensaje típico: *"no se puede cargar el archivo ...\Activate.ps1 porque la ejecución de scripts está deshabilitada en este sistema"*.

```powershell
# Ver la política actual
Get-ExecutionPolicy -List

# Permitir scripts firmados y propios (recomendado, alcance solo para su usuario)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Si la empresa bloquea por GPO, alternativa sin cambiar la política:
# usar CMD en su lugar con  .venv\Scripts\activate.bat
```

Después de aplicarlo, **cierren y reabran PowerShell** y vuelvan a activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 14.14 Windows: `python` abre la Microsoft Store o no lo encuentra

Es el **alias falso** de Windows, no Python de verdad.

```powershell
# Ver todas las versiones instaladas y su ruta
py -0p

# Usar explícitamente la 3.12
py -3.12 --version
```

Para quitar los alias: *Configuración → Aplicaciones → Configuración avanzada de aplicaciones → Alias de ejecución de aplicaciones* → **desactivar** `python.exe` y `python3.exe`. Cierren y reabran PowerShell.

Mientras tanto, en esta guía pueden sustituir `python` por `py -3.12` en cualquier comando.

### 14.15 Windows: Docker Desktop no arranca o pide WSL 2

```powershell
# Estado de WSL
wsl --version
wsl --status

# Instalar/actualizar WSL 2 (PowerShell como administrador)
wsl --install
wsl --update

# Si ya está instalado pero da error, apagar y reiniciar el motor
wsl --shutdown
```

Checklist si Docker Desktop no arranca en Windows 11:

1. **Virtualización activada** en la BIOS/UEFI (en el Administrador de tareas → *Rendimiento → CPU* debe decir *Virtualización: habilitada*).
2. **WSL 2** instalado y con una distro (`wsl --install`).
3. En Docker Desktop → *Settings → General*: **Use the WSL 2 based engine** marcado.
4. *Settings → Resources → WSL Integration*: activar la integración con su distro por defecto.
5. Reiniciar la computadora tras la primera instalación.
6. Si la empresa usa **Hyper-V** en lugar de WSL 2, activen *Settings → General → Use Hyper-V* (solo en ediciones Pro/Enterprise).

### 14.16 Windows: los archivos se guardan con CRLF y algo se rompe

Síntoma clásico: `docker-compose.yml` o un script `.sh` traído del repositorio falla con errores raros (`exec format error`, `\r: command not found`).

```powershell
# Configuración de una sola vez en su máquina
git config --global core.autocrlf input

# Ver qué configuración tienen
git config --list | Select-String "autocrlf"
```

Si un archivo ya quedó con CRLF, vuelvan a traerlo:

```powershell
git rm --cached -r .
git reset --hard
```

> Notepad de Windows 11 muestra `Windows (CRLF)` o `Unix (LF)` en la barra inferior. Para archivos del proyecto, **siempre LF**.

### 14.17 El contenedor falla por los certificados SSL (`ssl-cert-snakeoil.pem`)

El compose arranca PostgreSQL con `ssl=on` apuntando a:

```text
ssl_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
ssl_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
```

Esos certificados vienen de instalaciones de PostgreSQL en Debian/Ubuntu. La imagen oficial `postgres` **puede no tenerlos**, y entonces el contenedor muere al arrancar.

```bash
cd postgresql
docker compose logs db | Select-String -Pattern "ssl|certificate|does not exist|Permission denied"
```

**Solución recomendada (desarrollo local): quitar SSL**, que no aporta nada porque solo nos conectamos desde `localhost`. En el `command` del `docker-compose.yml`, eliminar estas tres parejas:

```yaml
    command:
      - "postgres"
      # - "-c"
      # - "ssl=on"
      # - "-c"
      # - "ssl_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem"
      # - "-c"
      # - "ssl_key_file=/etc/ssl/private/ssl-cert-snakeoil.key"
      - "-c"
      - "max_connections=100"
      - "-c"
      - "shared_buffers=256MB"
```

Luego recrear el contenedor (los datos **no** se pierden, están en `db-data/`):

```bash
cd postgresql
docker compose down
docker compose up -d
docker compose logs -f db
```

**Alternativa si quieren conservar SSL:** generar certificados y montarlos.

```bash
mkdir -p postgresql/certs
openssl req -new -x509 -days 365 -nodes -text \
  -out postgresql/certs/server.crt \
  -keyout postgresql/certs/server.key \
  -subj "/CN=localhost"
```

Y en el compose, agregar el volumen y apuntar a esas rutas:

```yaml
    volumes:
      - ./db-data:/var/lib/postgresql
      - ./certs:/etc/ssl/pg:ro
    command:
      - "postgres"
      - "-c"
      - "ssl=on"
      - "-c"
      - "ssl_cert_file=/etc/ssl/pg/server.crt"
      - "-c"
      - "ssl_key_file=/etc/ssl/pg/server.key"
```

> **Aviso de equipo:** cualquiera de las dos soluciones cambia el repo para los 7. Acuérdenlo en el canal y háganlo en **un solo PR**, no cada quien por su cuenta.

---


---

## 15. Referencia rápida de comandos del día a día

```bash
# ===== Linux / macOS / Git Bash =====
# Activar el ambiente (cada terminal nueva, desde la RAÍZ del repositorio)
source .venv/bin/activate

# --- PostgreSQL y pgAdmin (SIEMPRE desde la carpeta postgresql/) ---
cd postgresql
docker compose up -d                # levantar pgsql + pgadmin
docker compose ps                   # ¿pgsql está healthy?
docker compose logs -f db           # ver problemas del contenedor
docker compose stop                 # detener (conserva db-data/)
docker compose down                 # bajar los contenedores (conserva db-data/)
cd ..

# Consola SQL (desde cualquier carpeta, usando el nombre del contenedor)
docker exec -it pgsql psql -U sgprod -d sgprod_dev_tunombre
# Listar bases:  \l     Salir:  \q

# pgAdmin: http://localhost:8888   (host a usar dentro de pgAdmin: pgsql)

# --- Django (desde la RAÍZ del repositorio) ---
python manage.py runserver

# Cambios en modelos
python manage.py makemigrations
python manage.py migrate
python manage.py check_db            # ¿la base coincide con esta rama?

# Datos de prueba (Karen) — debe reproducir el mismo escenario en cualquier máquina
python manage.py seed_demo --reset

# Shell de Django con modelos cargados
python manage.py shell_plus        # viene de django-extensions

# Calidad de código
ruff check .
ruff format .

# Pruebas
pytest
pytest apps/personal/tests/ -v

# Actualizar lo que subió el equipo
git pull
cd postgresql && docker compose up -d && cd ..
python -m pip install -r requirements/dev.txt
python manage.py migrate
python manage.py check_db

# Fin de la jornada
cd postgresql && docker compose stop && cd ..
deactivate
```

```powershell
# ===== Windows 11 (PowerShell) =====
# 0) ¿Docker Desktop está abierto? (si no, el resto falla)

# Activar el ambiente (cada terminal nueva, desde la RAÍZ del repositorio)
.\.venv\Scripts\Activate.ps1

# --- PostgreSQL y pgAdmin (SIEMPRE desde la carpeta postgresql/) ---
Set-Location postgresql
docker compose up -d
docker compose ps
docker compose logs -f db
docker compose stop
docker compose down
Set-Location ..

# Consola SQL (desde cualquier carpeta; si pide TTY, quiten la -t)
docker exec -it pgsql psql -U sgprod -d sgprod_dev_tunombre

# pgAdmin: http://localhost:8888   (host a usar dentro de pgAdmin: pgsql)

# --- Django (desde la RAÍZ del repositorio) ---
python manage.py runserver

# Cambios en modelos
python manage.py makemigrations
python manage.py migrate
python manage.py check_db            # ¿la base coincide con esta rama?

# Datos de prueba
python manage.py seed_demo --reset

# Shell de Django con modelos cargados
python manage.py shell_plus

# Calidad de código
ruff check .
ruff format .

# Pruebas
pytest
pytest apps\personal\tests\ -v

# Actualizar lo que subió el equipo
git pull
Set-Location postgresql; docker compose up -d; Set-Location ..
python -m pip install -r requirements/dev.txt
python manage.py migrate
python manage.py check_db

# Fin de la jornada
Set-Location postgresql; docker compose stop; Set-Location ..
deactivate
```

> **Recordatorio del error más frecuente:** los comandos de `docker compose` **solo funcionan dentro de `postgresql/`**, y los de `python manage.py` **solo dentro de la raíz**. Si ven *"no configuration file provided: not found"*, están en la carpeta equivocada.

## 16. Siguientes pasos (de esta guía a las historias de usuario)

1. **Ejecutar esta guía** (Sprint 1, Semana 1): cada quien su PostgreSQL en Docker + Django conectado, y cerrar el checklist del §10.
2. **Redactar las historias de usuario** del MVP por módulo, con formato `Como <rol> quiero <acción> para <beneficio>` + criterios de aceptación dados-cuando-entonces, trazadas a los RF-1.x, RF-2.x y RF-3.x del documento de ideas.
3. **Estimar y priorizar** en el backlog de los 5 sprints (Sem 1–2, 3–4, 5–6, 7–8, 9–10).
4. **Congelar el MER** (Ángela y Karen) antes de que los módulos empiecen a escribir modelos.
5. **Definir el formato de las historias** y el tablero (por ejemplo: `docs/01_historias_usuario.md`) para que las 7 personas trabajen en paralelo sin pisarse.
