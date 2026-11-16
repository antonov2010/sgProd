"""Agrega el hash del PIN y convierte los PIN existentes (B-01).

El PIN en claro que existía en ``Empleado.pin`` se reemplaza por su hash de
Django. La columna ``pin`` se elimina en la migración siguiente, de modo que
esta migración pueda ejecutarse tanto sobre una base vacía como sobre una base
con datos.
"""

from django.contrib.auth.hashers import make_password
from django.db import migrations, models


def hashear_pines_existentes(apps, schema_editor):
    """Convierte cada PIN en claro en su hash, sin dejar rastro del valor."""
    Empleado = apps.get_model("personal", "Empleado")
    for empleado in Empleado.objects.exclude(pin__isnull=True).exclude(pin=""):
        empleado.pin_hash = make_password(empleado.pin)
        empleado.save(update_fields=["pin_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("personal", "0003_jefe_de_linea"),
    ]

    operations = [
        migrations.AddField(
            model_name="empleado",
            name="pin_hash",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.RunPython(
            hashear_pines_existentes,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
