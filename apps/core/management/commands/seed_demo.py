"""Carga los datos maestros del escenario de demo (US-04).

Por defecto solo prepara los catálogos (líneas, estaciones, empleados, metas,
defectos y matriz de habilidades). Con ``--us15`` agrega además 14 días de
asignaciones y registros de calidad para probar a mano la lista de elegibles a
bono por cero defectos (US-15).
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.calidad.models import (
    Asignacion,
    CatalogoDefecto,
    DetalleDefecto,
    RegistroCalidadHorario,
)
from apps.core.seed import cargar_dataset, ruta_dataset_por_defecto
from apps.dashboard.models import (
    AlertaCapacitacion,
    BonoIncentivo,
    ConfiguracionBono,
    MetaEstacion,
)
from apps.personal.models import (
    Empleado,
    Estacion,
    Linea,
    NivelHabilidad,
    Rol,
    SkillMatrix,
)

ROLES_DEMO = (
    ("operador", "Operador"),
    ("jefe", "Jefe de Línea"),
    ("gerente", "Gerente de Producción"),
)

NIVELES_COBERTURA = (
    NivelHabilidad.INSTRUCTOR,
    NivelHabilidad.EXPERTO,
    NivelHabilidad.EXPERTO,
    NivelHabilidad.AUTONOMO,
    NivelHabilidad.AUTONOMO,
)

# Turno 1 de la captura horaria (US-11): 06:00 a 13:59.
HORAS_TURNO_1 = range(6, 14)

# Días atrás donde se coloca el defecto de cada caso de prueba de US-15.
DIAS_DEFECTO_ANTIGUO = 10
DIAS_DEFECTO_RECIENTE = 1


class Command(BaseCommand):
    help = "Carga el escenario maestro de demo desde JSON (US-04)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            default=None,
            help="Ruta al JSON. Por defecto data/seed/demo_sgprod.json.",
        )
        parser.add_argument(
            "--empleados",
            type=int,
            default=None,
            help=(
                "Total de empleados a cargar. Por defecto, todos los del JSON. "
                "No elimina sobrantes; combínalo con --reset para un volumen exacto."
            ),
        )
        parser.add_argument(
            "--pin",
            default=None,
            help="PIN de demo. Por defecto, el valor del JSON (123456).",
        )
        parser.add_argument(
            "--aleatorio",
            type=int,
            default=2026,
            help="Semilla para que la matriz de habilidades sea reproducible.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Borra TODOS los datos de dominio de la base antes de cargar "
                "(no solo los de demo). Solo para desarrollo local."
            ),
        )
        parser.add_argument(
            "--us15",
            action="store_true",
            help=(
                "Agrega 14 días de asignaciones y calidad para probar la lista "
                "de elegibles a bono por cero defectos (US-15). Requiere --reset."
            ),
        )

    def handle(self, *args, **options):
        try:
            dataset = cargar_dataset(options["archivo"])
        except ValueError as exc:
            raise CommandError(f"Dataset inválido: {exc}") from exc

        total_dataset = dataset.empleados.total
        empleados_total = (
            options["empleados"]
            if options["empleados"] is not None
            else total_dataset
        )
        pin = options["pin"] if options["pin"] is not None else dataset.pin_default

        minimo = 1 + len(dataset.empleados.jefes) + 1
        if empleados_total < max(10, minimo):
            raise CommandError(
                f"Se necesitan al menos {max(10, minimo)} empleados "
                f"(Gerente + Jefes + Operadores); el JSON tiene {total_dataset}."
            )
        if empleados_total > total_dataset:
            raise CommandError(
                f"El dataset solo tiene {total_dataset} empleados; "
                f"pediste {empleados_total}."
            )
        if not pin.isdigit() or len(pin) != 6:
            raise CommandError("El PIN debe tener exactamente 6 dígitos.")
        if options["us15"] and not options["reset"]:
            raise CommandError(
                "--us15 requiere --reset: el escenario de US-15 necesita una "
                "base limpia para que los casos sean reproducibles."
            )

        self.dataset = dataset
        self.empleados_total = empleados_total
        self.pin = pin
        self.rng = random.Random(options["aleatorio"])
        self.archivo = options["archivo"] or str(ruta_dataset_por_defecto())

        with transaction.atomic():
            if options["reset"]:
                self._reset()
            roles = self._roles()
            lineas = self._lineas_y_estaciones()
            defectos = self._defectos()
            empleados, gerente, jefes = self._empleados(roles)
            estaciones = list(
                Estacion.objects.filter(linea__in=lineas)
                .select_related("linea")
                .order_by("linea__nombre", "orden")
            )
            self._metas(estaciones)
            habilidades = self._habilidades(empleados, estaciones)
            casos_us15 = None
            if options["us15"]:
                self._asignar_lineas(lineas, jefes)
                casos_us15 = self._datos_us15(lineas, estaciones, defectos)

        self._resumen(
            lineas=lineas,
            estaciones=estaciones,
            empleados=empleados,
            gerente=gerente,
            jefes=jefes,
            defectos=defectos,
            habilidades=habilidades,
            casos_us15=casos_us15,
        )

    # ------------------------------------------------------------------
    # Catálogos
    # ------------------------------------------------------------------
    def _reset(self):
        self.stdout.write(self.style.WARNING("Borrando datos de demo…"))
        AlertaCapacitacion.objects.all().delete()
        BonoIncentivo.objects.all().delete()
        ConfiguracionBono.objects.all().delete()
        DetalleDefecto.objects.all().delete()
        RegistroCalidadHorario.objects.all().delete()
        Asignacion.objects.all().delete()
        SkillMatrix.objects.all().delete()
        MetaEstacion.objects.all().delete()
        Estacion.objects.all().delete()
        Linea.objects.all().delete()
        Empleado.objects.all().delete()
        Rol.objects.all().delete()
        CatalogoDefecto.objects.all().delete()

    def _roles(self):
        roles = {}
        for tipo, nombre in ROLES_DEMO:
            rol, _ = Rol.objects.update_or_create(
                tipo_rol=tipo, defaults={"nombre": nombre}
            )
            roles[tipo] = rol
        return roles

    def _lineas_y_estaciones(self):
        lineas = []
        for linea_demo in self.dataset.lineas:
            linea, _ = Linea.objects.update_or_create(nombre=linea_demo.nombre)
            lineas.append(linea)
            for orden, estacion_demo in enumerate(linea_demo.estaciones, start=1):
                Estacion.objects.update_or_create(
                    linea=linea,
                    nombre=estacion_demo.nombre,
                    defaults={"orden": orden},
                )
        return lineas

    def _defectos(self):
        defectos = []
        for defecto_demo in self.dataset.defectos:
            defecto, _ = CatalogoDefecto.objects.update_or_create(
                codigo=defecto_demo.codigo,
                defaults={"descripcion": defecto_demo.descripcion},
            )
            defectos.append(defecto)
        return defectos

    def _empleados(self, roles):
        gerente_demo = self.dataset.empleados.gerente
        jefes_demo = self.dataset.empleados.jefes
        operadores_demo = self.dataset.empleados.operadores
        cupo_operadores = self.empleados_total - 1 - len(jefes_demo)
        operadores_demo = operadores_demo[:cupo_operadores]

        empleados = []
        jefes = []

        def guardar(persona_demo, tipo):
            empleado, _ = Empleado.objects.update_or_create(
                numero_empleado=persona_demo.numero,
                defaults={
                    "nombre": persona_demo.nombre,
                    "rol": roles[tipo],
                    "activo": True,
                    "pin": self.pin,
                },
            )
            return empleado

        gerente = guardar(gerente_demo, "gerente")
        empleados.append(gerente)
        for jefe_demo in jefes_demo:
            jefe = guardar(jefe_demo, "jefe")
            empleados.append(jefe)
            jefes.append(jefe)
        for operador_demo in operadores_demo:
            empleados.append(guardar(operador_demo, "operador"))
        return empleados, gerente, jefes

    def _metas(self, estaciones):
        metas = {}
        for linea_demo in self.dataset.lineas:
            for estacion_demo in linea_demo.estaciones:
                metas[(linea_demo.nombre, estacion_demo.nombre)] = estacion_demo.meta

        for estacion in estaciones:
            meta = metas.get((estacion.linea.nombre, estacion.nombre), 100)
            MetaEstacion.objects.update_or_create(
                estacion=estacion,
                defaults={"piezas_por_hora_meta": meta},
            )

    # ------------------------------------------------------------------
    # Matriz de habilidades
    # ------------------------------------------------------------------
    def _habilidades(self, empleados, estaciones):
        operadores = [empleado for empleado in empleados if empleado.rol.tipo_rol == "operador"]
        if not operadores:
            raise CommandError("No hay operadores para construir la matriz de habilidades.")

        habilidades = {}
        for estacion in estaciones:
            candidatos = self.rng.sample(
                operadores, k=min(len(NIVELES_COBERTURA), len(operadores))
            )
            for empleado, nivel in zip(candidatos, NIVELES_COBERTURA, strict=False):
                habilidades[(empleado.id, estacion.id)] = nivel

        # Cada operador debe tener al menos una estación para que la matriz no
        # deje personas completamente vacías.
        for empleado in operadores:
            if not any(clave[0] == empleado.id for clave in habilidades):
                estacion = self.rng.choice(estaciones)
                habilidades[(empleado.id, estacion.id)] = NivelHabilidad.AUTONOMO

        SkillMatrix.objects.filter(empleado__in=operadores).delete()
        SkillMatrix.objects.bulk_create(
            [
                SkillMatrix(empleado_id=empleado_id, estacion_id=estacion_id, nivel=nivel)
                for (empleado_id, estacion_id), nivel in habilidades.items()
            ],
            batch_size=500,
        )
        return habilidades

    # ------------------------------------------------------------------
    # Datos de producción para la prueba manual de US-15
    # ------------------------------------------------------------------
    def _asignar_lineas(self, lineas, jefes):
        """Deja cada línea con su jefe y cada operador en una línea.

        El seed maestro no asigna líneas porque US-05 las administra a mano.
        Para la prueba de US-15 hace falta que el Gerente vea producción real y
        que un Jefe pueda entrar a la matriz y a la captura.
        """
        lineas_ordenadas = sorted(lineas, key=lambda linea: linea.nombre)
        jefes_ordenados = sorted(jefes, key=lambda jefe: jefe.numero_empleado)
        for linea, jefe in zip(lineas_ordenadas, jefes_ordenados, strict=False):
            linea.jefe_linea = jefe
            jefe.linea = linea

        operadores = list(
            Empleado.objects.filter(rol__tipo_rol="operador").order_by("numero_empleado")
        )
        for indice, operador in enumerate(operadores):
            operador.linea = lineas_ordenadas[indice % len(lineas_ordenadas)]

        Empleado.objects.bulk_update(jefes_ordenados + operadores, ["linea"])
        Linea.objects.bulk_update(lineas_ordenadas, ["jefe_linea"])

    def _datos_us15(self, lineas, estaciones, defectos):
        """Crea 14 días de asignaciones y calidad con casos controlados.

        Cada línea tiene tres operadores identificables:
        - el primero nunca tiene piezas rechazadas;
        - el segundo tiene un defecto hace 10 días (fuera de una ventana de 7);
        - el tercero tiene un defecto ayer (dentro de cualquier ventana).
        Así se puede comprobar la lista y el cambio de periodo sin tocar código.
        """
        if not defectos:
            raise CommandError("El dataset no tiene defectos para el escenario US-15.")

        defecto = defectos[0]
        dias = max(self.dataset.dias_default, DIAS_DEFECTO_ANTIGUO + 1)
        hoy = timezone.localdate()
        fechas = [hoy - timedelta(days=offset) for offset in range(dias - 1, -1, -1)]
        fecha_antigua = hoy - timedelta(days=DIAS_DEFECTO_ANTIGUO)
        fecha_reciente = hoy - timedelta(days=DIAS_DEFECTO_RECIENTE)

        ConfiguracionBono.objects.create(
            tipo_periodo="dias", dias_evaluacion=dias, activo=True
        )

        metas = {
            meta.estacion_id: meta.piezas_por_hora_meta
            for meta in MetaEstacion.objects.all()
        }
        niveles = {
            (habilidad.empleado_id, habilidad.estacion_id): habilidad.nivel
            for habilidad in SkillMatrix.objects.filter(estacion__in=estaciones)
        }
        estaciones_por_linea = {}
        for estacion in estaciones:
            estaciones_por_linea.setdefault(estacion.linea_id, []).append(estacion)

        asignaciones = []
        casos = []
        casos_por_linea = {}
        for linea in sorted(lineas, key=lambda item: item.nombre):
            operadores = list(
                Empleado.objects.filter(
                    linea=linea, rol__tipo_rol="operador", activo=True
                ).order_by("numero_empleado")
            )
            estaciones_linea = estaciones_por_linea.get(linea.id, [])
            if not operadores or not estaciones_linea:
                continue

            caso_limpio = operadores[0]
            caso_antiguo = operadores[1] if len(operadores) > 1 else None
            caso_reciente = operadores[2] if len(operadores) > 2 else None
            casos.append(
                {
                    "linea": linea.nombre,
                    "limpio": caso_limpio,
                    "antiguo": caso_antiguo,
                    "reciente": caso_reciente,
                }
            )
            casos_por_linea[linea.id] = {
                "antiguo": caso_antiguo.id if caso_antiguo else None,
                "reciente": caso_reciente.id if caso_reciente else None,
            }

            for indice, estacion in enumerate(estaciones_linea):
                operador = operadores[indice % len(operadores)]
                for fecha in fechas:
                    asignaciones.append(
                        Asignacion(
                            empleado=operador,
                            estacion=estacion,
                            fecha=fecha,
                            turno=1,
                            alerta_supervision=niveles.get(
                                (operador.id, estacion.id)
                            )
                            in (None, NivelHabilidad.PRINCIPIANTE),
                        )
                    )

        Asignacion.objects.bulk_create(asignaciones, batch_size=500)

        registros = []
        for asignacion in asignaciones:
            estacion = asignacion.estacion
            meta = metas.get(estacion.id, 100)
            caso = casos_por_linea.get(estacion.linea_id, {})
            for hora in HORAS_TURNO_1:
                aceptadas = max(
                    0,
                    meta
                    + ((estacion.orden * 7 + hora * 3 + asignacion.fecha.toordinal()) % 7)
                    - 3,
                )
                rechazadas = 0
                if (
                    asignacion.empleado_id == caso.get("antiguo")
                    and asignacion.fecha == fecha_antigua
                    and hora == 9
                ):
                    rechazadas = 2
                elif (
                    asignacion.empleado_id == caso.get("reciente")
                    and asignacion.fecha == fecha_reciente
                    and hora == 10
                ):
                    rechazadas = 1

                registros.append(
                    RegistroCalidadHorario(
                        asignacion=asignacion,
                        hora=hora,
                        piezas_aceptadas=aceptadas,
                        piezas_rechazadas=rechazadas,
                        piezas_retrabajo=2 if (hora + estacion.orden) % 4 == 0 else 0,
                    )
                )

        RegistroCalidadHorario.objects.bulk_create(registros, batch_size=500)
        DetalleDefecto.objects.bulk_create(
            [
                DetalleDefecto(
                    registro=registro,
                    defecto=defecto,
                    cantidad=registro.piezas_rechazadas,
                )
                for registro in registros
                if registro.piezas_rechazadas > 0
            ],
            batch_size=500,
        )
        return casos

    def _resumen(
        self,
        *,
        lineas,
        estaciones,
        empleados,
        gerente,
        jefes,
        defectos,
        habilidades,
        casos_us15=None,
    ):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("SG-Prod · datos maestros de demo cargados")
        )
        self.stdout.write(f"  Dataset:       {self.dataset.nombre}")
        self.stdout.write(f"  Archivo:       {self.archivo}")
        self.stdout.write(f"  Líneas:        {len(lineas)}")
        self.stdout.write(f"  Estaciones:    {len(estaciones)}")
        self.stdout.write(f"  Empleados:     {len(empleados)}")
        self.stdout.write(f"  Habilidades:   {len(habilidades)}")
        self.stdout.write(f"  Defectos:      {len(defectos)}")
        self.stdout.write(f"  Metas:         {MetaEstacion.objects.count()}")
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(f"Credenciales de demo (PIN: {self.pin})")
        )
        self.stdout.write(f"  Gerente:       {gerente.numero_empleado} · {gerente.nombre}")
        for jefe in jefes:
            self.stdout.write(f"  Jefe:          {jefe.numero_empleado} · {jefe.nombre}")
        operador = next(
            (empleado for empleado in empleados if empleado.rol.tipo_rol == "operador"),
            None,
        )
        if operador:
            self.stdout.write(
                f"  Operador:      {operador.numero_empleado} · {operador.nombre}"
            )
        self.stdout.write("")
        if casos_us15:
            configuracion = ConfiguracionBono.objects.filter(activo=True).first()
            ventana = (
                configuracion.dias_evaluacion
                if configuracion
                else self.dataset.dias_default
            )
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"Casos de prueba US-15 (ventana de {ventana} días)"
                )
            )
            self.stdout.write(
                f"  Asignaciones:  {Asignacion.objects.count()}"
            )
            self.stdout.write(
                f"  Registros:     {RegistroCalidadHorario.objects.count()}"
            )
            self.stdout.write(
                f"  Configuración: {ConfiguracionBono.objects.filter(activo=True).count()} activa"
            )

            def persona(empleado):
                if empleado is None:
                    return "—"
                return f"{empleado.numero_empleado} · {empleado.nombre}"

            for caso in casos_us15:
                self.stdout.write("")
                self.stdout.write(f"  {caso['linea']}")
                self.stdout.write(f"    Elegible:         {persona(caso['limpio'])}")
                self.stdout.write(
                    f"    Defecto antiguo:  {persona(caso['antiguo'])} "
                    f"(hace {DIAS_DEFECTO_ANTIGUO} días)"
                )
                self.stdout.write(
                    f"    Defecto reciente: {persona(caso['reciente'])} "
                    f"(hace {DIAS_DEFECTO_RECIENTE} día)"
                )
            self.stdout.write("")
            self.stdout.write(
                "  Prueba manual: docs/04_guia_pruebas_us15.md"
            )
        else:
            self.stdout.write(
                "  Nota: asignaciones y producción se agregan con --us15 "
                "para la prueba de bono cero defectos."
            )
