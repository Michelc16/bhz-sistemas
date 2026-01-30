import logging
from datetime import timedelta

import requests
import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


ML_ORDERS_SEARCH_URL = "https://api.mercadolibre.com/orders/search"


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

    # ---------------------------------------------------------
    # Helpers de data / formatação
    # ---------------------------------------------------------
    def _iso_with_tz_offset(self, dt_utc, tz_name):
        """
        Recebe dt_utc (naive/utc) e devolve string ISO com offset do timezone (ex: -03:00).
        O ML lida melhor com offset explícito do que com "Z" em alguns cenários.
        """
        if not dt_utc:
            return None
        if isinstance(dt_utc, str):
            dt_utc = fields.Datetime.from_string(dt_utc)

        tz = pytz.timezone(tz_name or "UTC")

        # Odoo armazena datetime em UTC (naive). Vamos assumir UTC e converter pro tz.
        dt_utc = pytz.utc.localize(dt_utc)
        dt_local = dt_utc.astimezone(tz)

        # Formato: 2026-01-26T10:20:30.000-03:00
        s = dt_local.isoformat()
        if "." not in s:
            if s.endswith("Z"):
                s = s.replace("Z", ".000Z")
            else:
                s = s[:-6] + ".000" + s[-6:]
        return s

    def _prepare_orders_date_from_candidates(self, account):
        """
        Retorna uma lista de candidatos para 'order.date_created.from' (1º com offset local, 2º em UTC Z).
        Evita resultado vazio por diferença de timezone/offset.
        """
        last_order = self.search(
            [("account_id", "=", account.id)],
            order="date_created desc",
            limit=1,
        )

        if last_order and last_order.date_created:
            base_dt = last_order.date_created
            if isinstance(base_dt, str):
                base_dt = fields.Datetime.from_string(base_dt)
            # pega 10min antes pra não perder pedido em borda
            start_dt = base_dt - timedelta(minutes=10)
        else:
            # primeiro sync: últimos 15 dias (altere para 120 se quiser puxar histórico maior)
            now_dt = fields.Datetime.now()
            if isinstance(now_dt, str):
                now_dt = fields.Datetime.from_string(now_dt)
            start_dt = now_dt - timedelta(days=15)

        tz_name = (
            self.env.user.tz
            or (account.company_id and account.company_id.partner_id.tz)
            or "America/Sao_Paulo"
        )

        c1 = self._iso_with_tz_offset(start_dt, tz_name)

        # candidato 2: UTC com Z (fallback)
        start_dt_utc = pytz.utc.localize(start_dt)
        c2 = start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        out = []
        for c in [c1, c2]:
            if c and c not in out:
                out.append(c)
        return out

    def _ml_datetime_to_odoo(self, value):
        """
        Converte ISO 8601 do ML (ex: 2026-01-13T10:48:24.000-04:00)
        para string compatível com Odoo: 'YYYY-MM-DD HH:MM:SS' (UTC naive).
        """
        if not value:
            return False

        # datetime python
        if hasattr(value, "tzinfo"):
            dt = value
            if dt.tzinfo:
                dt = dt.astimezone(fields.Datetime.UTC).replace(tzinfo=None)
            return fields.Datetime.to_string(dt)

        if isinstance(value, str):
            s = value.strip()

            # Melhor caminho (normalmente disponível no Odoo)
            try:
                from dateutil.parser import isoparse  # type: ignore
                dt = isoparse(s)
                if getattr(dt, "tzinfo", None):
                    dt = dt.astimezone(fields.Datetime.UTC).replace(tzinfo=None)
                return fields.Datetime.to_string(dt)
            except Exception:
                pass

            # Fallback sem dateutil
            try:
                s2 = s.replace("T", " ")
                if s2.endswith("Z"):
                    s2 = s2[:-1]
                # corta timezone tipo -04:00 / +03:00
                if len(s2) >= 6 and (s2[-6] in ["+", "-"]) and s2[-3] == ":":
                    s2 = s2[:-6]
                # remove milissegundos
                if "." in s2:
                    s2 = s2.split(".")[0]

                # agora deve ficar 'YYYY-MM-DD HH:MM:SS'
                dt = fields.Datetime.from_string(s2)
                return fields.Datetime.to_string(dt)
            except Exception:
                _logger.warning("[ML] Não consegui converter datetime do ML: %r", value)
                return False

        return False

    # ---------------------------------------------------------
    # Chamadas API (com retry)
    # ---------------------------------------------------------
    def _ml_get(self, url, account, params=None, timeout=30):
        """
        GET com retry simples:
        - se 401: tenta renovar token e repete 1x
        """
        account.ensure_one()
        headers = {"Authorization": f"Bearer {account.access_token}"}

        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 401:
            _logger.warning("[ML] 401 (token). Tentando renovar token para conta %s...", account.name)
            account.refresh_access_token()
            headers = {"Authorization": f"Bearer {account.access_token}"}
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        return resp

    def _import_orders_for_account(self, account):
        """
        Busca pedidos no ML e cria registros meli.order.
        Corrige date_created ISO+timezone antes de salvar.
        """
        if not account.ml_user_id:
            _logger.warning("[ML] Conta %s sem ml_user_id. Pulei importação de pedidos.", account.name)
            return 0
        account.ensure_valid_token()

        imported = 0
        limit = 50

        date_from_candidates = self._prepare_orders_date_from_candidates(account)

        for date_from in date_from_candidates:
            offset = 0
            imported_this_candidate = 0

            _logger.warning("[ML] Conta %s: buscando pedidos a partir de %s", account.name, date_from)

            while True:
                params = {
                    "seller": str(account.ml_user_id),
                    "offset": offset,
                    "limit": limit,
                    "order.date_created.from": date_from,
                }

                try:
                    resp = self._ml_get(ML_ORDERS_SEARCH_URL, account, params=params, timeout=30)
                except requests.RequestException as exc:
                    _logger.exception(
                        "[ML] Conta %s: erro de rede ao buscar pedidos (offset %s): %s",
                        account.name,
                        offset,
                        exc,
                    )
                    break

                if resp.status_code != 200:
                    _logger.error(
                        "[ML] Conta %s: erro HTTP %s ao buscar pedidos (offset %s). Body: %s",
                        account.name,
                        resp.status_code,
                        offset,
                        (resp.text or "")[:2000],
                    )
                    break

                payload = resp.json() if resp.text else {}
                results = payload.get("results") or []

                if not results and offset == 0:
                    total = None
                    try:
                        total = (payload.get("paging") or {}).get("total")
                    except Exception:
                        total = None
                    _logger.warning(
                        "[ML] Conta %s: API retornou 0 pedidos (date_from=%s). paging.total=%s",
                        account.name,
                        date_from,
                        total,
                    )
                    break

                if not results:
                    break

                for ml_order in results:
                    order_id = str(ml_order.get("id"))
                    if not order_id or order_id == "None":
                        continue

                    exists = self.search(
                        [("name", "=", order_id), ("account_id", "=", account.id)],
                        limit=1,
                    )
                    if exists:
                        continue

                    buyer = ml_order.get("buyer") or {}
                    buyer_name = (
                        buyer.get("nickname")
                        or " ".join(filter(None, [buyer.get("first_name"), buyer.get("last_name")]))
                        or "Comprador Mercado Livre"
                    )

                    vals = {
                        "name": order_id,
                        "account_id": account.id,
                        "buyer_name": buyer_name,
                        "buyer_email": buyer.get("email"),
                        # ✅ CORREÇÃO: converte ISO com timezone -> formato Odoo
                        "date_created": self._ml_datetime_to_odoo(ml_order.get("date_created")),
                        "total_amount": ml_order.get("total_amount") or 0.0,
                        "status": ml_order.get("status"),
                        "raw_data": ml_order,
                    }

                    rec = self.create(vals)
                    imported += 1
                    imported_this_candidate += 1

                    try:
                        self._create_sale_order_from_meli(rec)
                    except Exception:
                        _logger.exception("[ML] Falha ao criar sale.order para pedido ML %s", order_id)

                if len(results) < limit:
                    break
                offset += limit

            if imported_this_candidate > 0:
                return imported_this_candidate

        return imported

    # ---------------------------------------------------------
    # Cron
    # ---------------------------------------------------------
    @api.model
    def cron_fetch_orders(self):
        """
        Cron que busca pedidos em todas as contas conectadas.
        Usa WARNING para garantir visibilidade no odoo.sh.
        """
        self = self.sudo()
        _logger.warning("[ML] (CRON) Iniciando importação de pedidos")

        accounts = self.env["meli.account"].sudo().search([("state", "=", "authorized")])
        if not accounts:
            _logger.warning("[ML] (CRON) Nenhuma conta autorizada encontrada para importar pedidos")
            return

        total_imported = 0

        for account in accounts:
            company = account.company_id or self.env.company
            order_model = self.with_company(company)
            account_ctx = account.with_company(company)

            try:
                account_ctx.ensure_valid_token()
            except Exception as exc:
                _logger.error("[ML] Conta %s: falha ao validar token: %s", account.name, exc)
                continue

            try:
                imported = order_model._import_orders_for_account(account_ctx)
                total_imported += imported
                _logger.warning("[ML] Conta %s: %s pedidos importados", account.name, imported)
            except Exception:
                _logger.exception("[ML] Erro inesperado ao importar pedidos da conta %s", account.name)
                account_ctx._record_error(str(exc))

        _logger.warning("[ML] (CRON) Importação finalizada. Total importado: %s", total_imported)

    # ---------------------------------------------------------
    # Sale Order básico
    # ---------------------------------------------------------
    def _create_sale_order_from_meli(self, meli_order):
        """
        Cria um sale.order simples a partir do pedido ML.
        (Mantive a sua abordagem)
        """
        partner = None
        if meli_order.buyer_email:
            partner = self.env["res.partner"].search(
                [
                    ("email", "=", meli_order.buyer_email),
                    ("company_id", "in", [False, meli_order.company_id.id]),
                ],
                limit=1,
            )
        if not partner:
            partner = self.env["res.partner"].create(
                {
                    "name": meli_order.buyer_name or "Cliente Mercado Livre",
                    "email": meli_order.buyer_email,
                }
            )

        so_vals = {
            "partner_id": partner.id,
            "origin": f"Mercado Livre {meli_order.name}",
            "company_id": meli_order.company_id.id if meli_order.company_id else False,
        }
        so = self.env["sale.order"].create(so_vals)
        meli_order.sale_order_id = so.id

    def action_manual_sync_orders(self):
        self.env["meli.order"].sudo().cron_fetch_orders()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mercado Livre",
                "message": "Sincronização de pedidos executada. Verifique os logs do servidor.",
                "type": "success",
                "sticky": False,
            },
        }
