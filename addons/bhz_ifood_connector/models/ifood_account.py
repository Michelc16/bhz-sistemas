import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta

_logger = logging.getLogger(__name__)

class BhzIFoodAccount(models.Model):
    _name = "bhz.ifood.account"
    _description = "Conta iFood (por empresa)"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)

    environment = fields.Selection([
        ("prod", "Produção"),
        ("sandbox", "Sandbox/Teste"),
    ], default="sandbox", required=True, tracking=True)

    # Credenciais do app (global do integrador, mas você pode permitir por conta também)
    client_id = fields.Char(string="Client ID", tracking=True)
    client_secret = fields.Char(string="Client Secret")

    # Merchant/Loja (identificador que o iFood fornece / vinculação)
    merchant_id = fields.Char(string="Merchant ID", tracking=True)

    # Tokens OAuth
    access_token = fields.Text()
    refresh_token = fields.Text()
    token_expires_at = fields.Datetime()

    # Webhook
    webhook_enabled = fields.Boolean(default=False, tracking=True)
    webhook_secret = fields.Char(
        string="Webhook Secret (para validar assinatura)",
        help="Use para validar o X-IFood-Signature conforme a doc do iFood."
    )

    last_sync_at = fields.Datetime(tracking=True)
    last_error = fields.Text()

    def action_test_connection(self):
        for rec in self:
            client = rec._client()
            client.ensure_token()
            # ping simples: você troca por um endpoint real da sua categoria
            ok = client.ping()
            if not ok:
                raise UserError(_("Falha ao testar conexão com iFood. Verifique credenciais/token."))
        return True

    def _client(self):
        self.ensure_one()
        return self.env["bhz.ifood.client"].with_context(ifood_account_id=self.id)

    def _get_base_url(self):
        # ATENÇÃO: ajuste conforme “API Reference” da sua categoria (FOOD / Mercado etc.)
        # Mantive genérico por segurança: o client monta rotas.
        if self.environment == "prod":
            return "https://merchant-api.ifood.com.br"  # exemplo comum em integrações
        return "https://merchant-api.ifood.com.br"     # sandbox pode variar conforme portal
    
    def _cron_sync_orders(self):
        for acc in self.search([("active", "=", True)]):
            try:
                client = acc._client()
                # janela simples: últimos 10 minutos
                since = (fields.Datetime.now() - timedelta(minutes=10)).isoformat()
                data = client.fetch_orders_since(since)
                # TODO: parse real e criar bhz.ifood.order por pedido
                acc.last_sync_at = fields.Datetime.now()
                acc.last_error = False
            except Exception as e:
                acc.last_error = str(e)
