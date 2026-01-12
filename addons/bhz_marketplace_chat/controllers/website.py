# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceChatWebsite(http.Controller):

    @http.route("/marketplace/qa/ask", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def qa_ask(self, product_tmpl_id=None, question=None, **kw):
        try:
            product_tmpl_id = int(product_tmpl_id)
        except Exception:
            return request.redirect(request.httprequest.referrer or "/shop")
        if not question:
            return request.redirect(request.httprequest.referrer or "/shop")
        request.env["bhz.product.question"].sudo().create_from_website(product_tmpl_id, question, partner=request.env.user.partner_id)
        return request.redirect(request.httprequest.referrer or "/shop/product/%s" % product_tmpl_id)
