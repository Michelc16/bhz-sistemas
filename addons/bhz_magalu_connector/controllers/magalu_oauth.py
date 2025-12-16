import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MagaluOAuthController(http.Controller):

    @http.route('/magalu/oauth/callback', type='http', auth='public', csrf=False)
    def magalu_oauth_callback(self, **kwargs):
        """Endpoint registrado no ID Magalu para concluir o OAuth."""
        code = kwargs.get("code")
        state = kwargs.get("state")
        error = kwargs.get("error")

        cfg_id = None
        config = None
        state_data = None
        try:
            state_data = self._parse_state(state) if state else None
            if state_data:
                cfg_id = int(state_data.get("cfg"))
        except Exception:
            _logger.warning("Magalu OAuth: state inválido: %s", state)

        if cfg_id:
            config = request.env["bhz.magalu.config"].sudo().browse(cfg_id)
            if not config.exists():
                config = None

        if error:
            error_description = kwargs.get("error_description") or ""
            extra = f" ({error_description})" if error_description else ""
            if config and error == "invalid_scope":
                message = _(
                    "ID Magalu rejeitou os scopes solicitados. Ajuste o parâmetro 'bhz_magalu.oauth_scopes' com scopes permitidos para este client e tente novamente. Erro original: %(err)s%(extra)s",
                    err=error,
                    extra=extra,
                )
            else:
                message = f"Erro retornado pelo Magalu: {error}{extra}"
            _logger.error("Magalu OAuth erro (%s): %s", cfg_id or "sem cfg", message)
            return message

        if not code or not state_data:
            return "Callback Magalu: faltando 'code' ou 'state'."

        if not config:
            return "Callback Magalu: configuração não encontrada."

        try:
            config._validate_state(state_data)
        except UserError as exc:
            return f"Callback Magalu: {exc.name or exc.args[0]}"
        except Exception:
            _logger.exception("Magalu OAuth: falha ao validar state (cfg %s)", config.id)
            return "Callback Magalu: falha ao validar o parâmetro state."

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
        if not state:
            raise ValueError("State vazio.")
        parts = {}
        for chunk in state.split("|"):
            if ":" in chunk:
                key, value = chunk.split(":", 1)
                parts[key] = value
        required = {"cfg", "url", "nonce", "sig"}
        if not required.issubset(parts.keys()):
            raise ValueError("State incompleto.")
        parts["url"] = (parts["url"] or "").rstrip("/")
        return parts
