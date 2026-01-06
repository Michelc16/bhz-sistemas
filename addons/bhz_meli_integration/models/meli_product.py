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

    @api.model
    def cron_fetch_items(self):
        _logger.info("[ML] Iniciando importação de anúncios")
        accounts = self.env["meli.account"].sudo().search([("state", "=", "authorized")])
        total_imported = 0
        if not accounts:
            _logger.info("[ML] Nenhuma conta autorizada encontrada para importar anúncios")
            return

        Product = self.env["product.product"].sudo()
        Currency = self.env["res.currency"].sudo()

        for account in accounts:
            account_imported = 0
            try:
                account.ensure_valid_token()
            except Exception as exc:
                _logger.error("[ML] Conta %s: falha ao validar token (%s)", account.name, exc)
                continue

            if not account.ml_user_id:
                _logger.warning("[ML] Conta %s sem ml_user_id. Pulei importação de itens.", account.name)
                continue

            headers = {"Authorization": f"Bearer {account.access_token}"}
            limit = 50
            offset = 0
            while True:
                params = {
                    "search_type": "scan",
                    "offset": offset,
                    "limit": limit,
                }
                search_url = f"https://api.mercadolibre.com/users/{account.ml_user_id}/items/search"
                resp = requests.get(search_url, headers=headers, params=params, timeout=30)
                if resp.status_code != 200:
                    _logger.error(
                        "[ML] Conta %s: erro HTTP %s ao buscar anúncios: %s",
                        account.name,
                        resp.status_code,
                        resp.text,
                    )
                    break

                payload = resp.json()
                item_ids = payload.get("results") or []
                if not item_ids:
                    break

                for item_id in item_ids:
                    item_url = f"https://api.mercadolibre.com/items/{item_id}"
                    item_resp = requests.get(item_url, headers=headers, timeout=30)
                    if item_resp.status_code != 200:
                        _logger.error(
                            "[ML] Conta %s: erro ao buscar item %s: %s",
                            account.name,
                            item_id,
                            item_resp.text,
                        )
                        continue

                    item_data = item_resp.json()
                    currency = None
                    currency_code = item_data.get("currency_id")
                    if currency_code:
                        currency = Currency.search([("name", "=", currency_code)], limit=1)

                    # Garante que existe um produto Odoo
                    seller_sku = item_data.get("seller_sku") or item_id
                    domain = [("company_id", "=", account.company_id.id)]
                    if seller_sku:
                        domain.append(("default_code", "=", seller_sku))
                    product = Product.search(domain, limit=1)
                    if not product:
                        product = Product.create(
                            {
                                "name": item_data.get("title") or item_id,
                                "default_code": item_data.get("seller_sku") or item_id,
                                "company_id": account.company_id.id,
                                "type": "product",
                            }
                        )

                    currency_id = currency.id if currency else account.company_id.currency_id.id
                    vals = {
                        "name": item_data.get("title") or item_id,
                        "account_id": account.id,
                        "product_id": product.id,
                        "meli_item_id": item_id,
                        "meli_permalink": item_data.get("permalink"),
                        "sale_price": item_data.get("price") or 0.0,
                        "currency_id": currency_id,
                    }
                    record = self.search(
                        [("account_id", "=", account.id), ("meli_item_id", "=", item_id)], limit=1
                    )
                    if record:
                        record.write(vals)
                    else:
                        self.create(vals)
                        account_imported += 1
                        total_imported += 1

                if len(item_ids) < limit:
                    break
                offset += limit

            _logger.info("[ML] Conta %s: %s anúncios sincronizados", account.name, account_imported)

        _logger.info("[ML] Importação de anúncios finalizada. Total sincronizado: %s", total_imported)

    def action_manual_sync_products(self):
        """Botão manual para sincronizar anúncios do Mercado Livre."""
        self.env["meli.product"].sudo().cron_fetch_items()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mercado Livre",
                "message": "Sincronização de produtos iniciada em segundo plano.",
                "type": "success",
                "sticky": False,
            },
        }
