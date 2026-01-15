# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiaBHCinemaMovie(models.Model):
    _name = "guiabh.cinema.movie"
    _description = "Cinema - Filmes (GuiaBH)"
    _order = "category, name"

    name = fields.Char(string="Título", required=True, index=True)
    category = fields.Selection(
        [
            ("now", "Em cartaz"),
            ("soon", "Em breve"),
            ("premiere", "Estreias"),
        ],
        string="Categoria",
        required=True,
        default="now",
        index=True,
    )
    genre = fields.Char(string="Gênero")
    age_rating = fields.Char(string="Classificação indicativa")
    release_date = fields.Char(string="Data de estreia")
    cineart_url = fields.Char(string="Link externo")
    poster_image = fields.Image(string="Cartaz", max_width=1024, max_height=1024)
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        default=lambda self: self.env["website"].get_current_website(),
        ondelete="set null",
    )
    is_featured = fields.Boolean(string="Destaque", default=False)

    def action_open_external(self):
        self.ensure_one()
        if not self.cineart_url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.cineart_url,
            "target": "new",
        }
