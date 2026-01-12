# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceReturnsPortal(http.Controller):

    def _get_user_returns(self):
        seller = request.env["bhz.marketplace.seller"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)
        domain = []
        if seller:
            domain = [("seller_id", "=", seller.id)]
        else:
            # comprador logado: limitar a pedidos dele
            domain = [("sale_order_id.partner_id", "=", request.env.user.partner_id.id)]
        return request.env["bhz.marketplace.return"].sudo().search(domain, order="create_date desc", limit=200)

    @http.route("/my/bhz/marketplace/returns", type="http", auth="user", website=True)
    def portal_returns(self, **kw):
        returns = self._get_user_returns()
        return request.render("bhz_marketplace_returns_disputes.portal_my_marketplace_returns", {"returns": returns})
