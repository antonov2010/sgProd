import pytest

from apps.personal.models import Empleado, Rol


@pytest.fixture
def entrar(client, db):
    """Devuelve una función que inicia sesión de planta con el rol indicado."""

    def _entrar(tipo_rol, activo=True, numero=None):
        rol, _ = Rol.objects.get_or_create(tipo_rol=tipo_rol, defaults={"nombre": tipo_rol.title()})
        empleado = Empleado.objects.create(
            numero_empleado=numero or f"T-{tipo_rol}",
            nombre=f"Prueba {tipo_rol}",
            rol=rol,
            activo=activo,
        )
        sesion = client.session
        sesion["empleado_id"] = empleado.id
        sesion.save()
        return empleado

    return _entrar
