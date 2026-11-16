# Dataset de demo (US-04)

`demo_sgprod.json` contiene los **datos maestros** que carga `seed_demo`:

- 5 líneas y 40 estaciones.
- Metas por estación.
- 12 motivos de defecto.
- 200 empleados: 1 Gerente, 5 Jefes y 194 Operadores.
- PIN de demo.

El comando carga estos catálogos y la matriz de habilidades. Por defecto **no**
crea asignaciones ni registros de producción. Con `--us15` agrega además 14
días de producción y los casos controlados que usa la
[guía de prueba manual de US-15](../../docs/04_guia_pruebas_us15.md).

## Uso

```bash
python manage.py seed_demo
python manage.py seed_demo --reset
python manage.py seed_demo --empleados 80 --reset
python manage.py seed_demo --archivo data/seed/demo_sgprod.json --reset

# Escenario completo para la prueba manual de US-15
python manage.py seed_demo --reset --us15
```

`--us15` **requiere** `--reset`: Borra los datos de dominio y deja siempre los
mismos tres casos por línea (elegible, defecto antiguo y defecto reciente).
También asigna cada línea a su Jefe de Línea y cada operador a una línea, crea
560 asignaciones y 4 480 registros horarios, y deja activa una configuración de
bono de 14 días. Los números y nombres de los casos se imprimen al terminar.

`--empleados` conserva siempre al Gerente y a todos los Jefes del JSON; el resto
se toma del inicio de la lista de Operadores.

Sin `--reset`, el comando actualiza y crea registros, pero **no borra** empleados,
estaciones ni habilidades que ya existían. Para que la base quede exactamente con
el volumen pedido, usa `--reset` junto con `--empleados`.

## Formato

```json
{
  "version": 1,
  "nombre": "Planta demo SG-Prod",
  "pin_default": "123456",
  "dias_default": 14,
  "lineas": [
    {
      "nombre": "Línea 3",
      "estaciones": [
        {"nombre": "Corte", "nivel": "experto", "meta": 88}
      ]
    }
  ],
  "defectos": [
    {"codigo": "DEF-01", "descripcion": "Falta de estaño"}
  ],
  "empleados": {
    "gerente": {"numero": "SG-0001", "nombre": "Laura Méndez"},
    "jefes": [{"numero": "SG-0002", "nombre": "Rocío Salas"}],
    "operadores": [{"numero": "SG-0005", "nombre": "Verónica Reyes"}]
  }
}
```

Validaciones:

- nombres de línea únicos;
- nombres de estación únicos dentro de su línea;
- `nivel` en `principiante`, `autonomo`, `experto` o `instructor`;
- `meta` entero positivo;
- códigos de defecto únicos;
- números de empleado únicos;
- al menos una línea, una estación, un defecto, un Gerente, un Jefe y un Operador.

`nivel` y `dias_default` se conservan para la siguiente etapa del proyecto: el
seed actual no genera producción y usa una matriz de cobertura fija. Si cambias
esos valores hoy, no cambian los registros de `SkillMatrix`.

Este archivo es la fuente de verdad de los datos de demo. No edites nombres,
estaciones o personas dentro del comando.
