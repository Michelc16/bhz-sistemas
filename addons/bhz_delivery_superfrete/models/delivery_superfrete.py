# -*- coding: utf-8 -*-
import logging
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SuperFreteConfig(models.Model):
    _name = "bhz.superfrete.config"
    _description = "Config SuperFrete"
    _rec_name = "name"

    name = fields.Char(default="Config SuperFrete", required=True)
    api_key = fields.Char("API Key", required=True)
    sandbox = fields.Boolean("Sandbox", default=True)
    base_url = fields.Char(
        "Base URL",
        help="Ex.: https://sandbox.superfrete.com (Sandbox) ou https://api.superfrete.com (Produção)"
    )
    user_agent = fields.Char(
        "User-Agent",
        help="Obrigatório p/ SuperFrete. Ex.: BHZ-Odoo/19 (suporte@bhzsistemas.com.br)",
        default="BHZ-Odoo/19 (suporte@bhzsistemas.com.br)"
    )
    default_services = fields.Char(
        "Serviços p/ Cotação",
        help="String de serviços: ex. '1,2,17' (PAC, SEDEX, Mini Envios). Se vazio, usa '1,2'",
        default="1,2"
    )

    @api.model
    def get_conf(self):
        rec = self.search([], limit=1)
        return rec or self.create({"name": "Config SuperFrete"})


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    # registra o provedor no dropdown de "Tipo de entrega"
    delivery_type = fields.Selection(
        selection_add=[("superfrete", "SuperFrete")],
        ondelete={"superfrete": "set default"},
    )
    superfrete_config_id = fields.Many2one(
        "bhz.superfrete.config",
        string="Configuração SuperFrete",
        ondelete="set null",
    )
    # serviço único quando gerar etiqueta
    superfrete_service = fields.Selection(
        selection=[
            ("1", "PAC"),
            ("2", "SEDEX"),
            ("17", "Mini Envios"),
            ("3", "Jadlog.Package"),
            ("31", "Loggi Econômico"),
        ],
        string="Serviço p/ Etiqueta"
    )

    # ---------------- helpers de config/headers/urls ----------------
    def _sf_conf(self):
        conf = (self.superfrete_config_id or self.env["bhz.superfrete.config"].get_conf())
        if not conf.api_key:
            raise UserError(_("Configure a API Key do SuperFrete."))
        return conf

    def _sf_base(self):
        conf = self._sf_conf()
        if conf.base_url:
            return conf.base_url.rstrip("/")
        return "https://sandbox.superfrete.com" if conf.sandbox else "https://api.superfrete.com"

    def _sf_headers(self):
        conf = self._sf_conf()
        return {
            "Authorization": f"Bearer {conf.api_key}",
            "User-Agent": conf.user_agent or "BHZ-Odoo/19 (suporte@bhzsistemas.com.br)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    # ---------------- util: normalização/validação ----------------
    @staticmethod
    def _sf_norm_cep(zip_str):
        return (zip_str or "").replace("-", "").strip()

    def _sf_validate_calc_payload(self, payload):
        errors = []
        for side in ("from", "to"):
            pc = payload.get(side, {}).get("postal_code")
            if not pc or not pc.isdigit() or len(pc) != 8:
                errors.append(f"CEP {side} inválido: {pc!r}")
        services = payload.get("services")
        if isinstance(services, list):
            if not services:
                errors.append("Services deve ser lista de códigos: ex. ['1', '2']")
        elif isinstance(services, str):
            if not services.strip():
                errors.append("Services deve ser string com códigos separados por vírgula.")
        else:
            errors.append("Services deve ser string ou lista de códigos.")
        prods = payload.get("products")
        if not isinstance(prods, list) or not prods:
            errors.append("products deve ser lista não vazia.")
        else:
            for i, pr in enumerate(prods):
                for k in ("uid", "quantity", "weight", "height", "width", "length"):
                    if pr.get(k) in (None, "", 0):
                        errors.append(f"products[{i}].{k} obrigatório")
                for k in ("quantity", "weight", "height", "width", "length"):
                    try:
                        val = float(pr.get(k, 0))
                    except Exception:
                        val = 0.0
                    if val <= 0:
                        errors.append(f"products[{i}].{k} deve ser > 0")
        return errors

    @staticmethod
    def _sf_dim(value, minimum):
        try:
            val = float(value or 0.0)
        except Exception:
            val = 0.0
        return max(val, minimum)

    def _sf_prepare_products(self, order):
        items = []
        for idx, line in enumerate(order.order_line, start=1):
            product = line.product_id
            qty = int(line.product_uom_qty or 0)
            if not product or line.is_delivery or qty <= 0:
                continue
            items.append({
                "uid": product.default_code or f"item-{product.id or idx}",
                "quantity": qty,
                "weight": round(self._sf_dim(getattr(product, "weight", 0.0), 0.01), 3),
                "height": round(self._sf_dim(getattr(product, "height", 0.0), 1.0), 2),
                "width": round(self._sf_dim(getattr(product, "width", 0.0), 1.0), 2),
                "length": round(self._sf_dim(getattr(product, "length", 0.0), 1.0), 2),
                "insurance_value": round(float(line.price_subtotal or 0.0), 2),
            })
        if not items:
            total_weight = sum(
                (l.product_uom_qty or 0.0) * (l.product_id.weight or 0.0)
                for l in order.order_line
                if l.product_id and not l.is_delivery
            ) or 0.01
            items.append({
                "uid": "fallback-1",
                "quantity": 1,
                "weight": round(self._sf_dim(total_weight, 0.01), 3),
                "height": 10.0,
                "width": 20.0,
                "length": 30.0,
                "insurance_value": round(float(order.amount_untaxed or 0.0), 2),
            })
        return items

    # ---------------- COTAÇÃO (SO) ----------------
    def superfrete_rate_shipment(self, order):
        self.ensure_one()

        origin = order.warehouse_id.partner_id or order.company_id.partner_id
        dest = order.partner_shipping_id

        # Brasil + CEPS
        if (origin.country_id and origin.country_id.code != "BR") or (dest.country_id and dest.country_id.code != "BR"):
            return {"success": False, "price": 0.0, "error_message": _("SuperFrete atende apenas CEPs do Brasil."), "warning_message": False}

        cep_from = self._sf_norm_cep(origin.zip)
        cep_to = self._sf_norm_cep(dest.zip)
        if not cep_from or not cep_to:
            return {"success": False, "price": 0.0, "error_message": _("Preencha CEP de origem e destino."), "warning_message": False}

        conf = self._sf_conf()
        if conf.default_services:
            services = [
                s.strip()
                for s in conf.default_services.split(",")
                if s.strip()
            ] or ["1", "2"]
        else:
            services = ["1", "2"]

        # API espera string separada por vírgula
        services_str = ",".join(services)

        products = self._sf_prepare_products(order)

        payload = {
            "from": {"postal_code": cep_from},
            "to":   {"postal_code": cep_to},
            "services": services_str,
            "options": {
                "own_hand": False,
                "receipt": False,
                "insurance_value": 0,
                "use_insurance_value": False,
            },
        }
        payload["products"] = products

        errs = self._sf_validate_calc_payload(payload)
        if errs:
            msg = " / ".join(errs)
            return {"success": False, "price": 0.0, "error_message": _("Payload inválido p/ SuperFrete: %s") % msg, "warning_message": False}

        try:
            url = f"{self._sf_base()}/api/v0/calculator"
            headers = self._sf_headers()
            _logger.info("SF calculator POST %s\nheaders=%s\npayload=%s", url, headers, payload)
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            _logger.info("SF calculator RESPONSE %s %s", res.status_code, res.text)

            if res.status_code >= 400:
                raise UserError(_("SuperFrete retornou erro %s: %s") % (res.status_code, res.text))

            data = res.json()
            offers = data if isinstance(data, list) else data.get("offers") or []
            if not offers:
                return {"success": False, "price": 0.0, "error_message": _("Sem ofertas retornadas."), "warning_message": False}

            offers = sorted(offers, key=lambda o: float(o.get("price", 0) or 0))
            price = float(offers[0].get("price", 0.0))
            if price <= 0:
                return {"success": False, "price": 0.0, "error_message": _("Oferta sem preço (>0)."), "warning_message": False}

            return {"success": True, "price": price, "error_message": False, "warning_message": False}

        except UserError:
            raise
        except Exception as e:
            _logger.exception("Falha na cotação SuperFrete")
            return {"success": False, "price": 0.0, "error_message": str(e), "warning_message": False}

    # ---------------- ENVIO / ETIQUETA (Pickings) ----------------
    def superfrete_send_shipping(self, pickings):
        self.ensure_one()
        results = []
        conf = self._sf_conf()

        if not self.superfrete_service:
            raise UserError(_("Selecione 'Serviço p/ Etiqueta' no método de entrega SuperFrete."))

        for picking in pickings:
            origin = (picking.picking_type_id.warehouse_id.partner_id or picking.company_id.partner_id)
            dest = picking.partner_id
            products = []
            for idx, ml in enumerate(picking.move_line_ids, start=1):
                product = ml.product_id
                qty = int(ml.qty_done or ml.product_uom_qty or 0)
                if not product or qty <= 0:
                    continue
                insurance = 0.0
                if ml.sale_line_id:
                    insurance = ml.sale_line_id.currency_id._convert(
                        ml.sale_line_id.price_subtotal,
                        picking.company_id.currency_id,
                        picking.company_id,
                        fields.Date.today(),
                    )
                products.append({
                    "uid": product.default_code or f"item-{product.id or idx}",
                    "quantity": qty,
                    "weight": round(self._sf_dim(getattr(product, "weight", 0.0), 0.01), 3),
                    "height": round(self._sf_dim(getattr(product, "height", 0.0), 1.0), 2),
                    "width": round(self._sf_dim(getattr(product, "width", 0.0), 1.0), 2),
                    "length": round(self._sf_dim(getattr(product, "length", 0.0), 1.0), 2),
                    "insurance_value": round(float(insurance or 0.0), 2),
                })

            if not products:
                total_weight = sum(
                    (ml.product_id.weight or 0.0) * (ml.qty_done or 0.0)
                    for ml in picking.move_line_ids
                ) or 0.01
                products = [{
                    "uid": "fallback-1",
                    "quantity": 1,
                    "weight": round(self._sf_dim(total_weight, 0.01), 3),
                    "height": 10.0,
                    "width": 20.0,
                    "length": 30.0,
                    "insurance_value": round(float(picking.sale_id.amount_untaxed or 0.0), 2),
                }]

            payload = {
                "from": {
                    "name": (origin.name or "Loja BHZ"),
                    "address": origin.street or "",
                    "number": "",
                    "district": getattr(origin, "l10n_br_district", None) or "NA",
                    "city": origin.city or "",
                    "state_abbr": origin.state_id and origin.state_id.code or "",
                    "postal_code": self._sf_norm_cep(origin.zip),
                    "email": origin.email or None,
                },
                "to": {
                    "name": (dest.name or "Cliente"),
                    "address": dest.street or "",
                    "number": "",
                    "district": getattr(dest, "l10n_br_district", None) or "NA",
                    "city": dest.city or "",
                    "state_abbr": dest.state_id and dest.state_id.code or "",
                    "postal_code": self._sf_norm_cep(dest.zip),
                    "email": dest.email or "cliente@exemplo.com",
                },
                "service": self.superfrete_service,  # um serviço específico
                "products": products,
                "options": {
                    "insurance_value": None,
                    "receipt": False,
                    "own_hand": False,
                    "non_commercial": True,
                },
                "tag": picking.name,
                "platform": "Odoo 19 - BHZ Sistemas",
                "url": self.env["ir.config_parameter"].sudo().get_param("web.base.url"),
            }

            try:
                url = f"{self._sf_base()}/api/v0/cart"
                _logger.info("SF cart POST %s payload=%s", url, payload)
                res = requests.post(url, json=payload, headers=self._sf_headers(), timeout=30)
                _logger.info("SF cart %s %s", res.status_code, res.text)
                res.raise_for_status()
                data = res.json()

                order_id = data.get("id") or data.get("order") or data.get("order_id")
                price = float(data.get("price", 0.0))
                # tracking só após checkout (released)
                picking.carrier_tracking_ref = None

                # anexa um .url com o link de impressão (via /api/v0/tag/print)
                if order_id:
                    url_print = self._superfrete_label_url(order_id)
                    if url_print:
                        self.env["ir.attachment"].create({
                            "name": f"Etiqueta_Link_{picking.name}.url",
                            "type": "url",
                            "url": url_print,
                            "res_model": "stock.picking",
                            "res_id": picking.id,
                        })

                results.append({"exact_price": price, "tracking_number": None})
            except Exception as e:
                _logger.exception("Erro criando etiqueta SuperFrete")
                results.append({"exact_price": 0.0, "tracking_number": False, "error_message": str(e)})
        return results

    def _superfrete_label_url(self, order_id):
        try:
            url = f"{self._sf_base()}/api/v0/tag/print"
            payload = {"orders": order_id}
            res = requests.post(url, json=payload, headers=self._sf_headers(), timeout=30)
            res.raise_for_status()
            data = res.json()
            return data.get("url") or data.get("link") or ""
        except Exception:
            _logger.exception("Erro obtendo link de etiqueta no SuperFrete")
            return ""

    # (Opcional) checkout (paga etiqueta com saldo)
    def action_superfrete_checkout(self, order_id):
        url = f"{self._sf_base()}/api/v0/checkout"
        res = requests.post(url, json={"id": order_id}, headers=self._sf_headers(), timeout=30)
        res.raise_for_status()
        return res.json()
