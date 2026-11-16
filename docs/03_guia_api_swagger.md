# Guía de la API REST y su documentación Swagger

**Alcance:** cómo arrancar, autenticarse y usar el Swagger UI de SG-Prod, cómo
consumir la API desde `curl` o Python, y cómo documentar endpoints nuevos.

**Rama:** `feat/api-swagger-docs`
**Herramientas:** Django REST Framework 3.16 + drf-spectacular 0.30

---

## 0. Antes de empezar: por qué no `django-rest-swagger`

La idea original era usar [`django-rest-swagger`](https://django-rest-swagger.readthedocs.io/en/latest/),
que es el proyecto que aparece primero al buscar "swagger django". **No se usó
porque está abandonado y no funciona con este proyecto:**

| | `django-rest-swagger` | `drf-spectacular` (lo que sí se instaló) |
| :-- | :-- | :-- |
| Última versión | 2.2.0 (2019) | 0.30.0 (2025) |
| Django soportado | 1.8 – 1.11 | 4.2 – 5.2 |
| DRF soportado | 3.5 – 3.9 | 3.14 – 3.16 |
| OpenAPI | 2.0 (Swagger viejo) | 3.0 |
| Estado | Archivado por el equipo de DRF | Mantenido |

Este proyecto corre **Django 5.2.18 sobre Python 3.14**. Instalar
`django-rest-swagger` ahí no es una degradación cosmética: el paquete importa
APIs de Django que ya no existen y revienta al cargar `urls.py`. Su interfaz
tampoco funciona porque usa Swagger UI 2.x, retirado hace años.

`drf-spectacular` es el reemplazo que el propio equipo de DRF recomienda: misma
idea (una UI interactiva generada desde las vistas), pero compatible con el
stack actual y con OpenAPI 3.

> **Si tu instructor o tu equipo exige literalmente `django-rest-swagger`,**
> hay que bajar el proyecto a Django ≤ 2.2 y DRF ≤ 3.9. Eso implica abandonar
> `django-environ` reciente, `psycopg` 3 y probablemente Python 3.14. No es
> recomendable; esta guía documenta la alternativa que sí corre.

---

## 1. Qué se agregó

| Archivo | Qué hace |
| :-- | :-- |
| `requirements/base.txt` | Agrega `djangorestframework` y `drf-spectacular`. |
| `config/settings/base.py` | Registra las apps y configura `REST_FRAMEWORK` y `SPECTACULAR_SETTINGS`. |
| `config/urls.py` | Monta todo bajo `/api/`. |
| `apps/api/serializers.py` | Serializers de solo lectura (sin el PIN) + el del POST de la matriz. |
| `apps/api/views.py` | Colecciones de solo lectura y el endpoint de escritura de la matriz. |
| `apps/api/urls.py` | Router y rutas de Swagger / ReDoc / esquema. |
| `apps/api/tests.py` | 19 pruebas de la API y de la documentación. |
| `apps/personal/services.py` | Reglas de la matriz, compartidas por la vista HTML y la REST. |

### Las cuatro rutas

| URL | Qué es |
| :-- | :-- |
| `/api/docs/` | **Swagger UI**: la interfaz interactiva. Es la que vas a usar. |
| `/api/redoc/` | ReDoc: la misma especificación en modo lectura, más limpia para imprimir. |
| `/api/schema/` | El esquema OpenAPI 3 en YAML. Es lo que consumen las dos anteriores. |
| `/api/` | Redirige a `/api/docs/`. |

---

## 2. Arranque rápido

```bash
# 1. Dependencias nuevas (si ya tenías el venv, basta con esto)
python -m pip install -r requirements/dev.txt

# 2. Verifica que todo cargue
python manage.py check

# 3. Levanta el servidor
python manage.py runserver
```

Abre <http://127.0.0.1:8000/api/docs/>. Deberías ver el título **SG-Prod API**
y las operaciones agrupadas por dominio: `personal`, `matriz`, `calidad` y
`dashboard`.

Si la página sale en blanco o sin operaciones, ve a [§10](#10-problemas-comunes).

---

## 3. Autenticación (esto es lo que más confunde)

Las colecciones **no son públicas**: exponen nombres y números de empleado. Por
eso la API exige un **usuario de Django** (`User`), no el login de planta
(número de empleado + PIN) que usa `/personal/login/`.

Hay dos formas de autenticarse, y sirven para cosas distintas:

| Forma | Cómo | Cuándo usarla |
| :-- | :-- | :-- |
| **Sesión de Django** | Entra a `/admin/` en el mismo navegador y luego abre `/api/docs/`. | Probar desde Swagger UI. |
| **HTTP Basic** | Usuario y contraseña en cada request (`-u usuario:clave`). | `curl`, Postman, scripts. |

Si no tienes usuario, créalo:

```bash
python manage.py createsuperuser
# o, si ya existe, dale una contraseña utilizable:
python manage.py shell -c "from django.contrib.auth import get_user_model; u = get_user_model().objects.get(username='revisor'); u.set_password('ClaveSegura123'); u.save()"
```

### En Swagger UI

1. Abre `/admin/` e inicia sesión (esto deja la cookie de sesión).
2. Vuelve a `/api/docs/`.
3. Opcional: botón **Authorize** → `basicAuth` → usuario y contraseña. Esto es
   obligatorio si vas a probar desde otro navegador o sin sesión.

Con sesión, Swagger UI **envía el token CSRF automáticamente** en los `POST`;
no tienes que pegarlo a mano.

> **El PIN nunca sale por la API.** `Empleado.pin_hash` está excluido del serializer
> a propósito: es una credencial de planta, no un dato de consulta. Si algún día
> necesitas cambiarlo, va por el Admin, no por aquí.

---

## 4. Navegar el Swagger UI

| Elemento | Para qué sirve |
| :-- | :-- |
| Selector de **tag** | Filtra por dominio (`personal`, `calidad`, …). |
| **Filter** (caja de búsqueda) | Busca una operación por ruta o resumen. |
| **Try it out** | Habilita los campos y ejecuta la petición real contra el servidor. |
| **Execute** | Dispara la petición y muestra la URL, el `curl` equivalente y la respuesta. |
| **Schema** (abajo) | Modelos de datos: qué campos devuelve cada recurso. |

Todas las colecciones aceptan los mismos parámetros de consulta:

| Parámetro | Ejemplo | Efecto |
| :-- | :-- | :-- |
| `search` | `?search=Ana` | Búsqueda de texto sobre los campos marcados del recurso. |
| `ordering` | `?ordering=-nombre` | Ordena; el guion inicial invierte. |
| `page` | `?page=2` | Paginación, 50 registros por página. |

Ejemplo: `GET /api/empleados/?search=Ana&ordering=numero_empleado&page=1`.

La respuesta viene paginada:

```json
{
  "count": 200,
  "next": "http://127.0.0.1:8000/api/empleados/?page=2",
  "previous": null,
  "results": [
    {
      "id": 12,
      "numero_empleado": "SG-0100",
      "nombre": "Ana Activa",
      "rol": { "id": 1, "nombre": "Operador", "tipo_rol": "operador" },
      "activo": true,
      "linea": { "id": 3, "nombre": "Línea 3" }
    }
  ]
}
```

---

## 5. Catálogo de endpoints

Todo es `GET` (lista y detalle) salvo donde se indique.

| Dominio | Recurso | Ruta | Notas |
| :-- | :-- | :-- | :-- |
| personal | Roles | `/api/roles/` | `?search=` por nombre y tipo. |
| personal | Líneas | `/api/lineas/` | Incluye `jefe_linea` y sus estaciones. |
| personal | Empleados | `/api/empleados/` | **Sin `pin` ni `pin_hash`.** `?search=` por número o nombre. |
| personal | Estaciones | `/api/estaciones/` | Filtra por línea con `?search=`. |
| matriz | Matriz de habilidades | `/api/skill-matrix/` | Un registro por empleado + estación. |
| matriz | Asignar nivel | `POST /api/matriz/nivel/` | Único endpoint de escritura. |
| calidad | Catálogo de defectos | `/api/defectos/` | — |
| calidad | Asignaciones | `/api/asignaciones/` | — |
| calidad | Registros horarios | `/api/registros-calidad/` | — |
| calidad | Detalle de defectos | `/api/detalles-defecto/` | — |
| dashboard | Metas por estación | `/api/metas-estacion/` | — |
| dashboard | Bonos | `/api/bonos/` | — |
| dashboard | Alertas de capacitación | `/api/alertas-capacitacion/` | — |

### `POST /api/matriz/nivel/`

Es el único endpoint que escribe: crea, actualiza o **borra** un nivel de la
matriz de habilidades. Es el equivalente REST de la pantalla `/personal/matriz/`
y comparte con ella las reglas de negocio (`apps/personal/services.py`).

```json
{ "empleado_id": 12, "estacion_id": 4, "nivel": "Experto" }
```

| `nivel` aceptado | Efecto |
| :-- | :-- |
| `Principiante`, `Autónomo`, `Experto`, `Instructor` | Crea o actualiza la fila. |
| `Sin nivel` | **Elimina** la fila de la matriz. |

Respuestas:

```jsonc
// 200
{ "success": true, "nivel": "Experto" }

// 400 — nivel fuera del catálogo o campos faltantes
{ "success": false, "error": "nivel: \"Dios\" is not a valid choice." }

// 404 — el empleado o la estación no existen
{ "success": false, "error": "Empleado no encontrado" }
```

> La pantalla `/personal/matriz/` sigue usando su propia ruta
> (`/personal/matriz/actualizar-nivel/`) y **no cambia**: esa ruta ahora delega
> en el mismo servicio. Si algo devolvía 444, ahora devuelve **404**, que es el
> código correcto para "no existe" (444 es una extensión de nginx, no HTTP).

---

## 6. Consumirla sin el navegador

### curl

```bash
# Listar con búsqueda y orden
curl -u admin:ClaveSegura123 \
  "http://127.0.0.1:8000/api/empleados/?search=Ana&ordering=-numero_empleado"

# Un solo registro
curl -u admin:ClaveSegura123 http://127.0.0.1:8000/api/empleados/12/

# Asignar un nivel (Basic auth no necesita token CSRF)
curl -u admin:ClaveSegura123 -X POST \
  http://127.0.0.1:8000/api/matriz/nivel/ \
  -H "Content-Type: application/json" \
  -d '{"empleado_id": 12, "estacion_id": 4, "nivel": "Experto"}'

# Descargar el esquema para revisarlo o versionarlo
curl -s http://127.0.0.1:8000/api/schema/ -o openapi.yml
```

### Python

```python
import requests

BASE = "http://127.0.0.1:8000/api"
auth = ("admin", "ClaveSegura123")

r = requests.get(f"{BASE}/empleados/", auth=auth, params={"search": "Ana"}, timeout=10)
r.raise_for_status()
for empleado in r.json()["results"]:
    print(empleado["numero_empleado"], empleado["nombre"])

r = requests.post(
    f"{BASE}/matriz/nivel/",
    auth=auth,
    json={"empleado_id": 12, "estacion_id": 4, "nivel": "Instructor"},
    timeout=10,
)
print(r.status_code, r.json())
```

> **Si usas la sesión del navegador en vez de Basic auth**, el `POST` necesita
> el token CSRF (`X-CSRFToken`) y la cookie `csrftoken`. Con Basic auth no hace
> falta: es la razón por la que los ejemplos de arriba la usan.

---

## 7. Documentar un endpoint nuevo

Este es el flujo que vas a repetir cada vez que agregues algo a la API.

### 7.1. ¿La vista es de DRF?

`drf-spectacular` **solo ve vistas de DRF**. Las vistas normales de Django
(las que hacen `render()`, como `/personal/matriz/`) no aparecen en Swagger y no
hay forma limpia de forzarlas. Si necesitas documentar algo así, expón un
endpoint REST que haga lo mismo sobre el mismo servicio — es justo lo que se
hizo con la matriz.

### 7.2. Escribe el serializer

```python
class MiRecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MiModelo
        fields = ["id", "nombre", "fecha"]
        # Nunca incluyas campos sensibles (PIN, contraseñas, tokens).
```

El serializer es también la documentación del modelo: los tipos, los campos
requeridos y los `help_text` viajan al esquema.

### 7.3. Escribe la vista y anótala

```python
@extend_schema(
    tags=["calidad"],                       # agrupa en la UI
    summary="Qué hace en una línea",         # título de la operación
    description="Detalle largo, admite **Markdown**.",
    request=MiRecursoSerializer,             # cuerpo esperado
    responses={201: MiRecursoSerializer},    # qué devuelve
)
def post(self, request):
    ...
```

Si es una colección de solo lectura, hereda de `ColeccionSoloLectura` y solo
declara `queryset`, `serializer_class`, `dominio`, `search_fields` y
`ordering_fields`:

```python
class MiRecursoViewSet(ColeccionSoloLectura):
    queryset = MiModelo.objects.all().order_by("nombre")
    serializer_class = MiRecursoSerializer
    dominio = "calidad"
    search_fields = ["nombre"]
    ordering_fields = ["nombre"]
```

`dominio` decide el tag de Swagger; sin él se usa el primer segmento de la ruta.

### 7.4. Regístrala en el router

En `apps/api/urls.py`:

```python
router.register("mi-recurso", views.MiRecursoViewSet, basename="mirecurso")
```

La ruta queda en `/api/mi-recurso/` y `/api/mi-recurso/{id}/` sin escribir nada
más. Para una vista suelta (no colección), usa `path()` como con
`matriz/nivel/`.

### 7.5. Verifica

```bash
python manage.py spectacular --validate --fail-on-warn
```

Ese comando es el que usa CI: si el esquema tiene errores o *warnings*
(operation IDs duplicados, serializers ambiguos, etc.) **falla con código
distinto de cero**. No lo dejes para el final.

---

## 8. Generar el esquema en CI o para versionarlo

```bash
# A un archivo (YAML por defecto)
python manage.py spectacular --file openapi.yml --validate

# En JSON, si tu consumidor lo prefiere
python manage.py spectacular --file openapi.json --format openapi-json --validate

# Comparar contra lo versionado (rompe si alguien cambió la API sin querer)
python manage.py spectacular --file /tmp/actual.yml --validate
diff -u openapi.yml /tmp/actual.yml
```

El esquema es también lo que se importa en Postman, Insomnia o en un cliente
generado (por ejemplo `openapi-generator`).

---

## 9. Seguridad: lo que no debes aflojar

| Regla | Por qué |
| :-- | :-- |
| `IsAuthenticated` por defecto | La API expone datos de personal. No la abras sin querer. |
| El PIN fuera de los serializers | Con el PIN te haces pasar por el empleado en planta. |
| Basic auth solo por HTTPS o en local | Basic auth manda la contraseña en base64: sin TLS es texto plano. |
| Swagger cerrado en producción | La UI no es para el usuario final. Ver abajo. |
| Sin escritura salvo la matriz | Cada colección es `ReadOnlyModelViewSet`. No lo cambies sin permiso por objeto. |

En producción, restringe la documentación (por ejemplo, solo staff):

```python
# config/settings/prod.py
SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.IsAdminUser"]
SPECTACULAR_SETTINGS["SERVE_INCLUDE_SCHEMA"] = False
```

También puedes no montar `/api/docs/` en `prod.py` y dejar el esquema solo como
artefacto de CI.

---

## 10. Problemas comunes

| Síntoma | Causa | Solución |
| :-- | :-- | :-- |
| `403 {"detail": "Las credenciales de autenticación no se proveyeron."}` | No hay sesión ni Basic auth. | Entra a `/admin/` o usa **Authorize**. |
| `403 {"detail": "CSRF Failed: ..."}` | `POST` con sesión de Django sin token. | Usa Basic auth, o hazlo desde Swagger UI (él lo inyecta). |
| La UI abre pero **no lista operaciones** | `/api/schema/` falló o se sirvió mal. | Abre `/api/schema/` directo: debe devolver YAML, no un 403. |
| Página **en blanco** | El CDN de Swagger UI (`cdn.jsdelivr.net`) está bloqueado. | Ver "UI sin internet" abajo. |
| `AssertionError` al generar el esquema | Dos vistas con el mismo `operation_id` o un serializer sin `Meta.model`. | Corre con `--fail-on-warn` y revisa el mensaje; suele señalar el archivo. |
| Ruta nueva no aparece | No está en el router o la vista no es de DRF. | Regístrala en `apps/api/urls.py`; verifica que herede de DRF. |

### UI sin internet

Swagger UI se carga desde un CDN (`cdn.jsdelivr.net`). Si tu red lo bloquea, la
página sale en blanco. Descarga la distribución y sírvela como archivo estático:

```bash
npm pack swagger-ui-dist@5        # o baja el .tgz desde jsdelivr
tar -xzf swagger-ui-dist-5*.tgz
mkdir -p static/swagger-ui
cp -r package/. static/swagger-ui/
```

Y apunta la configuración a esa carpeta (ya está en `STATICFILES_DIRS`):

```python
# config/settings/base.py
SPECTACULAR_SETTINGS["SWAGGER_UI_DIST"] = "/static/swagger-ui"
```

Después corre `python manage.py collectstatic` (o recarga con `DEBUG=True`).

---

## 11. Pruebas automáticas

```bash
python -m pytest apps/api/tests.py -q     # solo API y documentación
python -m pytest -q                       # toda la suite
```

Las 19 pruebas de `apps/api/tests.py` cubren lo que se rompe en silencio: que el
esquema se genere, que la UI y ReDoc carguen, que un anónimo **no** pueda leer
ni escribir, que el PIN no se filtre, la paginación, la búsqueda, los cuatro
caminos del `POST` de la matriz (crear, actualizar, borrar, error) y las tres
formas de autenticarse (sesión + CSRF, sesión sin CSRF → 403, y Basic sin CSRF).

---

## 12. Referencias

- [drf-spectacular](https://drf-spectacular.readthedocs.io/) — documentación oficial.
- [Django REST Framework](https://www.django-rest-framework.org/) — vistas, serializers y autenticación.
- [OpenAPI 3.0](https://spec.openapis.org/oas/v3.0.3) — la especificación que se genera.
- [django-rest-swagger](https://django-rest-swagger.readthedocs.io/en/latest/) — el proyecto original, para comparar (§0).
