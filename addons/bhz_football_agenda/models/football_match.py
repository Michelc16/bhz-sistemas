from odoo import api, fields, models
from odoo.exceptions import ValidationError

class FootballMatch(models.Model):
    _name = "bhz.football.match"
    _description = "Jogo de Futebol"
    _order = "match_datetime asc"

    # Times
    home_team_id = fields.Many2one("bhz.football.team", required=True, string="Mandante")
    away_team_id = fields.Many2one("bhz.football.team", required=True, string="Visitante")

    # Info do jogo
    competition = fields.Char(string="Competição")
    match_datetime = fields.Datetime(required=True, string="Data/Hora")
    stadium = fields.Char(string="Estádio")
    city = fields.Char(string="Cidade")
    round_name = fields.Char(string="Rodada/Fase")

    # Extras
    broadcast = fields.Char(string="Transmissão")
    ticket_url = fields.Char(string="Link de ingressos")
    notes = fields.Text(string="Observações")

    # Publicação
    website_published = fields.Boolean(default=True, string="Publicado no site")
    active = fields.Boolean(default=True)
    external_id = fields.Char(string="ID externo", index=True)

    # Ajuda para filtrar por “time envolvido”
    team_ids = fields.Many2many(
        "bhz.football.team",
        compute="_compute_team_ids",
        store=True,
        string="Times envolvidos",
    )

    def _compute_team_ids(self):
        for rec in self:
            rec.team_ids = [(6, 0, [rec.home_team_id.id, rec.away_team_id.id] if rec.home_team_id and rec.away_team_id else [])]

    @api.constrains("external_id")
    def _check_external_id_unique(self):
        for rec in self:
            if rec.external_id:
                duplicate = self.search(
                    [("external_id", "=", rec.external_id), ("id", "!=", rec.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError("Já existe um jogo com este ID externo.")
