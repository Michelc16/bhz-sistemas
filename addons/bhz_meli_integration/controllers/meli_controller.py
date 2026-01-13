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
        state = kwargs.get("state")
        _logger.info("[ML][OAuth] Callback recebido. code? %s | state=%s", bool(code), state)

        if not code or not state:
            return "Faltou o code/state do Mercado Livre. Gere a autorização novamente."

        try:
            account_id = int(state.split(":", 1)[0])
        except Exception:
            _logger.warning("[ML][OAuth] State inválido recebido: %s", state)
            return "State inválido recebido. Gere a autorização novamente."

        account = request.env["meli.account"].sudo().browse(account_id)
        if not account or not account.exists():
            return "Conta do Mercado Livre não encontrada."

        try:
            account = account.sudo().with_company(account.company_id)
            account.exchange_code_for_token(code, state=state)
        except Exception as e:
            _logger.exception("[ML][OAuth] Erro ao autenticar conta Mercado Livre %s", account.display_name)
            try:
                account._record_error(str(e))
            except Exception:
                _logger.debug("Não foi possível registrar erro na conta ML", exc_info=True)
            return "Erro ao autenticar: %s" % str(e)

        return "Conta Mercado Livre conectada com sucesso. Você já pode fechar esta aba."
