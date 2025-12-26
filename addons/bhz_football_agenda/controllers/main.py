from odoo import http
from odoo.http import request

class BhzFootballAgendaController(http.Controller):

    @http.route([
        "/futebol/agenda",
        "/futebol/agenda/<string:team_slug>",
    ], type="http", auth="public", website=True, sitemap=True)
    def football_agenda(self, team_slug=None, **kwargs):
        Team = request.env["bhz.football.team"].sudo()
        Match = request.env["bhz.football.match"].sudo()

        teams = Team.search([("website_published", "=", True), ("active", "=", True)], order="name asc")

        selected_team = None
        domain = [
            ("website_published", "=", True),
            ("active", "=", True),
            ("match_datetime", ">=", request.env.cr.now()),
        ]

        if team_slug:
            selected_team = Team.search([("slug", "=", team_slug), ("website_published", "=", True), ("active", "=", True)], limit=1)
            if selected_team:
                domain.append(("team_ids", "in", selected_team.id))

        matches = Match.search(domain, order="match_datetime asc", limit=50)

        return request.render("bhz_football_agenda.page_football_agenda", {
            "teams": teams,
            "selected_team": selected_team,
            "matches": matches,
        })
