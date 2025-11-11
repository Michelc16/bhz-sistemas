from odoo import http

try:
    # Odoo 16+ keeps WebClient in webclient module
    from odoo.addons.web.controllers.webclient import WebClient
except ImportError:  # pragma: no cover - fallback for older versions
    from odoo.addons.web.controllers.main import WebClient

class BHZWebClient(WebClient):

    @http.route('/web/manifest', type='json', auth="public")
    def web_manifest(self):
        """Retorna manifest PWA com nome e ícones da BHZ."""
        return {
            "name": "BHZ SISTEMAS",
            "short_name": "BHZ",
            "start_url": "/web",
            "display": "standalone",
            "background_color": "#0b3b63",
            "theme_color": "#0b3b63",
            "icons": [
                {
                    "src": "/bhz_branding_dom/static/src/img/bhz_icon_192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/bhz_branding_dom/static/src/img/bhz_icon_512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
