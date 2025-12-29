from odoo import api, fields, models
from odoo.exceptions import ValidationError

class FootballTeam(models.Model):
    _name = "bhz.football.team"
    _description = "Time de Futebol"
    _order = "name"

    name = fields.Char(required=True)
    slug = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    logo = fields.Image(string="Logo", max_width=512, max_height=512)
    website_published = fields.Boolean(default=True, string="Publicado no site")

    @api.constrains("slug")
    def _check_slug(self):
        for rec in self:
            if not rec.slug or " " in rec.slug:
                raise ValidationError("Slug é obrigatório e não pode conter espaços. Ex: cruzeiro, atletico-mg, america-mg")
