from io import StringIO

import pytest
from django.core.management import call_command

from apps.calidad.models import CatalogoDefecto


@pytest.mark.django_db
def test_seed_defectos_carga_12_desde_json_sin_sobrescribir_existentes():
    CatalogoDefecto.objects.create(
        codigo="DEF-01",
        descripcion="Descripción personalizada existente",
    )

    out = StringIO()
    call_command("seed_defectos", stdout=out)

    assert CatalogoDefecto.objects.count() == 12
    def_01 = CatalogoDefecto.objects.get(codigo="DEF-01")
    assert def_01.descripcion == "Descripción personalizada existente"
    assert "11 nuevos, 0 actualizados, 1 sin cambios" in out.getvalue()


@pytest.mark.django_db
def test_seed_defectos_con_force_actualiza_y_avisa():
    CatalogoDefecto.objects.create(
        codigo="DEF-01",
        descripcion="Dimensión fuera de tolerancia",
    )

    out = StringIO()
    call_command("seed_defectos", "--force", stdout=out)

    salida = out.getvalue()
    def_01 = CatalogoDefecto.objects.get(codigo="DEF-01")
    assert def_01.descripcion == "Falta de estaño"
    assert "Actualizando DEF-01: 'Dimensión fuera de tolerancia' -> 'Falta de estaño'" in salida
    assert "11 nuevos, 1 actualizados, 0 sin cambios" in salida