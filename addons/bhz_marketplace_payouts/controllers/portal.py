# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplacePayoutPortal(http.Controller):

    def _get_seller(self):
        return request.env["bhz.marketplace.seller"].sudo().search([
            ("user_id", "=", request.env.user.id)
        ], limit=1)

    @http.route("/my/bhz/marketplace/payouts", type="http", auth="user", website=True)
    def portal_payouts(self, **kw):
        seller = self._get_seller()
        moves = request.env["bhz.seller.ledger.move"].sudo().search([("seller_id", "=", seller.id)], order="date desc", limit=200) if seller else []
        payouts = request.env["bhz.seller.payout"].sudo().search([("seller_id", "=", seller.id)], order="date_to desc", limit=50) if seller else []
        return request.render("bhz_marketplace_payouts.portal_my_marketplace_payouts", {"moves": moves, "payouts": payouts})
