# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class GuiaBHCineartController(http.Controller):

    @http.route(['/cineart'], type='http', auth='public', website=True, sitemap=True)
    def cineart_page(self, **kw):
        Movie = request.env['guiabh.cineart.movie'].sudo()

        now = Movie.search([('category', '=', 'now'), ('active', '=', True)])
        soon = Movie.search([('category', '=', 'soon'), ('active', '=', True)])
        premiere = Movie.search([('category', '=', 'premiere'), ('active', '=', True)])

        return request.render('guiabh_cineart.guiabh_cineart_page', {
            'now_movies': now,
            'soon_movies': soon,
            'premiere_movies': premiere,
        })
