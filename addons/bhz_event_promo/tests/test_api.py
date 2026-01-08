import json
import base64

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestEventApi(HttpCase):
    def setUp(self):
        super().setUp()
        self.token = "testtoken"
        self.env["ir.config_parameter"].sudo().set_param("bhz_event_promo.api_token", self.token)

    def _headers(self):
        return {"Content-Type": "application/json", "X-BHZ-Token": self.token}

    def test_ping_requires_token(self):
        res = self.url_open("/api/events/ping", data=json.dumps({}).encode(), headers=self._headers())
        payload = json.loads(res.decode())
        self.assertTrue(payload.get("ok"))

    def test_upsert_event(self):
        tiny_png = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2otioAAAAASUVORK5CYII="
        )
        payload = {
            "title": "API Test Event",
            "start_datetime": "2026-01-01T12:00:00",
            "timezone": "UTC",
            "short_description": "Via API",
            "external_source": "test",
            "external_id": "evt-123",
            "image_base64": tiny_png,
            "published": True,
            "featured": True,
        }
        res = self.url_open(
            "/api/events/upsert",
            data=json.dumps(payload).encode(),
            headers=self._headers(),
        )
        data = json.loads(res.decode())
        self.assertIn("id", data)
        event = self.env["event.event"].browse(data["id"])
        self.assertTrue(event.exists())
        self.assertEqual(event.name, "API Test Event")
        self.assertTrue(event.is_featured)
        self.assertTrue(event.show_on_public_agenda)
