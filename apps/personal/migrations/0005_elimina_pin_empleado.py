"""Elimina el PIN en claro una vez convertido a hash (B-01)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("personal", "0004_empleado_pin_hash"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="empleado",
            name="pin",
        ),
    ]
