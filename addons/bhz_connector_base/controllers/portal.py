# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceConnectorPortal(http.Controller):

    def _get_seller(self):
        return request.env["bhz.marketplace.seller"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)

    @http.route("/my/bhz/marketplace/connectors", type="http", auth="user", website=True)
    def portal_connectors(self, **kw):
        seller = self._get_seller()
        accounts = []
        jobs = []
        if seller:
            accounts = request.env["bhz.connector.account"].sudo().search([("seller_id", "=", seller.id)])
            jobs = request.env["bhz.connector.job"].sudo().search([("account_id.seller_id", "=", seller.id)], limit=200)
        return request.render("bhz_marketplace_connectors.portal_my_marketplace_connectors", {"accounts": accounts, "jobs": jobs})
