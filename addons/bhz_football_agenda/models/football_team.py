from odoo import api, fields, models
from odoo.exceptions import ValidationError

class FootballTeam(models.Model):
    _name = "bhz.football.team"
    _description = "Time de Futebol"
    _order = "name"

    name = fields.Char(required=True)
    slug = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)

    logo = fields.Binary(string="Logo")
    website_published = fields.Boolean(default=True, string="Publicado no site")

    _sql_constraints = [
        ("slug_unique", "unique(slug)", "O slug do time deve ser único."),
    ]

    @api.constrains("slug")
    def _check_slug(self):
        for rec in self:
            if not rec.slug or " " in rec.slug:
                raise ValidationError("Slug é obrigatório e não pode conter espaços. Ex: cruzeiro, atletico-mg, america-mg")
