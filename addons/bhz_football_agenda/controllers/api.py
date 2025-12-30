import json
import logging
import re

from odoo import fields, http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class FootballAgendaAPI(http.Controller):
    _token_param = "bhz_football_agenda.api_token"

    @http.route("/bhz/football/api/matches", type="http", auth="public", csrf=False, methods=["POST"])
    def api_matches(self, **kwargs):
        if not self._is_authorized():
            return self._json_response({"error": "Unauthorized"}, status=401)

        payload = self._parse_payload()
        if payload is None:
            return self._json_response({"error": "Invalid JSON payload"}, status=400)

        matches = payload.get("matches") or []
        if not isinstance(matches, list) or not matches:
            return self._json_response({"error": "Missing matches list"}, status=400)

        Match = request.env["bhz.football.match"].sudo()
        Team = request.env["bhz.football.team"].sudo()

        created = updated = 0
        errors = []

        for item in matches:
            try:
                result = self._upsert_match(Match, Team, item)
            except Exception as err:  # pylint: disable=broad-except
                errors.append(
                    {
                        "external_id": item.get("external_id"),
                        "home_team": item.get("home_team"),
                        "away_team": item.get("away_team"),
                        "error": str(err),
                    }
                )
                continue

            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1

        _logger.info(
            "BHZ Football API import source=%s created=%s updated=%s errors=%s",
            payload.get("source") or "unknown",
            created,
            updated,
            len(errors),
        )

        return self._json_response(
            {
                "created": created,
                "updated": updated,
                "errors": errors,
            }
        )

    # ------------------------------------------------------------------ Helpers
    def _is_authorized(self):
        header = request.httprequest.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        token = header[7:].strip()
        stored = request.env["ir.config_parameter"].sudo().get_param(self._token_param)
        return bool(token and stored and token == stored)

    def _parse_payload(self):
        try:
            data = request.httprequest.get_data()
            return json.loads(data.decode("utf-8"))
        except Exception:  # pylint: disable=broad-except
            return None

    def _json_response(self, data, status=200):
        return Response(json.dumps(data), status=status, mimetype="application/json")

    def _upsert_match(self, Match, Team, data):
        required_fields = ("match_datetime", "home_team", "away_team")
        for field in required_fields:
            if not data.get(field):
                raise ValueError("Campo obrigatório ausente: %s" % field)

        match_dt = self._parse_datetime(data["match_datetime"])
        home_team = self._get_or_create_team(Team, data["home_team"])
        away_team = self._get_or_create_team(Team, data["away_team"])
        if not home_team or not away_team:
            raise ValueError("Mandante ou visitante inválido.")

        domain = []
        external_id = (data.get("external_id") or "").strip()
        if external_id:
            domain = [("external_id", "=", external_id)]
        else:
            domain = [
                ("match_datetime", "=", match_dt),
                ("home_team_id", "=", home_team.id),
                ("away_team_id", "=", away_team.id),
                ("competition", "=", data.get("competition") or False),
            ]

        match = Match.search(domain, limit=1)
        vals = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_datetime": match_dt,
            "competition": data.get("competition"),
            "stadium": data.get("stadium"),
            "city": data.get("city"),
            "round_name": data.get("round_phase"),
            "broadcast": data.get("broadcast"),
            "ticket_url": data.get("ticket_url"),
            "website_published": bool(data.get("website_published", True)),
            "active": bool(data.get("active", True)),
            "external_id": external_id or False,
        }

        if match:
            match.write(vals)
            return "updated"
        match = Match.create(vals)
        return "created" if match else "skipped"

    def _parse_datetime(self, value):
        try:
            return fields.Datetime.from_string(value)
        except Exception as err:  # pylint: disable=broad-except
            raise ValueError("Data/hora inválida: %s (%s)" % (value, err)) from err

    def _slugify(self, name):
        slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
        return slug or "team"

    def _get_or_create_team(self, Team, name):
        slug = self._slugify(name)
        team = Team.search([("slug", "=", slug)], limit=1)
        if not team:
            team = Team.search([("name", "=", name)], limit=1)
        if team:
            return team
        return Team.create(
            {
                "name": name,
                "slug": slug,
                "website_published": True,
            }
        )
