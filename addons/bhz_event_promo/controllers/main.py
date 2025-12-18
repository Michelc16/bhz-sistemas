# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class GuiaBHAgendaController(http.Controller):

    @http.route(["/agenda"], type="http", auth="public", website=True, sitemap=True)
    def guiabh_agenda(self, **kw):
        # filtros
        category_id = kw.get("category")
        search = (kw.get("search") or "").strip()

        domain = [
            ("website_published", "=", True),
            ("show_on_public_agenda", "=", True),
        ]

        if category_id:
            try:
                domain.append(("promo_category_id", "=", int(category_id)))
            except Exception:
                pass

        if search:
            domain += ["|", ("name", "ilike", search), ("promo_short_description", "ilike", search)]

        events = request.env["event.event"].sudo().search(domain, order="date_begin asc")
        categories = request.env["event.type"].sudo().search([], order="name asc")

        return request.render(
            "guiabh_event_promo.guiabh_agenda_page",
            {
                "events": events,
                "categories": categories,
                "active_category": int(category_id) if category_id and str(category_id).isdigit() else False,
                "search": search,
            },
        )
