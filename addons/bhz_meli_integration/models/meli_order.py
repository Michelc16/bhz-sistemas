# bhz_meli_integration/models/meli_order.py
import logging
from datetime import timedelta

import requests

from odoo import api, fields, models

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

    def _prepare_orders_date_from(self, account):
        """Compute the initial date filter for ML search."""
        last_order = self.search(
            [("account_id", "=", account.id)],
            order="date_created desc",
            limit=1,
        )
        if last_order and last_order.date_created:
            last_dt = last_order.date_created
            if isinstance(last_dt, str):
                last_dt = fields.Datetime.from_string(last_dt)
            start_dt = last_dt - timedelta(minutes=5)
        else:
            now_dt = fields.Datetime.now()
            if isinstance(now_dt, str):
                now_dt = fields.Datetime.from_string(now_dt)
            start_dt = now_dt - timedelta(days=7)
        return start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _import_orders_for_account(self, account):
        """Fetch orders from Mercado Livre for one account."""
        if not account.ml_user_id:
            _logger.warning("[ML] Conta %s sem ml_user_id. Pulei importação.", account.name)
            return 0

        headers = {"Authorization": f"Bearer {account.access_token}"}
        limit = 50
        offset = 0
        imported = 0
        date_from = self._prepare_orders_date_from(account)
        _logger.info("[ML] Conta %s: buscando pedidos a partir de %s", account.name, date_from)
        while True:
            params = {
                "seller": account.ml_user_id,
                "offset": offset,
                "limit": limit,
                "order.date_created.from": date_from,
                "sort": "date_created",
            }
            try:
                resp = requests.get(
                    "https://api.mercadolibre.com/orders/search",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                error_body = ""
                if getattr(exc, "response", None) is not None:
                    error_body = exc.response.text
                _logger.error(
                    "[ML] Conta %s: erro ao buscar pedidos (offset %s): %s %s",
                    account.name,
                    offset,
                    exc,
                    error_body,
                )
                break

            payload = resp.json()
            results = payload.get("results") or []
            if not results:
                break

            for ml_order in results:
                order_id = str(ml_order.get("id"))
                exists = self.search(
                    [("name", "=", order_id), ("account_id", "=", account.id)],
                    limit=1,
                )
                if exists:
                    continue

                buyer = ml_order.get("buyer") or {}
                vals = {
                    "name": order_id,
                    "account_id": account.id,
                    "buyer_name": (
                        buyer.get("nickname")
                        or " ".join(filter(None, [buyer.get("first_name"), buyer.get("last_name")]))
                        or "Comprador Mercado Livre"
                    ),
                    "buyer_email": buyer.get("email"),
                    "date_created": ml_order.get("date_created"),
                    "total_amount": ml_order.get("total_amount") or 0.0,
                    "status": ml_order.get("status"),
                    "raw_data": ml_order,
                }
                rec = self.create(vals)
                imported += 1
                try:
                    self._create_sale_order_from_meli(rec)
                except Exception:
                    _logger.exception("[ML] Falha ao criar pedido de venda no Odoo para %s", order_id)

            if len(results) < limit:
                break
            offset += limit

        return imported

    @api.model
    def cron_fetch_orders(self):
        """Cron que busca pedidos em todas as contas conectadas."""
        self = self.sudo()
        _logger.info("[ML] Iniciando importação de pedidos")
        total_imported = 0
        accounts = self.env["meli.account"].sudo().search([("state", "=", "authorized")])
        if not accounts:
            _logger.info("[ML] Nenhuma conta autorizada encontrada para importar pedidos")
            return

        for account in accounts:
            company = account.company_id or self.env.company
            order_model = self.with_company(company)
            account_ctx = account.with_company(company)
            try:
                account_ctx.ensure_valid_token()
            except Exception as exc:
                _logger.error("[ML] Conta %s: falha ao validar token (%s)", account.name, exc)
                continue

            try:
                imported = order_model._import_orders_for_account(account_ctx)
                total_imported += imported
                _logger.info("[ML] Conta %s: %s pedidos importados", account.name, imported)
            except Exception:
                _logger.exception("[ML] Erro inesperado ao importar pedidos da conta %s", account.name)

        _logger.info("[ML] Importação de pedidos finalizada. Total importado: %s", total_imported)

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
