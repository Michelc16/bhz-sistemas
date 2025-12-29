from odoo import fields, http
from odoo.http import request

try:
    from odoo.tools.misc import format_datetime as misc_format_datetime
except Exception:
    misc_format_datetime = None

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
        matches_data = []

        def _fmt(dt):
            if not dt:
                return ""
            if misc_format_datetime:
                try:
                    return misc_format_datetime(request.env, dt)
                except TypeError:
                    pass
                except Exception:
                    pass
            return fields.Datetime.to_string(dt)

        for match in matches:
            matches_data.append(
                {
                    "id": match.id,
                    "home_team_name": match.home_team_id.name,
                    "away_team_name": match.away_team_id.name,
                    "competition": match.competition,
                    "stadium": match.stadium,
                    "city": match.city,
                    "round_name": match.round_name,
                    "broadcast": match.broadcast,
                    "ticket_url": match.ticket_url,
                    "match_datetime_str": _fmt(match.match_datetime),
                }
            )

        return request.render(
            "bhz_football_agenda.page_football_agenda",
            {
                "teams": teams,
                "selected_team": selected_team,
                "matches_data": matches_data,
            },
        )
