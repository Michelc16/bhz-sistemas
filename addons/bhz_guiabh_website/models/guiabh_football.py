# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class GuiaBHFootballTeam(models.Model):
    _name = "guiabh.football.team"
    _description = "Time de Futebol (GuiaBH)"
    _order = "name"

    name = fields.Char(required=True, index=True)
    logo = fields.Image(string="Escudo", max_width=256, max_height=256)
    active = fields.Boolean(default=True)


class GuiaBHFootballMatch(models.Model):
    _name = "guiabh.football.match"
    _description = "Jogo de Futebol (GuiaBH)"
    _order = "match_datetime asc"

    home_team_id = fields.Many2one("guiabh.football.team", required=True, string="Mandante")
    away_team_id = fields.Many2one("guiabh.football.team", required=True, string="Visitante")
    competition = fields.Char(string="Competição")
    match_datetime = fields.Datetime(required=True, string="Data/Hora")
    stadium = fields.Char(string="Estádio")
    city = fields.Char(string="Cidade")
    round_name = fields.Char(string="Rodada/Fase")
    broadcast = fields.Char(string="Transmissão")
    ticket_url = fields.Char(string="Link de ingressos")
    notes = fields.Text(string="Observações")
    website_published = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        default=lambda self: self.env["website"].get_current_website(),
        ondelete="set null",
    )

    def action_open_ticket(self):
        self.ensure_one()
        if not self.ticket_url:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": self.ticket_url,
            "target": "new",
        }

    @api.model
    def guiabh_get_upcoming_matches(self, limit=6, order_mode="recent"):
        now = fields.Datetime.now()
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
            ("match_datetime", ">=", now),
        ]
        order = "match_datetime asc, id asc"
        if order_mode == "popular" and "website_visit_count" in self._fields:
            order = "website_visit_count desc, match_datetime asc, id asc"
        return self.search(domain, order=order, limit=limit)
