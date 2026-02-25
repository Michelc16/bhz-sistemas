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
    meli_item_id = fields.Char("ID Anúncio ML", help="Ex.: MLB123456789", index=True)
    meli_permalink = fields.Char("Link do anúncio")
    sale_price = fields.Float("Preço de venda no ML")
    currency_id = fields.Many2one(
        "res.currency",
        string="Moeda",
        default=lambda self: self.env.company.currency_id.id,
    )

    # ---------------------------------------------------------
    # HTTP helpers
    # ---------------------------------------------------------
    def _ml_get(self, url, account, params=None, timeout=30):
        """GET com fallback de refresh_token quando vier 401."""
        account.ensure_one()
        headers = {"Authorization": f"Bearer {account.access_token}"}

        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 401:
            _logger.warning("[ML] 401 no GET. Renovando token da conta %s e tentando novamente...", account.name)
            account.refresh_access_token()
            headers = {"Authorization": f"Bearer {account.access_token}"}
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        return resp

    # ---------------------------------------------------------
    # Produto Odoo (criação compatível com Odoo 19)
    # ---------------------------------------------------------
    def _find_product_variant(self, account, seller_sku, fallback_code):
        Product = self.env["product.product"].sudo().with_company(account.company_id)
        domain = [("company_id", "=", account.company_id.id)]

        code = seller_sku or fallback_code
        if code:
            domain.append(("default_code", "=", code))

        return Product.search(domain, limit=1)

    def _create_product_variant(self, account, item_data):
        """
        Cria produto no Odoo de forma compatível com Odoo 19:
        - NÃO usa product.template.type='product' (dá erro)
        - Usa detailed_type='product' quando existir
        - Cria template e pega a variante
        """
        company = account.company_id
        ProductTmpl = self.env["product.template"].sudo().with_company(company)

        seller_sku = item_data.get("seller_sku")
        item_id = item_data.get("id") or ""
        title = item_data.get("title") or item_id or "Produto Mercado Livre"

        tmpl_vals = {
            "name": title,
            "company_id": company.id,
        }

        # SKU vai em product.product.default_code (mas pode ser propagado por create se passado no context)
        # O jeito mais compatível é criar o template e depois escrever no variant.
        if "detailed_type" in ProductTmpl._fields:
            tmpl_vals["detailed_type"] = "product"
        # Se não existir detailed_type, NÃO setar type (pra não quebrar em versões onde 'product' não existe)

        tmpl = ProductTmpl.create(tmpl_vals)

        variant = tmpl.product_variant_id.sudo().with_company(company)
        # define default_code na variante
        code = seller_sku or item_id
        if code:
            variant.write({"default_code": code})

        return variant

    def _get_or_create_product_variant(self, account, item_data):
        seller_sku = item_data.get("seller_sku")
        item_id = item_data.get("id") or ""
        product = self._find_product_variant(account, seller_sku, item_id)
        if product:
            return product
        return self._create_product_variant(account, item_data)

    # ---------------------------------------------------------
    # Ações
    # ---------------------------------------------------------
    def action_fetch_item(self):
        for rec in self:
            if not rec.meli_item_id:
                raise UserError(_("Informe o ID do anúncio do Mercado Livre."))

            account = rec.account_id
            account.ensure_valid_token()

            url = f"https://api.mercadolibre.com/items/{rec.meli_item_id}"
            resp = self._ml_get(url, account, timeout=30)
            if resp.status_code != 200:
                raise UserError(_("Erro ao buscar item no ML: %s") % (resp.text or resp.status_code))

            data = resp.json()
            rec.write(
                {
                    "name": data.get("title") or rec.name,
                    "meli_permalink": data.get("permalink"),
                    "sale_price": data.get("price") or 0.0,
                }
            )

    def _cron_fetch_items_impl(self):
        """Implementação compartilhada do cron de anúncios."""
        self = self.sudo()
        _logger.warning("[ML] (CRON) Iniciando importação de anúncios")

        accounts = self.env["meli.account"].sudo().search(
            [
                ("state", "in", ["connected", "authorized"]),
                ("access_token", "!=", False),
            ]
        )
        if not accounts:
            _logger.warning("[ML] (CRON) Nenhuma conta conectada encontrada para importar anúncios")
            return

        Currency = self.env["res.currency"].sudo()
        total_imported = 0
        total_updated = 0

        for account in accounts:
            company = account.company_id or self.env.company
            account_ctx = account.with_company(company)

            try:
                account_ctx.ensure_valid_token()
            except Exception as exc:
                _logger.error("[ML] Conta %s: falha ao validar token (%s)", account_ctx.name, exc)
                account_ctx._record_error(str(exc))
                continue

            if not account_ctx.ml_user_id:
                _logger.warning("[ML] Conta %s sem ml_user_id. Pulei importação de itens.", account_ctx.name)
                continue

            account_imported = 0
            account_updated = 0

            limit = 50
            offset = 0

            search_url = f"https://api.mercadolibre.com/users/{account_ctx.ml_user_id}/items/search"
            while True:
                params = {"search_type": "scan", "offset": offset, "limit": limit}
                resp = self._ml_get(search_url, account_ctx, params=params, timeout=30)

                if resp.status_code != 200:
                    _logger.error(
                        "[ML] Conta %s: erro HTTP %s ao buscar anúncios: %s",
                        account_ctx.name,
                        resp.status_code,
                        (resp.text or "")[:2000],
                    )
                    break

                payload = resp.json() if resp.text else {}
                item_ids = payload.get("results") or []
                if not item_ids:
                    break

                for item_id in item_ids:
                    item_url = f"https://api.mercadolibre.com/items/{item_id}"
                    item_resp = self._ml_get(item_url, account_ctx, timeout=30)

                    if item_resp.status_code != 200:
                        _logger.error(
                            "[ML] Conta %s: erro ao buscar item %s: %s",
                            account_ctx.name,
                            item_id,
                            (item_resp.text or "")[:2000],
                        )
                        continue

                    item_data = item_resp.json()
                    item_data["id"] = item_id  # garante

                    # moeda
                    currency_id = company.currency_id.id
                    currency_code = item_data.get("currency_id")
                    if currency_code:
                        currency = Currency.search([("name", "=", currency_code)], limit=1)
                        if currency:
                            currency_id = currency.id

                    # produto odoo (VARIANTE)
                    try:
                        product_variant = self._get_or_create_product_variant(account_ctx, item_data)
                    except Exception:
                        _logger.exception(
                            "[ML] Conta %s: falha ao criar/obter produto Odoo do item %s",
                            account_ctx.name,
                            item_id,
                        )
                        continue

                    vals = {
                        "name": item_data.get("title") or item_id,
                        "account_id": account_ctx.id,
                        "product_id": product_variant.id,
                        "meli_item_id": item_id,
                        "meli_permalink": item_data.get("permalink"),
                        "sale_price": item_data.get("price") or 0.0,
                        "currency_id": currency_id,
                    }

                    record = self.search(
                        [("account_id", "=", account_ctx.id), ("meli_item_id", "=", item_id)],
                        limit=1,
                    )
                    if record:
                        record.write(vals)
                        account_updated += 1
                        total_updated += 1
                    else:
                        self.create(vals)
                        account_imported += 1
                        total_imported += 1

                if len(item_ids) < limit:
                    break
                offset += limit

            _logger.warning(
                "[ML] Conta %s: %s anúncios criados, %s atualizados",
                account_ctx.name,
                account_imported,
                account_updated,
            )

        _logger.warning(
            "[ML] (CRON) Importação de anúncios finalizada. Criados: %s | Atualizados: %s",
            total_imported,
            total_updated,
        )

    @api.model
    def cron_fetch_items(self):
        """Cron oficial (nome atual)."""
        return self._cron_fetch_items_impl()

    @api.model
    def cron_fetch_products(self):
        """Compatibilidade com ações/cron antigas."""
        return self._cron_fetch_items_impl()

    def action_manual_sync_products(self):
        """Botão manual para sincronizar anúncios do Mercado Livre."""
        self.env["meli.product"].sudo().cron_fetch_products()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mercado Livre",
                "message": "Sincronização de anúncios executada. Verifique os logs do servidor.",
                "type": "success",
                "sticky": False,
            },
        }
