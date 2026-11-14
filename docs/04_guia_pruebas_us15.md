# Guía para probar US-15 — Elegibles a bono por cero defectos

**Historia:** US-15 · **RF:** RF-3.3
**Alcance:** lista de operadores elegibles, periodo configurable y detalle de
los registros que sustentan la elegibilidad.
**Fuera de alcance:** pago real del bono. El sistema solo identifica elegibles.

Esta guía sirve para que Rocío (QA / regla de negocio) apruebe la historia a
mano, sin escribir consultas ni tocar código. Todo el escenario se carga con un
solo comando y es reproducible en cualquier ambiente de desarrollo.

---

## 1. Preparar el escenario

Desde la raíz del repositorio, con el virtualenv activo y la base migrada:

```bash
python manage.py migrate
python manage.py seed_demo --reset --us15
python manage.py runserver
```

> **Cuidado:** `--reset` borra **todos los datos de dominio** de esa base
> (empleados, líneas, estaciones, habilidades, metas, defectos, asignaciones,
> registros y configuración de bono). Úsalo solo en una base local.
>
> `--us15` exige `--reset` a propósito: así los casos siempre quedan iguales.
> El comando falla con un mensaje claro si se te olvida.

El comando imprime al final los casos de prueba y sus números de empleado.
También deja:
- 5 líneas, 40 estaciones y 200 empleados;
- cada línea con su Jefe de Línea y cada operador en una línea;
- 560 asignaciones (5 líneas × 8 estaciones × 14 días, turno 1);
- 4 480 registros horarios (8 horas por asignación);
- una `Configuración de bono cero defectos` activa de **14 días**.

Si tu base ya tenía datos y no quieres borrarlos, crea otra base y apunta
`DB_NAME` a ella antes de correr el seed (ver
[guía del ambiente](00_guia_ambiente_desarrollo.md), §14.8.1).

---

## 2. Credenciales

| Quién | Dónde entra | Número | PIN |
| :-- | :-- | :-- | :-- |
| Gerente de Producción | `/personal/login/` | `SG-0001` | `123456` |
| Jefe de Línea 3 | `/personal/login/` | `SG-0002` | `123456` |
| QA / Admin | `/admin/` | usuario de Django con `is_staff` | contraseña propia |

> El Gerente y los Jefes del seed son **empleados**, no usuarios de Django.
> Para entrar a `/admin/` necesitas un superusuario aparte
> (`python manage.py createsuperuser`). El PIN no sirve en el Admin.

---

## 3. Casos sembrados

Cada línea tiene tres operadores distinguibles. Los de la **Línea 3** son los
recomendados para la demostración:

| Caso | Número | Nombre | Qué tiene |
| :-- | :-- | :-- | :-- |
| Elegible | `SG-0005` | Verónica Reyes | 14 días sin piezas rechazadas |
| Defecto antiguo | `SG-0012` | Ricardo Gómez | 2 piezas rechazadas hace 10 días |
| Defecto reciente | `SG-0017` | Teresa Morales | 1 pieza rechazada ayer |

Otras líneas tienen el mismo patrón:

| Línea | Elegible | Defecto antiguo | Defecto reciente |
| :-- | :-- | :-- | :-- |
| Línea 4 | `SG-0008` Rosa López | `SG-0013` Alberto Flores | `SG-0018` Teresa Rojas |
| Línea 5 | `SG-0009` Adriana Campos | `SG-0014` Javier Sánchez | `SG-0019` Silvia Cruz |
| Línea 6 | `SG-0010` Rosa Aguilar | `SG-0015` Alberto Silva | `SG-0020` Pablo Ramírez |
| Línea 7 | `SG-0011` Pablo Aguilar | `SG-0016` Francisco Rojas | `SG-0021` Ricardo Soto |

La idea es simple:
- con la ventana de **14 días**, el defecto antiguo queda dentro y el operador
  **no** aparece;
- al cambiar la regla a **7 días**, ese defecto queda fuera y el operador
  **sí** aparece;
- el defecto reciente queda dentro en ambas ventanas, así que ese operador
  **nunca** aparece.

---

## 4. Verificación manual (criterios de aceptación)

### 4.1 Un operador sin defectos aparece en la lista

1. Entra con `SG-0001` / `123456`.
2. Abre `/dashboard/gerente/`.
3. En la tarjeta **Bonos del periodo**, verifica:
   - el periodo abarca los últimos **14 días** (fecha de inicio a hoy);
   - aparece **Verónica Reyes (`SG-0005`)**;
   - **no** aparecen Ricardo Gómez (`SG-0012`) ni Teresa Morales (`SG-0017`).

> La lista se presenta **paginada de 10 en 10** y ordenada por piezas aceptadas,
> así que Verónica puede quedar en una página posterior. Usa los controles
> **Anterior / Siguiente** («Página X de Y») para recorrerla; el total de
> elegibles se muestra arriba de la tabla.

✅ Criterio: *“Dado un operador sin defectos en el periodo evaluado, cuando el
Gerente consulta elegibles a bono, entonces el operador aparece en la lista.”*

### 4.2 Un operador con al menos un defecto no aparece

En la misma lista del paso anterior, confirma que `SG-0012` y `SG-0017` no
están. Ambos tienen piezas rechazadas dentro de la ventana de 14 días.

✅ Criterio: *“Dado un operador con al menos un defecto en el periodo, cuando
consulto la lista, entonces no aparece.”*

### 4.3 El detalle muestra los registros que sustentan la elegibilidad

1. En la fila de **Verónica Reyes**, haz clic en **Ver detalle (N)** (columna
   *Evidencia*).
2. Se abre `/dashboard/gerente/bono/<id>/`.
3. Verifica que se ven sus registros horarios: fecha, turno, línea, estación,
   aceptadas, rechazadas y retrabajo.
4. Comprueba que todas las filas tienen **0 rechazadas**.

✅ Criterio: *“Dado un operador elegible, cuando consulto su detalle, entonces
veo los registros que sustentan su elegibilidad.”*

### 4.4 El periodo es configurable y recalcula la lista sin tocar código

1. Entra a `/admin/` con tu usuario de Django.
2. Abre **Dashboard → Configuración de bono cero defectos**.
3. Cambia **Días de evaluación** de `14` a `7` y guarda.
4. Vuelve a `/dashboard/gerente/` y actualiza.
5. Verifica:
   - el periodo ahora abarca los últimos **7 días**;
   - **Ricardo Gómez (`SG-0012`)** ahora **sí** aparece;
   - **Teresa Morales (`SG-0017`)** sigue **sin** aparecer;
   - Verónica Reyes (`SG-0005`) sigue apareciendo.
6. Para dejarlo como estaba, vuelve a `14` o corre otra vez el seed.

✅ Criterio: *“Dado el periodo de evaluación, cuando lo modifico como regla de
negocio configurable, entonces la lista se recalcula sin tocar código.”*

> También puedes probar el modo **Rango de fechas específico** en el mismo
> formulario. Elige un rango que incluya el día del defecto antiguo y confirma
> que `SG-0012` desaparece; después elige un rango que lo excluya y confirma
> que reaparece.

---

## 5. Pruebas automáticas

```bash
pytest apps/core/test_seed_us15.py apps/dashboard/test_bonos.py -v
```

- `test_seed_us15_crea_los_casos_de_bono_y_respeta_el_periodo` valida los
  conteos, la configuración de 14 días, la elegibilidad y el recálculo a 7 días.
- `test_seed_us15_exige_reset_para_ser_reproducible` protege el contrato del
  comando.
- `apps/dashboard/test_bonos.py` cubre la regla de negocio y la pantalla del
  Gerente.

---

## 6. Problemas comunes

| Síntoma | Causa / solución |
| :-- | :-- |
| `--us15 requiere --reset` | Vuelve a correr `python manage.py seed_demo --reset --us15`. |
| La tarjeta **Bonos del periodo** no aparece | Iniciaste sesión como Jefe u Operador. Usa `SG-0001` (Gerente). |
| La lista está vacía | Revisa la configuración del periodo en el Admin; si la base se sembró hace más de 14 días, vuelve a correr el seed. |
| El detalle responde 404 | El operador no es elegible en la ventana actual. Ajusta el periodo o usa un operador que sí aparezca en la lista. |
| No puedo entrar a `/admin/` con el PIN | El Admin usa `User` de Django, no empleados. Crea un superusuario con `python manage.py createsuperuser`. |
| No aparecen líneas o jefes | El escenario `--us15` asigna líneas y jefes. Si corriste solo `seed_demo --reset`, vuelve a correrlo con `--us15`. |

---

## 7. Nota para QA

El seed es determinista: no usa aleatoriedad para las fechas ni para los
defectos de los tres casos. Las fechas se calculan con la fecha local de la
planta (`America/Tijuana`), por lo que el escenario debe probarse el mismo día
en que se carga. Si la base queda sembrada varios días, vuelve a ejecutar
`python manage.py seed_demo --reset --us15` para reubicar los casos.
