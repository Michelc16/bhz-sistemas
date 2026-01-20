# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class MarketplaceWebsite(http.Controller):

    def _query_products(self, domain=None, limit=20):
        base_domain = [("website_published", "=", True)]
        if domain:
            base_domain += domain
        return request.env["product.template"].sudo().search(base_domain, limit=limit, order="id desc")

    @http.route("/marketplace", type="http", auth="public", website=True)
    def page_home(self, **kw):
        products = self._query_products(limit=8)
        sellers = request.env["bhz.marketplace.seller"].sudo().search([], limit=6, order="create_date desc")
        return request.render("bhz_marketplace_app.marketplace_home", {
            "products": products,
            "sellers": sellers,
        })

    @http.route("/marketplace/shops", type="http", auth="public", website=True)
    def page_shops(self, **kw):
        sellers = request.env["bhz.marketplace.seller"].sudo().search([], order="name")
        return request.render("bhz_marketplace_app.marketplace_shops", {"sellers": sellers})

    @http.route("/marketplace/category/<int:category_id>", type="http", auth="public", website=True)
    def page_category(self, category_id, **kw):
        category = request.env["product.public.category"].sudo().browse(category_id)
        products = self._query_products([("public_categ_ids", "in", category.id)]) if category.exists() else []
        return request.render("bhz_marketplace_app.marketplace_category", {
            "category": category if category.exists() else None,
            "products": products,
        })

    @http.route("/marketplace/product/<int:product_id>", type="http", auth="public", website=True)
    def page_product(self, product_id, **kw):
        product = request.env["product.template"].sudo().browse(product_id)
        if not product.exists() or not product.website_published:
            return request.not_found()
        return request.render("bhz_marketplace_app.marketplace_product", {"product": product})
