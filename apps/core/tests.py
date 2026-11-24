"""Pruebas del dataset de demo (US-04).

Solo validan el archivo y no necesitan base de datos; la carga completa se
prueba contra una base local con `python manage.py seed_demo --reset`.
"""

import json

import pytest

from apps.core.seed import cargar_dataset, ruta_dataset_por_defecto


def test_dataset_demo_tiene_el_volumen_esperado():
    dataset = cargar_dataset()

    assert len(dataset.lineas) == 5
    assert dataset.total_estaciones == 40
    assert dataset.empleados.total == 200
    assert dataset.empleados.gerente.numero == "SG-0001"
    assert any(
        operador.numero == "SG-0005" for operador in dataset.empleados.operadores
    )


def test_dataset_rechaza_numeros_de_empleado_repetidos(tmp_path):
    datos = json.loads(ruta_dataset_por_defecto().read_text(encoding="utf-8"))
    datos["empleados"]["operadores"][0]["numero"] = datos["empleados"]["gerente"]["numero"]
    archivo = tmp_path / "dataset_invalido.json"
    archivo.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(ValueError, match="repetidos"):
        cargar_dataset(archivo)


@pytest.mark.django_db
def test_check_db_accepts_the_current_schema(capsys):
    from django.core.management import call_command

    call_command("check_db")

    salida = capsys.readouterr().out
    assert "Esquema: OK" in salida
    assert "[ERROR]" not in salida


@pytest.mark.django_db
def test_seed_demo_crea_principiante_e_instructor_por_linea_para_us09(client):
    from django.core.management import call_command

    from apps.personal.models import Estacion, Linea, NivelHabilidad, SkillMatrix

    call_command("seed_demo", "--reset", "--us15", "--empleados", "30")

    lineas = Linea.objects.order_by("nombre")
    assert lineas.exists()

    for linea in lineas:
        estacion = Estacion.objects.filter(linea=linea).order_by("orden").first()
        principiante = SkillMatrix.objects.filter(
            empleado__linea=linea,
            estacion=estacion,
            nivel=NivelHabilidad.PRINCIPIANTE,
        ).first()
        assert principiante is not None

        instructor = SkillMatrix.objects.filter(
            empleado__linea=linea,
            estacion=estacion,
            nivel=NivelHabilidad.INSTRUCTOR,
        ).first()
        assert instructor is not None

    primera_linea = lineas.first()
    jefe = primera_linea.jefe_linea
    estacion = Estacion.objects.filter(linea=primera_linea).order_by("orden").first()
    principiante = (
        SkillMatrix.objects.filter(
            empleado__linea=primera_linea,
            estacion=estacion,
            nivel=NivelHabilidad.PRINCIPIANTE,
        )
        .select_related("empleado")
        .first()
        .empleado
    )
    instructor = (
        SkillMatrix.objects.filter(
            empleado__linea=primera_linea,
            estacion=estacion,
            nivel=NivelHabilidad.INSTRUCTOR,
        )
        .select_related("empleado")
        .first()
        .empleado
    )

    sesion = client.session
    sesion["empleado_id"] = jefe.id
    sesion.save()

    client.post(
        "/personal/matriz/",
        {
            "guardar_asignacion": "1",
            "turno": "1",
            f"estacion_{estacion.id}": str(principiante.id),
        },
    )
    respuesta = client.get("/personal/matriz/?vista=asignacion&turno=1")
    contenido = respuesta.content.decode()
    primera_fila = respuesta.context["tabla_vigente_estatica"][0]

    assert respuesta.status_code == 200
    assert primera_fila["empleado_asignado"] == principiante
    assert primera_fila["es_principiante"] is True
    assert primera_fila["instructor_apoyo"] == instructor
    assert respuesta.context["instructores_apoyo"][str(estacion.id)] == instructor.nombre
    assert instructor.nombre in contenido