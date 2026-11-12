import json
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.personal.models import Empleado, Estacion, Linea, Rol

from . import services
from .models import Asignacion, CatalogoDefecto, DetalleDefecto, RegistroCalidadHorario


class CatalogoDefectoRF22Tests(TestCase):
    """Pruebas unitarias y de integración para RF-2.2 (Catálogo estandarizado de defectos)."""

    def setUp(self):
        self.rol_jefe = Rol.objects.create(nombre="Jefe de Línea", tipo_rol="jefe")
        self.rol_operador = Rol.objects.create(nombre="Operador", tipo_rol="operador")

        self.jefe = Empleado.objects.create(
            numero_empleado="SG-9001",
            nombre="Jefe Prueba",
            pin="123456",
            rol=self.rol_jefe,
            activo=True,
        )
        self.operador = Empleado.objects.create(
            numero_empleado="SG-9002",
            nombre="Operador Prueba",
            pin="123456",
            rol=self.rol_operador,
            activo=True,
        )

        self.linea = Linea.objects.create(nombre="Línea Test", jefe_linea=self.jefe)
        self.estacion = Estacion.objects.create(
            linea=self.linea,
            nombre="Estación Test",
            orden=1,
        )

        self.turno = 1
        self.hora = 8
        self.asignacion = Asignacion.objects.create(
            empleado=self.operador,
            estacion=self.estacion,
            turno=self.turno,
        )

        self.defecto = CatalogoDefecto.objects.create(
            codigo="DEF-01",
            descripcion="Dimensión fuera de tolerancia",
        )

        self.client = Client()
        session = self.client.session
        session["empleado_id"] = self.jefe.id
        session.save()

    @patch("apps.calidad.services.hora_actual", return_value=8)
    def test_guardar_sin_rechazos_no_requiere_defecto(self, _mock_hora):
        """Si piezas_rechazadas == 0, permite guardar sin defecto y no crea DetalleDefecto."""
        url = reverse("calidad:guardar_captura")
        payload = {
            "asignacion_id": self.asignacion.id,
            "hora": self.hora,
            "aceptadas": 15,
            "rechazadas": 0,
            "retrabajo": 1,
            "defecto_id": None,
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["registro"]["defecto"], "—")
        self.assertEqual(DetalleDefecto.objects.count(), 0)

    @patch("apps.calidad.services.hora_actual", return_value=8)
    def test_guardar_con_rechazos_sin_defecto_falla(self, _mock_hora):
        """Si piezas_rechazadas > 0 y no se envía defecto_id, responde 400 y no guarda registro."""
        url = reverse("calidad:guardar_captura")
        payload = {
            "asignacion_id": self.asignacion.id,
            "hora": self.hora,
            "aceptadas": 10,
            "rechazadas": 2,
            "retrabajo": 0,
            "defecto_id": "",
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(RegistroCalidadHorario.objects.count(), 0)

    @patch("apps.calidad.services.hora_actual", return_value=8)
    def test_guardar_con_rechazos_y_defecto_inexistente_falla(self, _mock_hora):
        """Si se envía un defecto_id que no existe en CatalogoDefecto, responde 400."""
        url = reverse("calidad:guardar_captura")
        payload = {
            "asignacion_id": self.asignacion.id,
            "hora": self.hora,
            "aceptadas": 10,
            "rechazadas": 1,
            "retrabajo": 0,
            "defecto_id": 99999,
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(RegistroCalidadHorario.objects.count(), 0)

    @patch("apps.calidad.services.hora_actual", return_value=8)
    def test_guardar_con_rechazos_y_defecto_valido_crea_detalle(self, _mock_hora):
        """Si piezas_rechazadas > 0 y defecto_id es válido, guarda registro y DetalleDefecto."""
        url = reverse("calidad:guardar_captura")
        payload = {
            "asignacion_id": self.asignacion.id,
            "hora": self.hora,
            "aceptadas": 12,
            "rechazadas": 3,
            "retrabajo": 0,
            "defecto_id": self.defecto.id,
        }

        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("DEF-01", data["registro"]["defecto"])

        detalle = DetalleDefecto.objects.get()
        self.assertEqual(detalle.defecto, self.defecto)
        self.assertEqual(detalle.cantidad, 3)

    @patch("apps.calidad.services.hora_actual", return_value=8)
    def test_actualizar_rechazos_a_cero_limpia_detalle_defecto(self, _mock_hora):
        """Si se corrige un registro previo bajando rechazadas a 0, elimina el DetalleDefecto."""
        services.registrar_captura(
            self.linea,
            self.asignacion.id,
            self.hora,
            10,
            2,
            0,
            defecto_id=self.defecto.id,
        )
        self.assertEqual(DetalleDefecto.objects.count(), 1)

        services.registrar_captura(
            self.linea,
            self.asignacion.id,
            self.hora,
            12,
            0,
            0,
            defecto_id=None,
        )
        self.assertEqual(DetalleDefecto.objects.count(), 0)