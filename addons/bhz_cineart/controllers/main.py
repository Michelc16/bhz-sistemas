# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class GuiaBHCineartController(http.Controller):

    _CATEGORY_ALIASES = {
        "now": ["now", "em_cartaz"],
        "soon": ["soon", "em_breve"],
        "premiere": ["premiere", "estreias"],
    }

    def _get_movies(self, movie_model, key):
        categories = self._CATEGORY_ALIASES.get(key, [key])
        domain = [("category", "in", categories), ("active", "=", True)]
        return movie_model.search(domain, order="name asc")

    @http.route(['/cineart'], type='http', auth='public', website=True, sitemap=True)
    def cineart_page(self, **kw):
        Movie = request.env['guiabh.cineart.movie'].sudo()
        now = self._get_movies(Movie, "now")
        soon = self._get_movies(Movie, "soon")
        premiere = self._get_movies(Movie, "premiere")

        return request.render('bhz_cineart.guiabh_cineart_page', {
            'now_movies': now,
            'soon_movies': soon,
            'premiere_movies': premiere,
        })

    @http.route(
        "/bhz_cineart/snippet/movies",
        type="json",
        auth="public",
        website=True,
    )
    def snippet_movies_data(self, category_ids=None, limit=8):
        limit = self._sanitize_limit(limit)
        category_codes = self._map_category_codes(category_ids)
        movies = (
            request.env["guiabh.cineart.movie"]
            .sudo()
            .guiabh_get_movies(categories=category_codes, limit=limit)
        )
        html = request.env["ir.ui.view"]._render_template(
            "bhz_cineart.guiabh_cineart_movie_cards",
            {"movies": movies},
        )
        return {"html": html, "has_movies": bool(movies)}

    def _sanitize_limit(self, limit):
        try:
            limit_value = int(limit)
        except (ValueError, TypeError):
            limit_value = 8
        return max(1, min(limit_value, 24))

    def _map_category_codes(self, category_ids):
        ids = []
        if isinstance(category_ids, str):
            try:
                category_ids = json.loads(category_ids)
            except ValueError:
                category_ids = []
        for entry in category_ids or []:
            try:
                if isinstance(entry, dict):
                    entry = entry.get("id")
                entry_id = int(entry)
            except (ValueError, TypeError):
                continue
            if entry_id:
                ids.append(entry_id)
        if not ids:
            return []
        categories = request.env["guiabh.cineart.category"].sudo().browse(ids)
        return [item.code for item in categories if item.code]
