from django.core.management.base import BaseCommand
from apps.calidad.models import CatalogoDefecto

CATALOGO_INICIAL = [
    ("DEF-01", "Dimensión fuera de tolerancia"),
    ("DEF-02", "Daño superficial / Rayadura"),
    ("DEF-03", "Ensamble incompleto o suelto"),
    ("DEF-04", "Falla de soldadura / Unión"),
    ("DEF-05", "Material contaminado o deformado"),
    ("DEF-06", "Etiquetado o marcado incorrecto"),
]


class Command(BaseCommand):
    help = "Precarga el catálogo estandarizado de motivos de defecto (RF-2.2)."

    def handle(self, *args, **options):
        creados = 0
        for codigo, descripcion in CATALOGO_INICIAL:
            _, created = CatalogoDefecto.objects.update_or_create(
                codigo=codigo,
                defaults={"descripcion": descripcion},
            )
            if created:
                creados += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo listo: {len(CATALOGO_INICIAL)} defectos ({creados} nuevos)."
            )
        )