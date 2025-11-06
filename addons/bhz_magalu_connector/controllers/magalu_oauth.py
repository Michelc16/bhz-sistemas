from odoo import http
from odoo.http import request


class MagaluOAuthController(http.Controller):

    @http.route('/magalu/oauth/callback', type='http', auth='public', csrf=False)
    def magalu_oauth_callback(self, **kwargs):
        code = kwargs.get("code")
        if not code:
            return "Code not provided"

        # pega a config da empresa atual (pega a primeira mesmo)
        config = request.env["bhz.magalu.config"].sudo().search([], limit=1)
        if not config:
            config = request.env["bhz.magalu.config"].sudo().create({})

        api = request.env["bhz.magalu.api"].sudo()
        api.exchange_code_for_token(config, code)

        # volta pro Odoo
        return request.redirect("/web?#action=")
