# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplacePortal(http.Controller):

    def _get_seller_for_user(self):
        seller = request.env["bhz.marketplace.seller"].sudo().search([
            "|", ("user_id", "=", request.env.user.id),
            ("partner_id", "=", request.env.user.partner_id.id)
        ], limit=1)
        return seller

    @http.route("/my/bhz/marketplace", type="http", auth="user", website=True)
    def portal_home(self, **kw):
        return request.render("bhz_marketplace_core.portal_my_marketplace_home", {})

    @http.route("/my/bhz/marketplace/products", type="http", auth="user", website=True)
    def portal_products(self, **kw):
        seller = self._get_seller_for_user()
        products = request.env["product.template"].sudo().search([("bhz_seller_id", "=", seller.id)]) if seller else []
        return request.render("bhz_marketplace_core.portal_my_marketplace_products", {"products": products})

    @http.route("/my/bhz/marketplace/orders", type="http", auth="user", website=True)
    def portal_orders(self, **kw):
        seller = self._get_seller_for_user()
        orders = request.env["sale.order"].sudo().search([("order_line.bhz_seller_id", "=", seller.id)]) if seller else []
        return request.render("bhz_marketplace_core.portal_my_marketplace_orders", {"orders": orders})
