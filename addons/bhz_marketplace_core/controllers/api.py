# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


def _auth_token():
    token = request.httprequest.headers.get("X-BHZ-Marketplace-Token")
    if not token:
        return None
    rec = request.env["bhz.marketplace.api.token"].sudo().search([("token", "=", token)], limit=1)
    if rec:
        rec.last_used_at = fields.Datetime.now()
    return rec


class MarketplaceApi(http.Controller):

    @http.route("/api/bhz/marketplace/ping", type="json", auth="public", methods=["POST"], csrf=False)
    def ping(self, **kw):
        tok = _auth_token()
        if not tok:
            return {"error": "unauthorized"}
        return {"pong": True, "seller": tok.seller_id.id}

    @http.route("/api/bhz/marketplace/products/upsert", type="json", auth="public", methods=["POST"], csrf=False)
    def products_upsert(self, **payload):
        tok = _auth_token()
        if not tok:
            return {"error": "unauthorized"}
        vals = payload or {}
        default_code = vals.get("default_code")
        if not default_code:
            return {"error": "default_code required"}
        Product = request.env["product.template"].sudo()
        prod = Product.search([("default_code", "=", default_code)], limit=1)
        data = {
            "name": vals.get("name") or default_code,
            "list_price": vals.get("list_price") or 0.0,
            "description_sale": vals.get("description_sale"),
            "categ_id": vals.get("categ_id"),
            "bhz_seller_id": tok.seller_id.id,
            "bhz_marketplace_state": "pending",
        }
        if prod:
            prod.write(data)
        else:
            data["default_code"] = default_code
            prod = Product.create(data)
        return {"id": prod.id, "state": prod.bhz_marketplace_state}

    @http.route("/api/bhz/marketplace/orders/list", type="json", auth="public", methods=["POST"], csrf=False)
    def orders_list(self, **payload):
        tok = _auth_token()
        if not tok:
            return {"error": "unauthorized"}
        orders = request.env["sale.order"].sudo().search([("order_line.bhz_seller_id", "=", tok.seller_id.id)])
        res = []
        for so in orders:
            res.append({
                "id": so.id,
                "name": so.name,
                "state": so.state,
                "amount_total": so.amount_total,
                "date_order": so.date_order,
            })
        return {"orders": res}
