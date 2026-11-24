import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.calidad.models import CatalogoDefecto


class Command(BaseCommand):
    help = "Precarga el catálogo estandarizado de motivos de defecto desde demo_sgprod.json (RF-2.2)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sobrescribe la descripción de los defectos existentes si difiere del JSON.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        json_path = Path(settings.BASE_DIR) / "data" / "seed" / "demo_sgprod.json"

        if not json_path.exists():
            raise CommandError(f"No se encontró el archivo de catálogo en: {json_path}")

        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        defectos = data.get("defectos", [])
        creados = 0
        actualizados = 0
        omitidos = 0

        for item in defectos:
            codigo = item["codigo"]
            descripcion = item["descripcion"]

            if force:
                existente = CatalogoDefecto.objects.filter(codigo=codigo).first()
                if existente is None:
                    CatalogoDefecto.objects.create(
                        codigo=codigo,
                        descripcion=descripcion,
                    )
                    creados += 1
                elif existente.descripcion != descripcion:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Actualizando {codigo}: '{existente.descripcion}' -> '{descripcion}'"
                        )
                    )
                    existente.descripcion = descripcion
                    existente.save(update_fields=["descripcion"])
                    actualizados += 1
                else:
                    omitidos += 1
            else:
                _, created = CatalogoDefecto.objects.get_or_create(
                    codigo=codigo,
                    defaults={"descripcion": descripcion},
                )
                if created:
                    creados += 1
                else:
                    omitidos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo listo: {len(defectos)} defectos en JSON "
                f"({creados} nuevos, {actualizados} actualizados, {omitidos} sin cambios)."
            )
        )