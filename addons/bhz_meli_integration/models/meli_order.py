# bhz_meli_integration/models/meli_order.py
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MeliOrder(models.Model):
    _name = "meli.order"
    _description = "Pedido Mercado Livre"
    _order = "date_created desc"
    _check_company_auto = True

    name = fields.Char("Número ML", required=True, index=True)
    account_id = fields.Many2one("meli.account", string="Conta ML", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        related="account_id.company_id",
        store=True,
        readonly=True,
    )

    buyer_name = fields.Char("Comprador")
    buyer_email = fields.Char("E-mail")
    date_created = fields.Datetime("Data do pedido")
    total_amount = fields.Float("Total")
    status = fields.Char("Status ML")
    raw_data = fields.Json("Dados brutos")

    sale_order_id = fields.Many2one("sale.order", string="Pedido de Venda Odoo")

    @api.model
    def cron_fetch_orders(self):
        """Cron que busca os últimos pedidos de todas as contas conectadas."""
        accounts = self.env["meli.account"].search([("state", "=", "authorized")])
        for account in accounts:
            try:
                account.refresh_access_token()
            except Exception:
                _logger.exception("Não foi possível renovar token da conta %s", account.name)
                continue

            url = f"https://api.mercadolibre.com/orders/search?seller={account.ml_user_id}&order.status=paid"
            headers = {"Authorization": f"Bearer {account.access_token}"}
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                _logger.error("Erro ao buscar pedidos ML conta %s: %s", account.name, resp.text)
                continue

            payload = resp.json()
            for ml_order in payload.get("results", []):
                order_id = str(ml_order.get("id"))
                exists = self.search([("name", "=", order_id), ("account_id", "=", account.id)], limit=1)
                if exists:
                    continue

                buyer = ml_order.get("buyer", {})
                vals = {
                    "name": order_id,
                    "account_id": account.id,
                    "buyer_name": buyer.get("nickname") or buyer.get("first_name"),
                    "buyer_email": buyer.get("email"),
                    "date_created": ml_order.get("date_created"),
                    "total_amount": ml_order.get("total_amount"),
                    "status": ml_order.get("status"),
                    "raw_data": ml_order,
                }
                rec = self.create(vals)
                self._create_sale_order_from_meli(rec)

    def _create_sale_order_from_meli(self, meli_order):
        """Cria um sale.order simples a partir do pedido ML."""
        partner = None
        if meli_order.buyer_email:
            partner = self.env["res.partner"].search([("email", "=", meli_order.buyer_email)], limit=1)
        if not partner:
            partner = self.env["res.partner"].create({
                "name": meli_order.buyer_name or "Cliente Mercado Livre",
                "email": meli_order.buyer_email,
            })

        so_vals = {
            "partner_id": partner.id,
            "origin": f"Mercado Livre {meli_order.name}",
            "company_id": meli_order.company_id.id if meli_order.company_id else False,
        }
        so = self.env["sale.order"].create(so_vals)
        meli_order.sale_order_id = so.id
