import requests
from odoo import http
from odoo.http import request


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

        config = request.env['bhz.magalu.config'].sudo().browse(int(config_id))
        if not config.exists():
            return "Configuração Magalu não encontrada."

        ICP = request.env["ir.config_parameter"].sudo()
        client_id = ICP.get_param("bhz_magalu.client_id")
        client_secret = ICP.get_param("bhz_magalu.client_secret")
        redirect_uri = ICP.get_param("bhz_magalu.redirect_uri")

        if not all([client_id, client_secret, redirect_uri]):
            return "Parâmetros Magalu incompletos (client_id, client_secret ou redirect_uri)."

        token_url = "https://id.magalu.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            resp = requests.post(token_url, data=data, timeout=30)
        except Exception as e:
            return f"Erro ao conectar no Magalu: {str(e)}"

        if resp.status_code != 200:
            return f"Erro do Magalu ({resp.status_code}): {resp.text}"

        token_data = resp.json()
        # usa o helper do modelo pra gravar expiração como datetime
        config.sudo().write_tokens(token_data)

        # volta pro formulário de configuração
        return request.redirect(f"/web#id={config.id}&model=bhz.magalu.config&view_type=form")
