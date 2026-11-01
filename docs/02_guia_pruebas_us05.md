# Guía para probar US-05 — Administración de empleados y estaciones

**Historia:** US-05 · **RF:** RF-1.1
**Rama original:** `feat/rf-1-1-empleados-estaciones`
**Alcance:** consulta y administración de empleados y estaciones desde el Admin
de Django, con la relación Jefe de Línea ↔ Línea de la corrección de US-06.

Esta guía es para quien revisa la historia por primera vez. Explica qué se
entrega, cómo correr las pruebas automáticas y cómo verificar a mano cada
criterio de aceptación, incluyendo los casos que suelen confundir.

> **Lo primero que hay que entender:** en este proyecto conviven dos tipos de
> usuario y no son lo mismo.
>
> | Quién | Dónde entra | Credencial |
> | :-- | :-- | :-- |
> | **Empleado** (`Empleado`) | Aplicación de planta: `/personal/login/` | Número de empleado + PIN |
> | **Usuario de Django** (`User`) | Admin: `/admin/` | Usuario + contraseña, con **Staff status** |
>
> Los jefes del seeding (`SG-0002`, `SG-0003`, …) son `Empleado`, **no**
> usuarios de Django. No sirven para entrar a `/admin/` con su PIN; hay que
> crearles un `User` aparte, como se explica abajo.

---

## 1. Antes de empezar

1. Ten el ambiente listo y la base migrada (ver la
   [guía del ambiente](00_guia_ambiente_desarrollo.md), §5 del
   [README](../README.md)).
2. Verifica que la base tenga datos de demo:

   ```bash
   python manage.py check_db
   python manage.py shell -c "from apps.personal.models import Empleado, Estacion, Linea; print(Empleado.objects.count(), Estacion.objects.count(), Linea.objects.count())"
   ```

   Con el seeding de US-04 deben salir **200 empleados, 40 estaciones y 5 líneas**.
   Si la base está vacía, cárgala con `python manage.py seed_demo --reset`
   (ojo: `--reset` borra los datos de dominio de **esa** base).
3. Asigna las líneas: cada empleado debe tener `Empleado.linea` y cada línea su
   `Linea.jefe_linea`. La asignación automática del seed queda en la historia
   de Karen; mientras tanto, puedes hacerlo desde el Admin.
4. Arranca el servidor en una terminal aparte:

   ```bash
   python manage.py runserver
   ```

5. Abre `http://127.0.0.1:8000/admin/`.

---

## 2. Pruebas automáticas

Lo mínimo para dar la historia por buena:

```bash
pytest apps/personal/tests.py -v
```

Resultado esperado: **10 passed**. Cada prueba cubre un criterio o un caso
límite:

| Prueba | Qué verifica |
| :-- | :-- |
| `test_admin_empleado_muestra_numero_nombre_y_estado` | El Admin lista número, nombre, línea y la columna `Activo` |
| `test_jefe_de_linea_solo_ve_al_personal_de_su_linea` | El jefe solo ve personal activo de su línea |
| `test_jefe_de_linea_solo_ve_las_estaciones_de_su_linea` | El jefe solo ve las estaciones de su línea |
| `test_jefe_de_linea_solo_ve_su_linea` | El jefe solo ve su línea y su Jefe de Línea |
| `test_jefe_de_linea_solo_ve_su_matriz_de_habilidades` | La matriz no muestra empleados ni estaciones de otras líneas |
| `test_superusuario_ve_toda_la_matriz` | El superusuario no queda restringido |
| `test_superusuario_ve_todas_las_estaciones` | El superusuario no queda restringido |
| `test_usuario_sin_linea_asignada_no_ve_datos_de_planta` | Sin grupo de línea no se ven datos de planta |
| `test_admin_linea_muestra_al_jefe_en_el_formulario` | El formulario de línea muestra al jefe asignado |
| `test_linea_rechaza_como_jefe_a_quien_no_tiene_ese_rol` | Solo un empleado con rol de jefe puede ser `Linea.jefe_linea` |

Y la suite completa, para descartar que la historia haya roto otra cosa:

```bash
pytest -q
```

Resultado esperado: **13 passed**.

Si `pytest` falla al crear la base de pruebas, revisa que PostgreSQL esté
arriba y que tu usuario de base tenga permiso `CREATEDB`; el detalle está en la
§14 de la [guía del ambiente](00_guia_ambiente_desarrollo.md).

---

## 3. Prueba manual

Duración aproximada: 15 minutos. Hazla en una ventana normal (superusuario) y
una ventana de incógnito (Jefe de Línea) para no mezclar sesiones.

### 3.1 Preparar los usuarios de prueba

**Superusuario** (si todavía no tienes uno):

```bash
python manage.py createsuperuser
```

**Jefe de Línea de la Línea 3.** La línea asignada se representa con un grupo
de Django que se llama **exactamente igual que la línea**; la relación del
modelo (`Linea.jefe_linea`) queda para las pantallas de la aplicación. Ejecuta:

```bash
python manage.py shell
```

y pega:

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()
jefe = User.objects.create_user(
    "jefe-linea-3", password="Prueba-US05!", is_staff=True
)
jefe.user_permissions.set(
    Permission.objects.filter(
        codename__in=[
            "view_empleado",
            "view_estacion",
            "view_linea",
            "view_skillmatrix",
        ]
    )
)
grupo, _ = Group.objects.get_or_create(name="Línea 3")
jefe.groups.add(grupo)
```

Esto crea un usuario **de solo consulta**. Si quieres probar también la
edición, agrega `change_empleado`, `change_estacion` y `change_linea` a la
lista de permisos.

> El nombre del grupo debe coincidir **letra por letra** con el de la línea:
> `Línea 3` lleva acento y espacio. `Linea 3` o `línea 3` no asignan nada y el
> jefe verá la lista de datos de planta vacía.

### 3.2 Criterio 1 — consultar un empleado

1. Entra a `/admin/` con el **superusuario**.
2. Abre **Personal → Empleados**.
3. Verifica las columnas: **Numero empleado**, **Nombre**, **Activo**, **Rol**.
4. Busca `SG-0001`.

**Esperado:** aparece Laura Méndez con el ícono verde de `Activo` y su rol
`Gerente de Producción (gerente)`.

### 3.3 Criterio 2 — un empleado dado de baja no aparece como disponible

1. Como superusuario, busca `SG-0005`, ábrelo y **desmarca `Activo`**.
   Guarda.
2. Sigue en la ventana del superusuario: `SG-0005` **sigue apareciendo**, ahora
   con el ícono rojo (`False`). El superusuario sí puede consultar las bajas.
3. En la ventana de incógnito, entra a `/admin/` con `jefe-linea-3`.
4. Abre **Empleados**: solo debe aparecer el personal activo de **Línea 3** y
   `SG-0005` no debe aparecer. Búscalo: **0 resultados**.
   > El buscador conserva el texto `SG-0005` que escribiste; eso no es un
   > resultado. Lo que importa es que la tabla quede vacía y el contador diga
   > *0 resultados*.
5. Prueba el acceso directo: abre
   `http://127.0.0.1:8000/admin/personal/empleado/<id>/change/` con el id de
   `SG-0005` (lo puedes obtener con
   `python manage.py shell -c "from apps.personal.models import Empleado; print(Empleado.objects.get(numero_empleado='SG-0005').pk)"`).
6. Prueba también la aplicación de planta: en `/personal/login/` usa
   `SG-0005` con PIN `123456`.

**Esperado:**

- El jefe no ve al empleado dado de baja en la lista ni por URL directa; el
  Admin lo regresa a `/admin/` con el mensaje *"Empleado con el ID … no
  existe. ¿Quizás fue eliminado?"*.
- La aplicación responde *"Acceso denegado: el usuario se encuentra inactivo."*

Al terminar, **reactiva `SG-0005`** (pásalo de nuevo a `Activo`) para no dejar
la demo alterada.

### 3.4 Criterio 3 — el Jefe de Línea solo ve su línea

En la ventana de incógnito, con `jefe-linea-3`:

1. Abre **Personal → Estaciones**.
   **Esperado:** **8 estaciones**, todas de **Línea 3** (Corte, Crimpado,
   Soldadura, Ensamble, Prueba eléctrica, Inspección visual, Empaque,
   Etiquetado) y el contador *"8 estaciones"*.
   No debe aparecer el filtro **Por línea**: al jefe solo le sirve su línea y
   ese filtro le mostraba las demás.
2. Abre **Personal → Lineas**.
   **Esperado:** una sola fila, `Línea 3`.
3. Prueba un acceso directo a una estación ajena. Obtén el id de una estación
   de la Línea 4:

   ```bash
   python manage.py shell -c "from apps.personal.models import Estacion; print(Estacion.objects.filter(linea__nombre='Línea 4').first().pk)"
   ```

   y abre `http://127.0.0.1:8000/admin/personal/estacion/<id>/change/`.

   **Esperado:** el Admin regresa a `/admin/` con *"Estación con el ID … no
   existe. ¿Quizás fue eliminado?"*.
4. Abre **Personal → Habilidades** (la matriz de habilidades).
   **Esperado:** solo aparecen habilidades de empleados y estaciones de
   **Línea 3**; ningún operador ni estación de Línea 4.
5. Contraste: repite los pasos 1 a 4 con el **superusuario**.
   **Esperado:** **40 estaciones** de las 5 líneas, filtro **Por línea** con
   Línea 3 a Línea 7, **5 líneas** en el listado y la matriz completa.

> En el Admin los modelos aparecen como *"Estacions"* y *"Lineas"*. Es la
> etiqueta automática que ya existía en los modelos; no es un defecto de esta
> historia ni cambia el alcance.

---

## 4. Checklist de aceptación

| Criterio de US-05 | Cómo se comprueba | Resultado esperado |
| :-- | :-- | :-- |
| Consultar un empleado → número, nombre y estado | Admin → Empleados | Columnas `Numero empleado`, `Nombre`, `Línea`, `Activo`, `Rol` |
| Un empleado de baja no aparece como disponible | Desactivar uno y entrar como jefe | No aparece en los resultados, ni por URL directa |
| El Jefe de Línea ve solo las estaciones de su línea | Entrar como jefe → Estaciones | 8 estaciones de Línea 3, sin filtro de otras líneas |
| El Jefe de Línea ve solo la matriz de su línea | Entrar como jefe → Habilidades | Solo empleados y estaciones de Línea 3 |
| El superusuario conserva la vista global | Entrar como superusuario | 40 estaciones y 5 líneas |
| Sin línea asignada no hay fuga de datos | Usuario staff sin grupo → Estaciones y Empleados | Listas vacías |

---

## 5. Limpieza

Borra el usuario y el grupo de prueba; deja la base como estaba:

```bash
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()
User.objects.filter(username="jefe-linea-3").delete()
Group.objects.filter(name="Línea 3").delete()
```

Y confirma que `SG-0005` volvió a estar activo. **No dejes usuarios de QA en
una base compartida.**

---

## 6. Problemas comunes

| Síntoma | Causa probable | Solución |
| :-- | :-- | :-- |
| El jefe ve **0 estaciones** | El grupo no coincide exactamente con el nombre de la línea, o el usuario no está en el grupo | Revisa `Línea 3` (acento incluido) y la pertenencia en *Authentication and Authorization → Groups* |
| El jefe ve **0 empleados** | El personal no tiene `Empleado.linea` asignada | Asigna la línea desde *Personal → Empleados* (la carga del seed la actualiza Karen) |
| El jefe recibe **403 Forbidden** en el Admin | Le faltan permisos de consulta | Agrega `view_empleado`, `view_estacion`, `view_linea` y `view_skillmatrix` |
| El jefe ve **todas** las estaciones o toda la matriz | Es superusuario: el superusuario omite el filtro a propósito | Usa un usuario staff sin `is_superuser` |
| Faltan las columnas `linea` o `jefe_linea` | La base no tiene aplicada la migración `personal.0003` | Corre `python manage.py migrate` |
| No puedo entrar a `/admin/` con `SG-0002` y PIN `123456` | `SG-0002` es un `Empleado`, no un `User` | Crea el usuario de Django de la §3.1 |
| "Acceso denegado: PIN incorrecto" en la app | El PIN del seeding es `123456`; otro valor es un PIN distinto | Usa el PIN real del empleado |
| Al abrir una estación ajena sale "no existe" | Comportamiento correcto del alcance | Es la prueba de que no hay fuga de datos |
| `pytest` no conecta a la base | PostgreSQL apagado o `.env` mal configurado | Revisa §4 y §14 de la guía del ambiente |

---

## 7. Cómo se asigna la línea

La corrección de US-06 movió la relación al modelo:

- `Empleado.linea`: línea del empleado (operadores y jefes).
- `Linea.jefe_linea`: Jefe de Línea responsable de la línea.

El Admin sigue resolviendo la línea del usuario con el grupo de Django que
coincide con el nombre de la línea. Sin grupo no se muestran datos de planta.
La relación del modelo queda lista para las pantallas de la aplicación, que
pueden leer directamente `Empleado.linea` y `Linea.jefe_linea`.

Con esa relación, la lista de empleados, las estaciones y la matriz de
habilidades quedan acotadas a la línea del jefe. La asignación de líneas del
escenario demo corresponde a la historia de seed de Karen.
