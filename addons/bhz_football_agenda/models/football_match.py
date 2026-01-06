from datetime import timedelta
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class FootballMatch(models.Model):
    _name = "bhz.football.match"
    _description = "Jogo de Futebol"
    _order = "match_datetime asc"
    _check_company_auto = True

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
    website_visit_count = fields.Integer(
        string="Visualizações no site",
        default=0,
        help="Usado para ordenar os jogos mais vistos no site.",
    )

    # Publicação
    website_published = fields.Boolean(default=True, string="Publicado no site")
    active = fields.Boolean(default=True)
    external_id = fields.Char(string="ID externo", index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        index=True,
    )

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

    @api.model
    def guiabh_get_upcoming_matches(self, team_ids=None, limit=6, order_mode="recent", company_id=None):
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ]
        companies = False
        if company_id:
            companies = [company_id]
        else:
            companies = self.env.context.get("allowed_company_ids") or [self.env.company.id]
        if companies:
            if False not in companies:
                companies.append(False)
            domain.append(("company_id", "in", companies))
        now = fields.Datetime.now()
        domain.append(("match_datetime", ">=", now))
        if team_ids:
            valid_ids = [tid for tid in team_ids if isinstance(tid, int)]
            if valid_ids:
                domain += [
                    "|",
                    ("home_team_id", "in", valid_ids),
                    ("away_team_id", "in", valid_ids),
                ]
        order = self._get_snippet_order(order_mode)
        return self.search(domain, order=order, limit=limit)

    def _get_snippet_order(self, order_mode):
        allowed = (order_mode or "recent").lower()
        if allowed == "popular":
            return "website_visit_count desc, match_datetime asc, id asc"
        return "match_datetime asc, id asc"

    @api.model
    def _prepare_match_card_data(self, matches):
        if not matches:
            return []
        user = self.env.user
        tz_name = self.env.context.get("tz") or user.tz or "UTC"
        tz_user = user.with_context(tz=tz_name)
        today_local = fields.Date.context_today(tz_user)
        tomorrow_local = today_local + timedelta(days=1)

        def _badge(local_dt):
            if not local_dt:
                return ""
            current_date = local_dt.date()
            if current_date == today_local:
                return "Hoje"
            if current_date == tomorrow_local:
                return "Amanhã"
            return ""

        def _logo(team):
            if not team or not team.id or not team.logo:
                return False
            return f"/web/image/{team._name}/{team.id}/logo"

        def _gcal(match):
            start_dt = match.match_datetime
            if not start_dt:
                return False
            end_dt = start_dt + timedelta(hours=2)
            start_str = start_dt.strftime("%Y%m%dT%H%M%SZ")
            end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
            title = f"{match.home_team_id.name} x {match.away_team_id.name}"
            if match.competition:
                title += f" - {match.competition}"
            location_parts = [part for part in [match.stadium, match.city] if part]
            location = " - ".join(location_parts)
            details_parts = []
            if match.broadcast:
                details_parts.append(f"Transmissão: {match.broadcast}")
            if match.ticket_url:
                details_parts.append(f"Ingressos: {match.ticket_url}")
            if match.round_name:
                details_parts.append(f"Rodada: {match.round_name}")
            details = "\n".join(filter(None, details_parts))

            return "https://calendar.google.com/calendar/render?%s" % urlencode(
                {
                    "action": "TEMPLATE",
                    "text": title,
                    "dates": f"{start_str}/{end_str}",
                    "details": details,
                    "location": location,
                }
            )

        prepared = []
        for match in matches:
            match_dt = match.match_datetime
            local_dt = (
                fields.Datetime.context_timestamp(tz_user, match_dt) if match_dt else False
            )
            prepared.append(
                {
                    "id": match.id,
                    "home_team_name": match.home_team_id.name,
                    "home_team_logo": _logo(match.home_team_id),
                    "away_team_name": match.away_team_id.name,
                    "away_team_logo": _logo(match.away_team_id),
                    "competition": match.competition,
                    "stadium": match.stadium,
                    "city": match.city,
                    "round_name": match.round_name,
                    "broadcast": match.broadcast,
                    "ticket_url": match.ticket_url,
                    "match_datetime_label": local_dt.strftime("%d/%m/%Y %H:%M")
                    if local_dt
                    else "",
                    "badge_label": _badge(local_dt),
                    "gcal_url": _gcal(match),
                }
            )
        return prepared
