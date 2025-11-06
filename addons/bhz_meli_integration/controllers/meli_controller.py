import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MeliAuthController(http.Controller):

    @http.route("/meli/auth/callback", type="http", auth="public", csrf=False)
    def meli_auth_callback(self, **kwargs):
        """
        Rota que o Mercado Livre chama depois que o usuário autoriza.
        Ela recebe ?code=... e opcionalmente ?state=<id_da_conta>
        """
        code = kwargs.get("code")
        account_id = kwargs.get("state")

        if not code:
            return "Faltou o code do Mercado Livre."

        if account_id:
            account = request.env["meli.account"].sudo().browse(int(account_id))
        else:
            # pega a primeira conta em rascunho
            account = request.env["meli.account"].sudo().search([("state", "=", "draft")], limit=1)

        if not account:
            return "Nenhuma conta do Mercado Livre encontrada para vincular."

        try:
            account.sudo().exchange_code_for_token(code)
        except Exception as e:
            _logger.exception("Erro ao autenticar conta Mercado Livre")
            return "Erro ao autenticar: %s" % str(e)

        return "Conta Mercado Livre conectada com sucesso. Você já pode fechar esta aba."
