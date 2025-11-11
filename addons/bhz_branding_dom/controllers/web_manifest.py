from odoo import http

class BHZWebManifest(http.Controller):
    @http.route('/web/manifest', type='http', auth='public')
    def web_manifest(self, **kw):
        return http.Response(status=404)
