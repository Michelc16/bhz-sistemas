import base64
import logging
import time

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class BhzEventApiController(http.Controller):
    _rate_bucket = {}
    _RATE_LIMIT = 120  # requests per 5 minutes per IP
    _RATE_WINDOW = 300

    # --------------------------- Utils
    def _get_client_ip(self):
        return request.httprequest.remote_addr or "0.0.0.0"

    def _check_rate_limit(self):
        ip = self._get_client_ip()
        now = time.time()
        bucket = self._rate_bucket.get(ip, [])
        bucket = [ts for ts in bucket if now - ts < self._RATE_WINDOW]
        if len(bucket) >= self._RATE_LIMIT:
            _logger.warning("API rate limit exceeded for ip=%s", ip)
            return False
        bucket.append(now)
        self._rate_bucket[ip] = bucket
        return True

    def _get_token(self):
        headers = request.httprequest.headers
        auth_header = headers.get("Authorization", "") or ""
        token = headers.get("X-BHZ-Token")
        if not token and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        return token or ""

    def _validate_token(self):
        expected = request.env["ir.config_parameter"].sudo().get_param("bhz_event_promo.api_token")
        if not expected:
            _logger.error("API token not configured (bhz_event_promo.api_token)")
            return False
        provided = self._get_token()
        return expected and provided and expected.strip() == provided.strip()

    def _unauthorized(self, message="Unauthorized"):
        return request.make_json_response({"error": message}, status=401)

    def _bad_request(self, message="Bad Request"):
        return request.make_json_response({"error": message}, status=400)

    def _server_error(self, message="Server Error"):
        return request.make_json_response({"error": message}, status=500)

    # --------------------------- Routes
    @http.route("/api/events/ping", type="json", auth="public", cors="*", csrf=False)
    def ping(self, **kwargs):
        if not self._validate_token():
            return self._unauthorized()
        if not self._check_rate_limit():
            return request.make_json_response({"error": "rate_limited"}, status=429)
        return {"ok": True, "time": fields.Datetime.now()}

    @http.route("/api/events/by_external/<string:source>/<string:external_id>", type="json", auth="public", cors="*", csrf=False)
    def by_external(self, source=None, external_id=None, **kwargs):
        if not self._validate_token():
            return self._unauthorized()
        if not self._check_rate_limit():
            return request.make_json_response({"error": "rate_limited"}, status=429)
        Event = request.env["event.event"].sudo()
        rec = Event.search(
            [("external_source", "=", source), ("external_id", "=", external_id)],
            limit=1,
        )
        if not rec:
            return request.make_json_response({"error": "not_found"}, status=404)
        return {
            "id": rec.id,
            "name": rec.name,
            "external_source": rec.external_source,
            "external_id": rec.external_id,
            "published": getattr(rec, "website_published", False) or getattr(rec, "is_published", False),
            "featured": rec.is_featured,
        }

    @http.route("/api/events/upsert", type="json", auth="public", cors="*", csrf=False)
    def upsert(self, **payload):
        if not self._validate_token():
            return self._unauthorized()
        if not self._check_rate_limit():
            return request.make_json_response({"error": "rate_limited"}, status=429)
        try:
            record = request.env["event.event"].bhz_api_upsert_event(payload)
            return {"id": record.id, "external_source": record.external_source, "external_id": record.external_id}
        except ValueError as err:
            _logger.warning("API upsert validation error: %s | payload=%s", err, payload)
            return self._bad_request(str(err))
        except Exception as err:
            _logger.exception("API upsert failed")
            return self._server_error(str(err))

    @http.route("/api/events/bulk_upsert", type="json", auth="public", cors="*", csrf=False)
    def bulk_upsert(self, **payload):
        if not self._validate_token():
            return self._unauthorized()
        if not self._check_rate_limit():
            return request.make_json_response({"error": "rate_limited"}, status=429)
        events = payload.get("events") or []
        if not isinstance(events, list):
            return self._bad_request("Payload deve conter uma lista 'events'")
        results = []
        for item in events:
            try:
                rec = request.env["event.event"].bhz_api_upsert_event(item)
                results.append({"external_source": rec.external_source, "external_id": rec.external_id, "id": rec.id, "status": "ok"})
            except Exception as err:
                _logger.warning("API bulk item failed: %s", err)
                results.append({"external_source": item.get("external_source"), "external_id": item.get("external_id"), "status": "error", "message": str(err)})
        return {"results": results}
