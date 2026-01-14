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
        domain = [
            ("active", "=", True),
            ("website_published", "=", True),
            "|",
            ("website_id", "=", False),
            ("website_id", "=", website.id),
        ]

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

    @http.route(
        ["/carros/<model(\"bhz.dealer.car\"):car>", "/carros/<slug(car)>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def car_detail(self, car, **kw):
        config = request.env["bhz.dealer.website.config"].sudo().get_for_website(request.website)
        if not config or not config.dealer_enabled:
            return request.not_found()

        website = request.website
        if (
            not car
            or not car.exists()
            or not car.active
            or not car.website_published
            or (car.website_id and car.website_id.id != website.id)
        ):
            return request.not_found()

        return request.render("bhz_dealer_website.template_dealer_car_detail", {"car": car, "website": website, "config": config})

    @http.route("/carros/lead", type="jsonrpc", auth="public", website=True, methods=["POST"])
    def car_lead(self, car_id=None, name=None, phone=None, email=None, message=None, lead_type=None, car_brand=None, car_model=None, car_year=None, car_km=None, **kw):
        if kw.get("hp_field"):
            return {"error": "spam"}

        Car = request.env["bhz.dealer.car"].sudo()
        LeadModel = request.env.get("crm.lead")
        if not LeadModel:
            return {"error": "crm_unavailable"}
        Lead = LeadModel.sudo()

        car = Car.browse(int(car_id)).exists() if car_id else Car.browse()
        if car and (not car.active or not car.website_published or car.website_id.id != request.website.id):
            return {"error": "not_found"}

        source = Lead._dealer_source() if hasattr(Lead, "_dealer_source") else False
        details = (message or "").strip()
        extra_lines = []
        if lead_type == "sell_car":
            if car_brand:
                extra_lines.append(f"Marca: {car_brand}")
            if car_model:
                extra_lines.append(f"Modelo: {car_model}")
            if car_year:
                extra_lines.append(f"Ano: {car_year}")
            if car_km:
                extra_lines.append(f"KM: {car_km}")
        if extra_lines:
            details = (details + "\n" if details else "") + "\n".join(extra_lines)

        vals = {
            "type": "opportunity",
            "name": name or "Lead site - BHZ Dealer",
            "contact_name": name,
            "phone": phone,
            "email_from": email,
            "description": details,
            "website_id": request.website.id,
        }
        if car:
            car_url = f"/carros/{car.id}-{car.slug or ''}"
            vals["description"] = (vals["description"] or "") + f"\n\nCarro: {car.name} (ID {car.id})\nURL: {car_url}"
            tag = request.env.ref("crm.tag_website_lead", raise_if_not_found=False)
            if tag:
                vals["tag_ids"] = [(4, tag.id)]
            if Lead._fields.get("dealer_car_id"):
                vals["dealer_car_id"] = car.id
        if source and Lead._fields.get("source_id"):
            vals["source_id"] = source.id

        lead = Lead.create(vals)

        group = request.env.ref("bhz_dealer_website.group_bhz_dealer_manager", raise_if_not_found=False)
        if group and group.users:
            lead.message_subscribe(partner_ids=group.users.partner_id.ids)
            lead.message_post(body="Novo lead do site Dealer.", subtype_xmlid="mail.mt_note")

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
