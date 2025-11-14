import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MagaluOAuthController(http.Controller):

    @http.route('/magalu/oauth/callback', type='http', auth='public', csrf=False)
    def magalu_oauth_callback(self, **kwargs):
        """Endpoint registrado no ID Magalu para concluir o OAuth."""
        code = kwargs.get("code")
        state = kwargs.get("state")
        error = kwargs.get("error")

        if error:
            return f"Erro retornado pelo Magalu: {error}"
        if not code or not state:
            return "Callback Magalu: faltando 'code' ou 'state'."

        try:
            cfg_id, state_base = self._parse_state(state)
        except ValueError:
            return "Callback Magalu: parâmetro state inválido."

        config = request.env["bhz.magalu.config"].sudo().browse(cfg_id)
        if not config.exists():
            return "Callback Magalu: configuração não encontrada."

        try:
            expected_base = config._get_base_url()
        except UserError as exc:
            message = exc.name or (exc.args and exc.args[0]) or "Configuração inválida."
            return f"Callback Magalu: {message}"
        if state_base != expected_base:
            return "Callback Magalu: state não corresponde a esta instância."

        try:
            request.env["bhz.magalu.api"].sudo()._exchange_code_for_token(config, code)
        except UserError as exc:
            message = exc.name or (exc.args and exc.args[0]) or "Erro desconhecido."
            _logger.error("Falha ao finalizar OAuth Magalu (cfg %s): %s", cfg_id, message)
            return f"Erro ao finalizar OAuth Magalu: {message}"
        except Exception:  # pragma: no cover
            _logger.exception("Erro inesperado ao finalizar OAuth Magalu (cfg %s)", cfg_id)
            return "Erro inesperado ao finalizar OAuth Magalu. Consulte os logs."

        return request.redirect(f"/web#id={config.id}&model=bhz.magalu.config&view_type=form")

    @staticmethod
    def _parse_state(state):
        parts = dict(item.split(":", 1) for item in state.split("|") if ":" in item)
        cfg_id = parts.get("cfg")
        base_url = (parts.get("url") or "").strip()
        if not cfg_id or not base_url:
            raise ValueError("State incompleto.")
        return int(cfg_id), base_url.rstrip("/")
