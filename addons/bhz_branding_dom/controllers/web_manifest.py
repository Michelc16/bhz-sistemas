from odoo import http

class BHZDisablePWA(http.Controller):

    # manifest padrão do Odoo
    @http.route('/web/manifest', type='http', auth='public')
    def web_manifest(self, **kw):
        return http.Response(status=404)

    # alguns navegadores pedem assim
    @http.route('/web/manifest.webmanifest', type='http', auth='public')
    def web_manifest_alt(self, **kw):
        return http.Response(status=404)

    # service worker do Odoo (se ficar ativo o browser ainda oferece instalar)
    @http.route('/web/service_worker', type='http', auth='public')
    def web_service_worker(self, **kw):
        return http.Response(status=404)
