from datetime import datetime, time

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
            ("match_datetime", ">=", fields.Datetime.now()),
        ]

        if team_slug:
            selected_team = Team.search([("slug", "=", team_slug), ("website_published", "=", True), ("active", "=", True)], limit=1)
            if selected_team:
                domain.append(("team_ids", "in", selected_team.id))

        filters = {
            "date_from": request.params.get("date_from") or "",
            "date_to": request.params.get("date_to") or "",
            "team_id": request.params.get("team_id") or "",
            "competition": request.params.get("competition") or "",
        }

        def _parse_date(value, end=False):
            if not value:
                return False
            try:
                parsed = fields.Date.from_string(value)
                if not parsed:
                    return False
                if end:
                    return datetime.combine(parsed, time.max)
                return datetime.combine(parsed, time.min)
            except Exception:
                return False

        date_from_dt = _parse_date(filters["date_from"])
        date_to_dt = _parse_date(filters["date_to"], end=True)
        if date_from_dt:
            domain.append(("match_datetime", ">=", fields.Datetime.to_string(date_from_dt)))
        if date_to_dt:
            domain.append(("match_datetime", "<=", fields.Datetime.to_string(date_to_dt)))

        if filters["team_id"]:
            try:
                team_id_int = int(filters["team_id"])
                domain.append(("team_ids", "in", team_id_int))
            except ValueError:
                filters["team_id"] = ""

        if filters["competition"]:
            domain.append(("competition", "=", filters["competition"]))

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

        base_comp_domain = [
            ("website_published", "=", True),
            ("active", "=", True),
        ]
        competition_groups = Match.read_group(base_comp_domain, ["competition"], ["competition"])
        competitions = sorted(filter(None, (grp["competition"] for grp in competition_groups)))

        return request.render(
            "bhz_football_agenda.page_football_agenda",
            {
                "teams": teams,
                "selected_team": selected_team,
                "matches_data": matches_data,
                "competitions": competitions,
                "filters": filters,
            },
        )
