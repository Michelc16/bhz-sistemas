# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BhzPlacesWebsite(http.Controller):

    @http.route(
        ["/lugares", "/lugares/page/<int:page>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def places_list(self, page=1, q=None, category=None, city=None, tag=None, **kw):
        website = request.website
        company = website.company_id
        Place = request.env["bhz.place"].sudo()

        domain = [("website_published", "=", True), ("active", "=", True)]

        # Restringe por website quando houver multi-site
        domain += ["|", ("website_id", "=", False), ("website_id", "=", website.id)]
        if company:
            domain.append(("company_id", "in", [False, company.id]))

        if q:
            domain += ["|", ("name", "ilike", q), ("short_description", "ilike", q)]
        if category:
            domain += [("category_id", "=", int(category))]
        if city:
            domain += [("city_id", "=", int(city))]
        if tag:
            domain += [("tag_ids", "in", [int(tag)])]

        page_size = 12
        total = Place.search_count(domain)
        pager = request.website.pager(
            url="/lugares",
            total=total,
            page=page,
            step=page_size,
            url_args={"q": q, "category": category, "city": city, "tag": tag},
        )

        places = Place.search(domain, limit=page_size, offset=pager["offset"], order="sequence, name")

        extra_domain = [("active", "=", True)]
        if company:
            extra_domain = [("active", "=", True), ("company_id", "in", [False, company.id])]
        categories = request.env["bhz.place.category"].sudo().search(list(extra_domain), order="sequence, name")
        cities = request.env["bhz.place.city"].sudo().search(list(extra_domain), order="name")
        tags = request.env["bhz.place.tag"].sudo().search(list(extra_domain), order="name")

        values = {
            "places": places,
            "pager": pager,
            "q": q or "",
            "category": int(category) if category else False,
            "city": int(city) if city else False,
            "tag": int(tag) if tag else False,
            "categories": categories,
            "cities": cities,
            "tags": tags,
        }
        return request.render("bhz_city_places.place_list_page", values)

    @http.route(
        ["/lugares/<int:place_id>"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def place_detail(self, place_id, **kw):
        website = request.website
        company = website.company_id
        place = request.env["bhz.place"].sudo().browse(place_id)
        if not place.exists() or not place.website_published or not place.active:
            return request.not_found()

        # Restringe por website quando houver multi-site
        if place.website_id and place.website_id.id != website.id:
            return request.not_found()
        if company and place.company_id and place.company_id.id != company.id:
            return request.not_found()

        return request.render("bhz_city_places.place_detail_page", {"place": place})
