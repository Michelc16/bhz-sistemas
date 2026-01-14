# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class BhzDealerWebsite(http.Controller):

    @http.route(["/carros"], type="http", auth="public", website=True, sitemap=True)
    def cars_listing(self, page=1, **kw):
        website = request.website
        config = request.env["bhz.dealer.website.config"].sudo().get_for_website(website)
        if not config or not config.dealer_enabled:
            return request.not_found()
        Car = request.env["bhz.dealer.car"].sudo()
        domain = [("active", "=", True), ("website_published", "=", True), ("website_id", "=", website.id)]

        def _intval(val):
            try:
                return int(val)
            except Exception:
                return False

        def _floatval(val):
            try:
                return float(val)
            except Exception:
                return False

        try:
            page = max(1, int(page))
        except Exception:
            page = 1

        q = (kw.get("q") or "").strip()
        brand = (kw.get("brand") or "").strip()
        model = (kw.get("model") or "").strip()
        fuel = (kw.get("fuel") or "").strip()
        condition = (kw.get("condition") or "").strip()
        transmission = (kw.get("transmission") or "").strip()
        year_min = _intval(kw.get("year_min"))
        year_max = _intval(kw.get("year_max"))
        price_min = _floatval(kw.get("price_min"))
        price_max = _floatval(kw.get("price_max"))
        km_min = _intval(kw.get("km_min"))
        km_max = _intval(kw.get("km_max"))
        order_key = (kw.get("order") or "").strip()

        if q:
            domain += ["|", "|", ("name", "ilike", q), ("model", "ilike", q), ("brand", "ilike", q)]
        if brand:
            domain.append(("brand", "ilike", brand))
        if model:
            domain.append(("model", "ilike", model))
        if fuel:
            domain.append(("fuel", "=", fuel))
        if condition:
            domain.append(("condition", "=", condition))
        if transmission:
            domain.append(("transmission", "=", transmission))
        if year_min:
            domain.append(("year", ">=", year_min))
        if year_max:
            domain.append(("year", "<=", year_max))
        if price_min:
            domain.append(("price", ">=", price_min))
        if price_max:
            domain.append(("price", "<=", price_max))
        if km_min:
            domain.append(("mileage_km", ">=", km_min))
        if km_max:
            domain.append(("mileage_km", "<=", km_max))

        order_map = {
            "price_asc": "is_featured desc, price asc, year desc, create_date desc",
            "price_desc": "is_featured desc, price desc, year desc, create_date desc",
            "year_desc": "is_featured desc, year desc, create_date desc",
            "year_asc": "is_featured desc, year asc, create_date desc",
            "newest": "is_featured desc, create_date desc",
        }
        order_by = order_map.get(order_key) or "is_featured desc, year desc, create_date desc"

        step = 12
        total = Car.search_count(domain)
        pager = request.website.pager(
            url="/carros",
            total=total,
            page=page,
            step=step,
            url_args={k: v for k, v in kw.items() if k not in ("page",)},
        )

        cars = Car.search(domain, order=order_by, limit=step, offset=pager["offset"])

        brands = Car.search_read([("active", "=", True), ("website_published", "=", True), ("website_id", "=", website.id)], ["brand"])
        brand_list = sorted({b["brand"] for b in brands if b.get("brand")})

        values = {
            "cars": cars,
            "website": website,
            "pager": pager,
            "filters": {
                "q": q,
                "brand": brand,
                "model": model,
                "fuel": fuel,
                "condition": condition,
                "transmission": transmission,
                "year_min": year_min or "",
                "year_max": year_max or "",
                "price_min": price_min or "",
                "price_max": price_max or "",
                "km_min": km_min or "",
                "km_max": km_max or "",
                "order": order_key,
            },
            "brand_list": brand_list,
            "config": config,
        }
        return request.render("bhz_dealer_website.template_dealer_car_list", values)

    @http.route(["/carros/<int:car_id>", "/carros/<int:car_id>-<string:slug>"], type="http", auth="public", website=True, sitemap=True)
    def car_detail(self, car_id, slug=None, **kw):
        config = request.env["bhz.dealer.website.config"].sudo().get_for_website(request.website)
        if not config or not config.dealer_enabled:
            return request.not_found()
        car = request.env["bhz.dealer.car"].sudo().browse(car_id).exists()

        website = request.website
        if not car or not car.active or not car.website_published or car.website_id.id != website.id:
            return request.not_found()

        return request.render("bhz_dealer_website.template_dealer_car_detail", {"car": car, "website": website, "config": config})

    @http.route("/carros/lead", type="jsonrpc", auth="public", website=True, methods=["POST"])
    def car_lead(self, car_id=None, name=None, phone=None, email=None, message=None, **kw):
        Car = request.env["bhz.dealer.car"].sudo()
        Lead = request.env["crm.lead"].sudo()

        car = Car.browse(int(car_id)).exists() if car_id else Car.browse()
        if car and (not car.active or car.website_id.id != request.website.id):
            return {"error": "not_found"}

        vals = {
            "type": "opportunity",
            "name": name or "Lead site - BHZ Dealer",
            "contact_name": name,
            "phone": phone,
            "email_from": email,
            "description": (message or "").strip(),
        }
        if car:
            vals["description"] = (vals["description"] or "") + f"\n\nCarro: {car.name} (ID {car.id})"
            tag = request.env.ref("crm.tag_website_lead", raise_if_not_found=False)
            if tag:
                vals["tag_ids"] = [(4, tag.id)]
        lead = Lead.create(vals)

        return {"lead_id": lead.id}

    @http.route("/bhz_dealer/snippet/cars", type="jsonrpc", auth="public", website=True)
    def snippet_cars(self, mode="featured", brand=None, limit=6, **kw):
        website = request.website
        config = request.env["bhz.dealer.website.config"].sudo().get_for_website(website)
        if not config or not config.dealer_enabled:
            return {"html": ""}
        domain = [("active", "=", True), ("website_published", "=", True), ("website_id", "=", website.id)]

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
