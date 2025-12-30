# -*- coding: utf-8 -*-
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
