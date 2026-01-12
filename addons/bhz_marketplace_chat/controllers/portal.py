# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceChatPortal(http.Controller):

    def _get_seller(self):
        return request.env["bhz.marketplace.seller"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)

    @http.route("/my/bhz/marketplace/questions", type="http", auth="user", website=True)
    def portal_questions(self, **kw):
        seller = self._get_seller()
        domain = []
        if seller:
            domain = [("seller_id", "=", seller.id)]
        questions = request.env["bhz.product.question"].sudo().search(domain, order="create_date desc", limit=200)
        return request.render("bhz_marketplace_chat.portal_my_marketplace_questions", {"questions": questions})
