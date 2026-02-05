# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class BhzWebManifestController(http.Controller):
    @http.route("/web/manifest.webmanifest", type="http", auth="public", csrf=False)
    def web_manifest(self, **kwargs):
        website = getattr(request, "website", False)
        if website:
            name = website.name or "Odoo"
            start_url = website.get_base_url() or "/"
            icon_url = "/web/image/website/%s/logo" % website.id
        else:
            name = request.env.company.name or "Odoo"
            base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
            start_url = base_url or "/"
            icon_url = False

        manifest = {
            "name": name,
            "short_name": name[:32],
            "start_url": start_url,
            "display": "standalone",
            "background_color": "#FFFFFF",
            "theme_color": "#FFFFFF",
        }
        if icon_url:
            manifest["icons"] = [
                {
                    "src": icon_url,
                    "sizes": "192x192",
                    "type": "image/png",
                }
            ]

        body = json.dumps(manifest, ensure_ascii=False)
        return request.make_response(
            body,
            headers=[
                ("Content-Type", "application/manifest+json; charset=utf-8"),
                ("Cache-Control", "no-cache"),
            ],
        )
