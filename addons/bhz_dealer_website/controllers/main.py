# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class BhzDealerWebsite(http.Controller):

    @http.route(["/carros"], type="http", auth="public", website=True, sitemap=True)
    def cars_listing(self, **kw):
        domain = [("active", "=", True)]
        website = request.website
        # respeita website_id quando definido
        domain += ["|", ("website_id", "=", False), ("website_id", "=", website.id)]

        # filtros
        q = (kw.get("q") or "").strip()
        brand = (kw.get("brand") or "").strip()
        fuel = (kw.get("fuel") or "").strip()
        condition = (kw.get("condition") or "").strip()
        transmission = (kw.get("transmission") or "").strip()
        year_min = kw.get("year_min")
        year_max = kw.get("year_max")
        price_min = kw.get("price_min")
        price_max = kw.get("price_max")
        sort = (kw.get("sort") or "").strip()

        if q:
            domain += ["|", "|", ("name", "ilike", q), ("model", "ilike", q), ("brand", "ilike", q)]
        if brand:
            domain += [("brand", "ilike", brand)]
        if fuel:
            domain += [("fuel", "=", fuel)]
        if condition:
            domain += [("condition", "=", condition)]
        if transmission:
            domain += [("transmission", "=", transmission)]
        if year_min:
            domain += [("year", ">=", int(year_min))]
        if year_max:
            domain += [("year", "<=", int(year_max))]
        if price_min:
            domain += [("price", ">=", float(price_min))]
        if price_max:
            domain += [("price", "<=", float(price_max))]

        order = "is_featured desc, create_date desc"
        if sort == "price_asc":
            order = "price asc, is_featured desc, create_date desc"
        elif sort == "price_desc":
            order = "price desc, is_featured desc, create_date desc"
        elif sort == "year_desc":
            order = "year desc, is_featured desc, create_date desc"
        elif sort == "year_asc":
            order = "year asc, is_featured desc, create_date desc"

        cars = request.env["bhz.dealer.car"].sudo().search(domain, order=order)

        # opções para filtros (simples)
        brands = request.env["bhz.dealer.car"].sudo().search_read(
            [("active", "=", True), "|", ("website_id", "=", False), ("website_id", "=", website.id)],
            ["brand"]
        )
        brand_list = sorted({b["brand"] for b in brands if b.get("brand")})

        values = {
            "cars": cars,
            "filters": {
                "q": q, "brand": brand, "fuel": fuel, "condition": condition,
                "transmission": transmission, "year_min": year_min, "year_max": year_max,
                "price_min": price_min, "price_max": price_max, "sort": sort,
            },
            "brand_list": brand_list,
        }
        return request.render("bhz_dealer_website.page_cars_listing", values)

    @http.route(["/carros/<int:car_id>", "/carros/<int:car_id>-<string:slug>"], type="http", auth="public", website=True, sitemap=True)
    def car_detail(self, car_id, slug=None, **kw):
        car = request.env["bhz.dealer.car"].sudo().browse(car_id).exists()
        if not car or not car.active:
            return request.not_found()

        website = request.website
        if car.website_id and car.website_id.id != website.id:
            return request.not_found()

        return request.render("bhz_dealer_website.page_car_detail", {"car": car})

    @http.route("/bhz_dealer/snippet/cars", type="json", auth="public", website=True)
    def snippet_cars(self, mode="featured", brand=None, limit=6, **kw):
        website = request.website
        domain = [("active", "=", True), "|", ("website_id", "=", False), ("website_id", "=", website.id)]

        try:
            limit = int(limit)
        except Exception:
            limit = 6
        limit = max(1, min(limit, 20))

        order = "create_date desc"
        if mode == "featured":
            domain.append(("is_featured", "=", True))
            order = "is_featured desc, create_date desc"
        elif mode == "brand" and brand:
            domain.append(("brand", "ilike", brand))
        elif mode == "latest":
            order = "create_date desc"

        cars = request.env["bhz.dealer.car"].sudo().search(domain, order=order, limit=limit)
        html = request.env.ref("bhz_dealer_website.snippet_car_showcase_cards")._render({"cars": cars})
        return {"html": html}
