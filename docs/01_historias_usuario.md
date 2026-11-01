# SG-Prod · Backlog de Historias de Usuario

**Documento:** Backlog Kanban (Asana) — listo para copiar y pegar
**Autoridad:** Product Owner
**Versión:** 2 — actualizada con la organización del equipo (`02_asignacion_equipo_carga.md` v4)
**Horizonte:** 6 semanas · 3 sprints de 2 semanas · 7 personas
**Regla de secuencia:** cada historia es la evolución de la anterior. No se abre una historia cuyo predecesor no esté en `Done`.
**Documentos base:** `01_alcance_del_proyecto.md`, `00_guia_ambiente_desarrollo.md`

---

## 0. Roles vigentes del equipo (autoridad para asignar)

| Rol | Persona | Autoridad |
| :-- | :-- | :-- |
| **Tech Lead** | Ángela | Arquitectura, patrones, migraciones. Árbitro técnico |
| **Scrum Master + PO en piso** | Rocío | Proceso, tablero, reglas de negocio, demo |
| **QA Lead** | Karen | **Gate de calidad: nada pasa a `Done` sin su verificación** |
| **Design Lead** | Martha | Toda decisión visual; la línea gráfica se define una vez |
| **Puente diseño–lógica** | Carlos Eduardo | Pantalla y servicio. Sin Docker, sin migraciones |
| **Camino crítico** | Iván | Entorno, captura en tableta, E2E |
| **Generalista** | Mariana | Asignación y alertas. Candidata a Tech Lead adjunta |

**Regla de asignación:** una historia tiene **un dueño**, **un apoyo** y **un revisor**. El dueño construye y escribe sus pruebas; el apoyo acompaña; el revisor aprueba el PR. **Karen es el gate final de las 18 historias.**

---

## 1. Recalibración de alcance (10 semanas → 6)

Compresión obligatoria: 5 sprints → **3 sprints**. El MVP no se negocia en su flujo de valor; se recorta el perímetro.

| Sprint | Semanas | Historias | Puntos | Alcance que cierra | Criterio de salida |
| :---- | :---- | :-- | :-- | :---- | :---- |
| **S1 — Fundaciones** | 1–2 | US-01 → US-05 | 31 | Entorno, MER, login QR/PIN, seeding, Módulo 1 base | Los 7 con ambiente; `migrate` limpio desde base vacía; login funcional |
| **S2 — Operación** | 3–4 | US-06 → US-12 | 37 | RF-1.2, RF-1.3, RF-1.4, RF-2.1, RF-2.2, RNF-2 | Una hora completa de 8 estaciones en menos de 3 min con motivo obligatorio |
| **S3 — Decisión** | 5–6 | US-13 → US-18 | 37 | RF-3.1 a RF-3.4, E2E, hardening, demo | Flujo completo de la sección 8 demostrado en vivo sin ayuda manual |

**Total: 105 puntos · 18 historias.**

**Recortes aprobados (fuera del MVP por tiempo):** exportables PDF/Excel, rediseño de identidad visual, y todo ítem de la sección 6 del documento de alcance. Van a **Backlog Futuro**, no se implementan.

**Compromiso:** 100 % de las historias US-01 a US-18. Si una historia no cierra en su sprint, se simplifica o se mueve a *Backlog Futuro*. No se extiende el alcance de un sprint en curso.

### Definición de Terminado (DoD) — aplica a toda historia

- [ ] Rama `feat/<id-historia>` con PR hacia `dev` y 1 revisión aprobada.
- [ ] `python manage.py check`, `migrate` y `ruff check .` sin errores.
- [ ] `pytest` en verde; **el dueño escribió las pruebas de su propia historia**.
- [ ] Criterios de aceptación verificados por **Karen (QA Lead)** contra el criterio escrito.
- [ ] Migraciones en el mismo PR del cambio de modelo.
- [ ] `.env.example` actualizado si se agregó variable.

### Definition of Ready (DoR)

Rol identificado · beneficio explícito · criterios dados-cuando-entonces · dependencias cerradas · ≤ 5 días de esfuerzo · dueño único asignado.

---

## 2. Panel de control del backlog (vista Asana)

Campos por tarea en Asana: `ID` · `Historia` · `Rol` · `Sprint` · `Prioridad` · `Puntos` · `RF/RNF` · `Depende de` · `Dueño` · `Apoyo` · `QA (gate)`.

| ID | Historia | Sprint | Prioridad | Pts | RF/RNF | Depende de | Dueño | Apoyo | QA |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| US-01 | Entorno de desarrollo reproducible | S1 | Crítica | 5 | §10 guía | — | Iván | Carlos Eduardo | Karen |
| US-02 | Modelo de datos congelado (MER) | S1 | Crítica | 8 | RNF-3 | US-01 | Ángela | Karen | Mariana |
| US-03 | Acceso por QR + PIN y por entrada manual | S1 | Crítica | 8 | RNF-1 | US-02 | Mariana | Iván | Karen |
| US-04 | Datos de prueba reproducibles (seeding) | S1 | Alta | 5 | §5 | US-02 | Karen | Ángela | Mariana |
| US-05 | Administración de empleados y estaciones | S1 | Alta | 5 | RF-1.1 | US-02 | Carlos Eduardo | Martha | Karen |
| US-06 | Consulta de matriz de habilidades | S2 | Alta | 5 | RF-1.2 | US-05 | Mariana | Martha | Karen |
| US-07 | Edición de niveles de competencia | S2 | Alta | 3 | RF-1.2 | US-06 | Mariana | Karen | Ángela |
| US-08 | Motor de sugerencia de asignación por línea | S2 | Crítica | 8 | RF-1.3 | US-07 | Carlos Eduardo | Ángela | Mariana |
| US-09 | Alerta visual por operador Principiante | S2 | Crítica | 5 | RF-1.3, §15 | US-08 | Mariana | Carlos Eduardo | Karen |
| US-10 | Asistencia por defecto con hooks de extensión | S2 | Media | 3 | RF-1.4 | US-08 | Karen | Iván | Ángela |
| US-11 | Captura horaria por estación en tableta | S2 | Crítica | 8 | RF-2.1, RNF-2 | US-09 | Iván | Martha | Mariana |
| US-12 | Catálogo de defectos con motivo obligatorio | S2 | Crítica | 5 | RF-2.2 | US-11 | Karen | Rocío | Iván |
| US-13 | Tablero At-a-Glance con semáforos y tendencia | S3 | Crítica | 8 | RF-3.1, RNF-4 | US-12 | Martha | Carlos Eduardo | Mariana |
| US-14 | KPIs verificables: FPY, Piezas/Hora, Tasa de Defectos | S3 | Crítica | 8 | RF-3.2 | US-12 | Ángela | Karen | Rocío |
| US-15 | Elegibles a bono por cero defectos | S3 | Alta | 5 | RF-3.3 | US-14 | Carlos Eduardo | Ángela | Rocío |
| US-16 | Alertas de capacitación dirigida por estación | S3 | Alta | 5 | RF-3.4 | US-14 | Carlos Eduardo | Rocío | Ángela |
| US-17 | Prueba E2E del flujo de valor | S3 | Crítica | 5 | §8, §9.1 | US-15, US-16 | Iván | Karen | Ángela |
| US-18 | Demo en vivo con datos reales | S3 | Crítica | 3 | §9.1 | US-17 | Rocío | Todo el equipo | Product Owner |

**Carga por sprint:** S1 31 pts · S2 37 pts · S3 37 pts. Sin holgura para alcance nuevo.

---

## 3. Historias de usuario

> Cada bloque = una tarea de Asana. Copiar desde el título hasta `Notas`.

---

### US-01 · Entorno de desarrollo reproducible

**Rol:** Integrante del equipo · **Sprint:** S1 (Semanas 1–2)
**Prioridad:** Crítica · **Puntos:** 5 · **RF:** §10 de la guía de ambiente
**Dueño:** Iván · **Apoyo:** Carlos Eduardo · **Revisor:** Karen

**Historia:** Como integrante del equipo quiero clonar el repositorio, levantar mi PostgreSQL en Docker y conectar Django, para tener un ambiente funcional sin depender de nadie más.

**Evoluciona a:** US-02 (sin base de datos no hay modelo).

**Criterios de aceptación**

```gherkin
Dado el repositorio clonado en una máquina limpia
Cuando ejecuto venv, requirements, los dos .env y docker compose up -d
Entonces `docker compose ps` muestra pgsql en (healthy)
Y `python manage.py check --database default` no reporta errores
Y `migrate` corre limpio partiendo de db-data/ vacía

Dado el checklist del §10
Cuando lo completo entero
Entonces los 7 integrantes lo reportan cerrado antes del fin de la Semana 1
```

**Notas · Asana**
Rama: `chore/setup-ambiente` · **Dueño: Iván** (único con Docker en su alcance) · Apoyo: Carlos Eduardo · QA: Karen
Riesgo: integrante sin ambiente el viernes de Semana 1 → parejas de instalación y padrinos Windows/Linux.
**Carlos Eduardo no toca Docker.** Se apoya con Iván sentado a su lado, no ejecutando el compose solo.

---

### US-02 · Modelo de datos congelado (MER)

**Rol:** Tech Lead · **Sprint:** S1 (Semanas 1–2)
**Prioridad:** Crítica · **Puntos:** 8 · **RF/RNF:** RNF-3
**Dueño:** Ángela · **Apoyo:** Karen · **Revisor:** Mariana

**Historia:** Como Tech Lead quiero un MER congelado con modelos normalizados y migraciones limpias, para que los tres módulos construyan sobre la misma estructura sin retrabajo.

**Evoluciona de:** US-01 (entorno operativo).

**Criterios de aceptación**

```gherkin
Dado el MER aprobado por el equipo
Cuando ejecuto `makemigrations` y `migrate` sobre una base vacía
Entonces las migraciones aplican sin error y sin intervención manual

Dado el código de modelos
Cuando reviso la separación de capas
Entonces los servicios de negocio están separados de las vistas (RNF-3)
Y existe documentación del MER en docs/

Dado el MER congelado al cierre del Sprint 1
Cuando alguien propone un cambio de modelo
Entonces requiere acuerdo del equipo y actualización del documento
```

**Notas · Asana**
Rama: `feat/mer-modelos` · **Dueña: Ángela (Tech Lead, dueña única de migraciones en S1)** · Apoyo: Karen (documentación y validez del modelo) · QA: Mariana
Bloquea: US-03, US-04, US-05.
**Restricción de carga:** Ángela trabaja un solo frente por día. No se le asignan vistas mientras el MER esté abierto.

---

### US-03 · Acceso por QR + PIN y por entrada manual

**Rol:** Empleado de piso · **Sprint:** S1 (Semanas 1–2)
**Prioridad:** Crítica · **Puntos:** 8 · **RF/RNF:** RNF-1
**Dueño:** Mariana · **Apoyo:** Iván · **Revisor:** Karen

**Historia:** Como empleado de piso quiero iniciar sesión escaneando mi QR con PIN de 6 dígitos o capturando mis datos manualmente, para entrar al sistema sin recordar usuario ni contraseña.

**Evoluciona de:** US-02 (modelo de usuarios y roles).

**Criterios de aceptación**

```gherkin
Dado un empleado activo con QR y PIN registrados
Cuando escanea su QR e ingresa el PIN correcto
Entonces accede al sistema con su rol

Dado un empleado activo
Cuando ingresa un PIN incorrecto
Entonces el sistema niega el acceso y muestra el motivo

Dado un empleado cuyo QR no es legible
Cuando usa la entrada manual con su número de empleado y PIN
Entonces accede con el mismo resultado que por QR

Dado un usuario con rol Operador, Jefe de Línea o Gerente
Cuando inicia sesión
Entonces solo ve las vistas de su rol
```

**Notas · Asana**
Rama: `feat/login-qr-pin` · **Dueña: Mariana** · Apoyo: Iván (pareja técnica) · QA: Karen
Dependencia: US-02. Habilita todo el flujo de la sección 8 del alcance.
**No se asigna a Carlos Eduardo:** crea modelo y migración, y toca seguridad. Fuera de su restricción.

---

### US-04 · Datos de prueba reproducibles (seeding)

**Rol:** Integrante del equipo · **Sprint:** S1 (Semanas 1–2)
**Prioridad:** Alta · **Puntos:** 5 · **RF:** sección 5 transversal
**Dueño:** Karen · **Apoyo:** Ángela · **Revisor:** Mariana

**Historia:** Como integrante del equipo quiero un comando de seeding que reproduzca el escenario completo, para que los siete veamos la misma pantalla con los mismos datos en cualquier máquina.

**Evoluciona de:** US-02 (modelos disponibles).

**Criterios de aceptación**

```
Dada una base vacía con migraciones aplicadas
Cuando ejecuto `python manage.py seed_demo`
Entonces se cargan empleados, estaciones por línea, matriz de habilidades, catálogo de defectos y metas de producción

Dado el mismo comando en otra máquina
Cuando comparo los datos generados
Entonces el escenario es idéntico y reproducible

Dado el seeding cargado
Cuando abro el tablero y las pantallas de captura
Entonces ninguna vista aparece vacía
```

**Notas · Asana**
Rama: `feat/seeding-demo` · **Dueña: Karen** (datos y validación: su terreno) · Apoyo: Ángela · QA: Mariana
Es la fuente de verdad para reproducir bugs: nadie se conecta a la base de otra persona.

---

### US-05 · Administración de empleados y estaciones

**Rol:** Jefe de Línea · **Sprint:** S1 (Semanas 1–2)
**Prioridad:** Alta · **Puntos:** 5 · **RF:** RF-1.1
**Dueño:** Carlos Eduardo · **Apoyo:** Martha · **Revisor:** Karen

**Historia:** Como Jefe de Línea quiero consultar y administrar empleados y estaciones por línea desde el Admin de Django, para mantener el padrón correcto antes de asignar personal.

**Evoluciona de:** US-02 y US-04 (modelo y datos base).

**Criterios de aceptación**

```gherkin
Dado el Admin de Django operativo
Cuando consulto un empleado
Entonces veo número, nombre y estado

Dado un empleado dado de baja
Cuando lo consulto para asignarlo
Entonces no aparece como disponible

Dado un Jefe de Línea con su línea asignada
Cuando abre la pantalla de consulta de estaciones
Entonces ve solo las estaciones de su línea
```

**Notas · Asana**
Rama: `feat/rf-1-1-empleados-estaciones` · **Dueño: Carlos Eduardo** (Admin y pantallas ya diseñadas) · Apoyo: Martha · QA: Karen
**Sin migraciones.** Si el modelo debe cambiar, se pide a Ángela, no se hace por cuenta propia.

---

### US-06 · Consulta de matriz de habilidades

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Alta · **Puntos:** 5 · **RF:** RF-1.2
**Dueño:** Mariana · **Apoyo:** Martha · **Revisor:** Karen

**Historia:** Como Jefe de Línea quiero ver la matriz empleado × estación con los cuatro niveles de competencia, para saber con evidencia quién domina qué antes de asignar.

**Evoluciona de:** US-05 (padrón y estaciones administrados).

**Criterios de aceptación**

```gherkin
Dada la matriz de habilidades cargada
Cuando la consulto para una línea
Entonces veo cada empleado activo contra cada estación de esa línea

Dado un empleado sin nivel registrado en una estación
Cuando aparece en la matriz
Entonces se muestra explícitamente como "sin nivel", no como celda vacía ambigua

Dado un empleado con nivel Instructor
Cuando reviso la matriz
Entonces el nivel se distingue visualmente de los otros tres
```

**Notas · Asana**
Rama: `feat/rf-1-2-consulta-matriz` · **Dueña: Mariana** · Apoyo: Martha (legibilidad y color) · QA: Karen
Los 4 niveles: Principiante, Autónomo, Experto, Instructor.
**Corrección de modelo (rama `feat/us06-correccion`):** `Empleado.linea` y `Linea.jefe_linea`; migración `personal.0003`. El Admin ya acota empleados, estaciones y matriz a la línea del jefe. La asignación de líneas del seed queda en la historia de Karen.
**Punto de control de S2:** si al día 4 esta historia no está cerrada, US-07 se transfiere a Carlos Eduardo.

---

### US-07 · Edición de niveles de competencia

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Alta · **Puntos:** 3 · **RF:** RF-1.2
**Dueño:** Mariana · **Apoyo:** Karen · **Revisor:** Ángela

**Historia:** Como Jefe de Línea quiero capturar y editar el nivel de un empleado por estación, para que la matriz refleje la competencia real del piso.

**Evoluciona de:** US-06 (consulta de la matriz).

**Criterios de aceptación**

```gherkin
Dado un empleado y una estación de su línea
Cuando registro su nivel entre los cuatro permitidos
Entonces la matriz se actualiza de inmediato

Dada una edición de nivel ya guardada
Cuando vuelvo a consultar la matriz
Entonces el valor persiste

Dado un valor fuera de los cuatro niveles permitidos
Cuando intento guardarlo
Entonces el sistema lo rechaza
```

**Notas · Asana**
Rama: `feat/rf-1-2-edicion-niveles` · **Dueña: Mariana** · Apoyo: Karen (validación de datos) · QA: Ángela
**Dueña única de este formulario.** Nadie más lo toca para evitar conflictos de merge.

---

### US-08 · Motor de sugerencia de asignación por línea

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Crítica · **Puntos:** 8 · **RF:** RF-1.3
**Dueño:** Carlos Eduardo · **Apoyo:** Ángela · **Revisor:** Mariana

**Historia:** Como Jefe de Línea quiero que el sistema sugiera la distribución completa del personal en las estaciones de mi línea, para dejar de asignar a ciegas.

**Evoluciona de:** US-06 (datos de competencia confiables).

**Criterios de aceptación**

```gherkin
Dada una línea con sus estaciones y la matriz de habilidades actualizada
Cuando solicito la sugerencia de asignación
Entonces el sistema propone una distribución completa, una persona por estación

Dada una estación sin personal disponible con nivel suficiente
Cuando se genera la sugerencia
Entonces el sistema la marca como descubierta en lugar de dejarla vacía

Dada una sugerencia generada
Cuando la acepto
Entonces queda registrada como la asignación vigente de la línea

Dada una sugerencia generada
Cuando la ajusto manualmente
Entonces el cambio manual prevalece sobre la sugerencia
```

**Notas · Asana**
Rama: `feat/rf-1-3-motor-asignacion` · **Dueño: Carlos Eduardo** · Apoyo: Ángela (lógica pura, sin migraciones) · QA: Mariana
Objetivo O1 del alcance: la distribución completa de la línea en una sola acción.
**Riesgo alto:** es el mayor punto de carga de Carlos Eduardo. Su PR se revisa **el día de apertura**, no al final.

---

### US-09 · Alerta visual por operador Principiante

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Crítica · **Puntos:** 5 · **RF:** RF-1.3, criterio §15
**Dueño:** Mariana · **Apoyo:** Carlos Eduardo · **Revisor:** Karen

**Historia:** Como Jefe de Línea quiero una alerta visual inmediata cuando asigno un Principiante a una estación, para decidir con conciencia el riesgo de rechazo.

**Evoluciona de:** US-08 (asignación operativa).

**Criterios de aceptación**

```gherkin
Dado un empleado con nivel Principiante en una estación
Cuando el Jefe de Línea lo asigna a esa estación
Entonces el sistema muestra una alerta visual
Y sugiere un Instructor de apoyo para esa estación

Dado un empleado con nivel Autónomo, Experto o Instructor
Cuando lo asigno
Entonces no se muestra alerta

Dada una línea con varios Principiantes asignados
Cuando consulto la asignación vigente
Entonces cada Principiante tiene su propia alerta visible
```

**Notas · Asana**
Rama: `feat/rf-1-3-alerta-principiante` · **Dueña: Mariana** · Apoyo: Carlos Eduardo · QA: Karen
Criterio de aceptación de módulo 1 del documento de alcance.
**Segunda candidata a transferencia** si Mariana se satura en S2.

---

### US-10 · Asistencia por defecto con hooks de extensión

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Media · **Puntos:** 3 · **RF:** RF-1.4
**Dueño:** Karen · **Apoyo:** Iván · **Revisor:** Ángela

**Historia:** Como Jefe de Línea quiero que la asignación asuma por defecto todo el personal activo, con puntos de extensión documentados, para operar hoy sin checador y poder integrarlo después.

**Evoluciona de:** US-08 (asignación sobre el padrón activo).

**Criterios de aceptación**

```gherkin
Dada una línea con personal activo
Cuando abro la pantalla de asignación
Entonces el sistema considera por defecto a todo el personal activo

Dado el código de asistencia
Cuando reviso los puntos de extensión
Entonces están documentados y aislados de la lógica de asignación

Dado un empleado dado de baja
Cuando se genera la sugerencia
Entonces queda excluido automáticamente
```

**Notas · Asana**
Rama: `feat/rf-1-4-asistencia-hooks` · **Dueña: Karen** (tarea contenida, sin lógica compleja) · Apoyo: Iván · QA: Ángela
Fuera de alcance: checador, biométrico o RFID. Solo hooks.

---

### US-11 · Captura horaria por estación en tableta

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Crítica · **Puntos:** 8 · **RF/RNF:** RF-2.1, RNF-2
**Dueño:** Iván · **Apoyo:** Martha · **Revisor:** Mariana

**Historia:** Como Jefe de Línea quiero registrar cada 60 minutos las piezas Aceptadas, Rechazadas y Retrabajo por estación, para alimentar el tablero sin frenar el turno.

**Evoluciona de:** US-09 (línea ya asignada y con alertas).

**Criterios de aceptación**

```gherkin
Dada una línea de 8 estaciones con personal asignado
Cuando registro una hora completa de las 8 estaciones
Entonces termino en menos de 3 minutos (O2)

Dado un registro en curso desde la tableta de planta
Cuando guardo cada captura
Entonces la respuesta es menor a 1.5 segundos (RNF-2)

Dada la vista de captura en tableta
Cuando la reviso en pantalla táctil
Entonces cada control tiene al menos 56 px

Dado un registro ya guardado de la hora anterior
Cuando lo consulto
Entonces aparece con su hora, estación y valores
```

**Notas · Asana**
Rama: `feat/rf-2-1-captura-horaria` · **Dueño: Iván** (camino crítico) · Apoyo: Martha (56 px y ergonomía táctil) · QA: Mariana
Medir RNF-2 sobre Wi-Fi de planta o emulación de red.
**Camino crítico:** ninguna otra historia se le suma sin quitarle una.

---

### US-12 · Catálogo de defectos con motivo obligatorio

**Rol:** Jefe de Línea · **Sprint:** S2 (Semanas 3–4)
**Prioridad:** Crítica · **Puntos:** 5 · **RF:** RF-2.2
**Dueño:** Karen · **Apoyo:** Rocío · **Revisor:** Iván

**Historia:** Como Jefe de Línea quiero seleccionar el motivo de defecto de un catálogo estandarizado y obligatorio, para que la causa sea reconstruible y comparable entre turnos.

**Evoluciona de:** US-11 (captura de piezas existente).

**Criterios de aceptación**

```gherkin
Dado el catálogo de defectos precargado por seeding
Cuando registro una hora con Rechazadas mayor a cero
Entonces debo seleccionar el motivo del catálogo

Dado un registro con Rechazadas mayor a cero
Cuando intento guardar sin seleccionar motivo
Entonces el sistema lo impide con un mensaje claro

Dado un registro con Rechazadas igual a cero
Cuando guardo
Entonces no se exige motivo

Dado un motivo seleccionado
Cuando el sistema calcula la tasa de defectos
Entonces el motivo queda asociado a la estación y al empleado
```

**Notas · Asana**
Rama: `feat/rf-2-2-catalogo-defectos` · **Dueña: Karen** (datos y reglas de validación) · Apoyo: Rocío (catálogo real de fábrica) · QA: Iván
Criterio de aceptación de módulo 2 del documento de alcance.
**Bloqueante:** el catálogo real de Rocío debe existir al fin de la Semana 2.

---

### US-13 · Tablero At-a-Glance con semáforos y tendencia

**Rol:** Gerente de Producción · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Crítica · **Puntos:** 8 · **RF/RNF:** RF-3.1, RNF-4
**Dueño:** Martha · **Apoyo:** Carlos Eduardo · **Revisor:** Mariana

**Historia:** Como Gerente de Producción quiero un tablero de lectura inmediata con semáforos Verde/Amarillo/Rojo y tendencia hora por hora, para ver el estado del turno sin abrir tablas crudas.

**Evoluciona de:** US-12 (los registros ya existen y son confiables).

**Criterios de aceptación**

```gherkin
Dada la captura horaria del turno anterior
Cuando el Gerente entra al tablero
Entonces ve semáforos Verde/Amarillo/Rojo por línea y estación

Dada una hora con calidad deteriorada
Cuando reviso la tendencia
Entonces la caída es visible hora por hora

Dada la vista del tablero
Cuando busco cualquier KPI
Entonces lo alcanzo en máximo 2 clics (RNF-4)

Dado un cambio de umbral de semáforo
Cuando lo configuro como regla de negocio
Entonces el tablero cambia de color sin tocar código
```

**Notas · Asana**
Rama: `feat/rf-3-1-tablero-at-a-glance` · **Dueña: Martha** (lectura visual e inmediata) · Apoyo: Carlos Eduardo (servicios y datos) · QA: Mariana
Umbrales = configuración, no constantes en código (supuesto 4 del alcance).
**Depende de Rocío:** sin los umbrales definidos en S1, esta historia no arranca.

---

### US-14 · KPIs verificables: FPY, Piezas/Hora, Tasa de Defectos

**Rol:** Gerente de Producción · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Crítica · **Puntos:** 8 · **RF:** RF-3.2
**Dueño:** Ángela · **Apoyo:** Karen · **Revisor:** Rocío

**Historia:** Como Gerente de Producción quiero FPY, Piezas/Hora contra meta y Tasa de Defectos por estación, línea, turno y empleado, calculados desde los registros, para tomar decisiones con números que puedo verificar.

**Evoluciona de:** US-12 (datos de calidad disponibles).

**Criterios de aceptación**

```gherkin
Dado un juego de registros conocido
Cuando consulto el FPY
Entonces el valor coincide exactamente con el cálculo manual:
Aceptadas / (Aceptadas + Rechazadas + Retrabajo)

Dada una meta de producción configurada
Cuando consulto Piezas/Hora
Entonces el sistema compara el valor real contra la meta

Dado un conjunto de registros con defectos
Cuando consulto la tasa de defectos
Entonces se desglosa por estación y por empleado

Dadas las fórmulas de KPI
Cuando corro la suite de pruebas
Entonces la cobertura de las fórmulas es del 100 %
```

**Notas · Asana**
Rama: `feat/rf-3-2-kpis` · **Dueña: Ángela** (consultas y modelo) · Apoyo: Karen (validación contra cálculo manual) · QA: Rocío (regla de negocio)
Única parte del proyecto con cobertura exigida al 100 %: un FPY mal calculado invalida bonos y capacitación.

---

### US-15 · Elegibles a bono por cero defectos

**Rol:** Gerente de Producción · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Alta · **Puntos:** 5 · **RF:** RF-3.3
**Dueño:** Carlos Eduardo · **Apoyo:** Ángela · **Revisor:** Rocío

**Historia:** Como Gerente de Producción quiero la lista de operadores con cero defectos en el periodo evaluado, para reconocer el buen desempeño y frenar la rotación.

**Evoluciona de:** US-14 (tasa de defectos por empleado confiable).

**Criterios de aceptación**

```gherkin
Dado un operador sin defectos en el periodo evaluado
Cuando el Gerente consulta elegibles a bono
Entonces el operador aparece en la lista

Dado un operador con al menos un defecto en el periodo
Cuando consulto la lista
Entonces no aparece

Dado el periodo de evaluación
Cuando lo modifico como regla de negocio configurable
Entonces la lista se recalcula sin tocar código

Dado un operador elegible
Cuando consulto su detalle
Entonces veo los registros que sustentan su elegibilidad
```

**Notas · Asana**
Rama: `feat/rf-3-3-bonos` · **Dueño: Carlos Eduardo** · Apoyo: Ángela · QA: Rocío (regla de negocio)
Fuera de alcance: pago real del bono. El sistema identifica elegibles.

---

### US-16 · Alertas de capacitación dirigida por estación

**Rol:** Gerente de Producción · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Alta · **Puntos:** 5 · **RF:** RF-3.4
**Dueño:** Carlos Eduardo · **Apoyo:** Rocío · **Revisor:** Ángela

**Historia:** Como Gerente de Producción quiero un reporte de las estaciones con mayor índice de rechazo por periodo, para dirigir la capacitación donde realmente se pierde dinero.

**Evoluciona de:** US-14 (tasa de defectos por estación confiable).

**Criterios de aceptación**

```gherkin
Dado un periodo con registros de varias estaciones
Cuando genero el reporte de capacitación
Entonces las estaciones se ordenan por índice de rechazo

Dada la estación con mayor rechazo
Cuando consulto su detalle
Entonces veo el motivo de defecto dominante

Dada la matriz de habilidades de esa estación
Cuando cruzo el reporte con la matriz
Entonces el sistema señala a los operadores a capacitar
```

**Notas · Asana**
Rama: `feat/rf-3-4-capacitacion` · **Dueño: Carlos Eduardo** · Apoyo: Rocío (criterio de fábrica) · QA: Ángela
Cierra el objetivo O5 del documento de alcance.
**Carga de Carlos Eduardo en S3: 10 puntos.** Es su sprint más pesado: revisión de PR el día de apertura.

---

### US-17 · Prueba E2E del flujo de valor

**Rol:** Equipo completo · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Crítica · **Puntos:** 5 · **RF:** §8 y §9.1 del alcance
**Dueño:** Iván · **Apoyo:** Karen · **Revisor:** Ángela

**Historia:** Como equipo quiero automatizar el recorrido completo del flujo de valor, para demostrar que el MVP funciona de extremo a extremo sin ayuda manual.

**Evoluciona de:** US-15 y US-16 (sistema completo).

**Criterios de aceptación**

```gherkin
Dado el sistema con seeding cargado
Cuando ejecuto la suite E2E
Entonces recorre: login QR/PIN, asignación con sugerencia y alerta,
captura de una hora con motivo de defecto, dashboard actualizado,
elegibles a bono y reporte de capacitación

Dado el recorrido completo
Cuando termina
Entonces no hubo intervención manual en base de datos ni en código

Dado un fallo en cualquier paso
Cuando corre la suite
Entonces el paso exacto queda identificado en el reporte
```

**Notas · Asana**
Rama: `test/e2e-flujo-valor` · **Dueño: Iván** · Apoyo: Karen (casos de prueba y registro de defectos) · QA: Ángela
**Reparto interno:** Iván automatiza, Karen define los casos y registra los defectos. Ninguno hace el trabajo del otro.

---

### US-18 · Demo en vivo con datos reales

**Rol:** Product Owner · **Sprint:** S3 (Semanas 5–6)
**Prioridad:** Crítica · **Puntos:** 3 · **RF:** §9.1 del alcance
**Dueño:** Rocío · **Apoyo:** Todo el equipo · **Revisor:** Product Owner

**Historia:** Como Product Owner quiero una demo en vivo con datos del caso de estudio, para validar el MVP ante la audiencia sin depender de datos de relleno.

**Evoluciona de:** US-17 (flujo E2E verificado).

**Criterios de aceptación**

```gherkin
Dada una sola sesión en vivo
Cuando ejecuto los 6 pasos del flujo de valor
Entonces se completan sin fallo y sin intervención manual

Dados los datos del caso de estudio
Cuando se cargan con el seeding
Entonces el dashboard muestra resultados reales, no de relleno

Dado el recorrido del tablero
Cuando busco cualquier KPI
Entonces lo alcanzo en máximo 2 clics (RNF-4)
```

**Notas · Asana**
Rama: `docs/demo-final` · **Dueña: Rocío** (guion, datos reales y conducción) · Apoyo: todo el equipo · QA: Product Owner
**Bloqueante:** los datos del caso de estudio deben estar en la Semana 3.

---

## 4. Congelamiento de alcance

1. Cada historia queda **congelada** al abrir su sprint. No se le agregan criterios a mitad de sprint.
2. Toda idea nueva va a **Backlog Futuro** (§6), sin excepción.
3. **Toda transferencia de dueño se registra en Asana el mismo día** y se avisa en el canal. Sin registro, la transferencia no existe.
4. Los tres puntos de control de transferencia ya definidos:
   - US-07 pasa a Carlos Eduardo si US-06 no cierra al día 4 del Sprint 2.
   - US-09 pasa a Carlos Eduardo si Mariana acumula más de 16 puntos activos en S2.
   - Cualquier historia de Carlos Eduardo puede recibir apoyo de Ángela o Iván sin cambiar de dueño.

---

## 5. Backlog Futuro (no se implementa en 6 semanas)

| Ítem | Origen |
| :---- | :---- |
| Integración efectiva ERP/MES (SAP, Oracle) | Fuera de alcance |
| Checador real: biométrico, RFID | RF-1.4 solo hooks |
| Captura automática desde PLC, sensores o IoT | Fuera de alcance |
| Notificaciones WhatsApp / SMS / correo | Fuera de alcance |
| App móvil nativa | Web responsive cubre tableta |
| Exportables PDF / Excel | Recortado por tiempo |
| Multiplanta, multiempresa, multi-idioma | Fuera de alcance |
| Analítica predictiva / Machine Learning | MVP descriptivo |
| Rediseño de identidad visual | Se define una vez |

---

## 6. Registro de riesgos del backlog

| Riesgo | Impacto | Respuesta |
| :---- | :-- | :---- |
| Historias de S2 bloqueadas por MER tardío | Alto | Congelar MER al cierre de S1 (US-02, criterio explícito) |
| Reglas de bonos y semáforos sin definir | Alto | Cerrarlas en S1 y tratarlas como configuración (US-13, US-15) |
| Carlos Eduardo con 23 pts y poca base técnica | Alto | Pareja en cada historia; revisión de PR el día de apertura |
| Mariana con 21 pts acumulados | Medio | Transferencia de US-07 al día 4 si US-06 no cerró |
| Karen como QA de 18 historias | Alto | Cada dueño prueba su historia; Karen solo verifica y registra |
| Iván concentra el camino crítico | Alto | Enjambre el mismo día; ninguna historia extra sin quitar otra |
| Ausencia de datos del caso de estudio en Semana 3 | Medio | Seeding reproducible de US-04 como respaldo |
| Alcance nuevo a mitad de sprint | Alto | Este documento: lo nuevo va a Backlog Futuro |
| Una persona concentra conocimiento crítico | Alto | Revisiones cruzadas obligatorias en cada PR |
