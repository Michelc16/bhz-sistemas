# bhz_meli_integration/models/meli_product.py
import logging
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MeliProduct(models.Model):
    _name = "meli.product"
    _description = "Produto Mercado Livre"
    _check_company_auto = True

    name = fields.Char("Nome", required=True)
    account_id = fields.Many2one("meli.account", string="Conta ML", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        related="account_id.company_id",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one("product.product", string="Produto Odoo", required=True)
    meli_item_id = fields.Char("ID Anúncio ML", help="Ex.: MLB123456789")
    meli_permalink = fields.Char("Link do anúncio")
    sale_price = fields.Float("Preço de venda no ML")
    currency_id = fields.Many2one("res.currency", string="Moeda", default=lambda self: self.env.company.currency_id.id)

    def action_fetch_item(self):
        for rec in self:
            if not rec.meli_item_id:
                raise UserError(_("Informe o ID do anúncio do Mercado Livre."))
            account = rec.account_id
            account.refresh_access_token()
            url = f"https://api.mercadolibre.com/items/{rec.meli_item_id}"
            headers = {"Authorization": f"Bearer {account.access_token}"}
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise UserError(_("Erro ao buscar item no ML: %s") % resp.text)
            data = resp.json()
            rec.write({
                "name": data.get("title"),
                "meli_permalink": data.get("permalink"),
                "sale_price": data.get("price"),
            })
