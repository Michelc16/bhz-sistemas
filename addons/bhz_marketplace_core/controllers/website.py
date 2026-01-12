# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceWebsite(http.Controller):

    @http.route("/seller/<string:slug>", type="http", auth="public", website=True, sitemap=True)
    def seller_public(self, slug=None, **kw):
        seller = request.env["bhz.marketplace.seller"].sudo().search([("shop_slug", "=", slug), ("state", "=", "approved")], limit=1)
        if not seller:
            return request.not_found()
        products = request.env["product.template"].sudo().search([
            ("bhz_seller_id", "=", seller.id),
            ("bhz_marketplace_state", "=", "approved"),
            ("website_published", "=", True),
        ])
        return request.render("bhz_marketplace_core.seller_public_page", {"seller": seller, "products": products})
