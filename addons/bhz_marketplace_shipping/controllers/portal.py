# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceShippingPortal(http.Controller):

    def _get_seller(self):
        return request.env["bhz.marketplace.seller"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)

    @http.route("/my/bhz/marketplace/shipments", type="http", auth="user", website=True)
    def portal_shipments(self, **kw):
        seller = self._get_seller()
        domain = []
        if seller:
            domain = [("seller_id", "=", seller.id)]
        shipments = request.env["bhz.seller.shipment"].sudo().search(domain, order="create_date desc", limit=200)
        return request.render("bhz_marketplace_shipping.portal_my_marketplace_shipments", {"shipments": shipments})
