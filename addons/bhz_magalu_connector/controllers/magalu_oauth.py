import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MagaluOAuthController(http.Controller):

    @http.route('/magalu/oauth/callback', type='http', auth='public', csrf=False)
    def magalu_oauth_callback(self, **kwargs):
        """
        O Magalu chama ESTE endpoint depois que o usuário loga e autoriza.
        Aqui a gente só lê o state pra saber qual é o Odoo do cliente
        e redireciona pra base dele, passando o code.
        """
        code = kwargs.get('code')
        state = kwargs.get('state')
        error = kwargs.get('error')

        if error:
            return f"Erro retornado pelo Magalu: {error}"

        if not code or not state:
            return "Callback Magalu: faltando 'code' ou 'state'."

        # state veio assim: "cfg:12|url:https://cliente.odoo.sh"
        parts = dict(item.split(":", 1) for item in state.split("|") if ":" in item)
        target_url = parts.get("url")
        cfg_id = parts.get("cfg")

        if not target_url:
            return "Callback Magalu: não foi possível identificar o Odoo do cliente."

        # manda o usuário pro Odoo do cliente terminar a troca
        redirect_url = f"{target_url}/magalu/oauth/finish?code={code}&config_id={cfg_id}"
        _logger.debug("Redirecting Magalu OAuth callback to %s", redirect_url)
        return request.redirect(redirect_url)


class MagaluOAuthFinishController(http.Controller):

    @http.route('/magalu/oauth/finish', type='http', auth='public', csrf=False)
    def magalu_oauth_finish(self, code=None, config_id=None, **kwargs):
        """
        Aqui a gente já está dentro do Odoo do cliente.
        Troca o code por token no Magalu e salva na bhz.magalu.config.
        """
        if not code or not config_id:
            return "Faltando parâmetros: code ou config_id."

        try:
            cfg_id_int = int(config_id)
        except (TypeError, ValueError):
            return "Config ID inválido."

        config = request.env['bhz.magalu.config'].sudo().browse(cfg_id_int)
        if not config.exists():
            return "Configuração Magalu não encontrada."

        try:
            request.env['bhz.magalu.api'].sudo().exchange_code_for_token(config, code)
        except UserError as exc:
            _logger.error("Falha ao finalizar OAuth Magalu: %s", exc.name or exc.args[0])
            return f"Erro ao finalizar OAuth Magalu: {exc.name or exc.args[0]}"
        except Exception as exc:  # pragma: no cover - proteção extra
            _logger.exception("Erro inesperado ao finalizar OAuth Magalu")
            return f"Erro inesperado ao finalizar OAuth Magalu: {str(exc)}"

        # volta pro formulário de configuração
        return request.redirect(f"/web#id={config.id}&model=bhz.magalu.config&view_type=form")
