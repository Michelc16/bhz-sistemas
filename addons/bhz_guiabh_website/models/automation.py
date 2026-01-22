from datetime import timedelta

from odoo import fields, models


class GuiaBHAutoMaintenance(models.AbstractModel):
    _name = "guiabh.auto.maintenance"
    _description = "GuiaBH Automations"

    def _run_auto_feature_and_cleanup(self):
        """Cron entrypoint: feature fresh content and unpublish expired items."""
        self._auto_feature_recent()
        self._auto_unpublish_expired()

    def _auto_feature_recent(self):
        """Mark recent content as featured; keep a small curated set per model."""
        now = fields.Datetime.now()
        models_def = [
            ("guiabh.event", "start_datetime", 6, 14),
            ("guiabh.match", "match_datetime", 4, 14),
            ("guiabh.movie", "release_date", 4, 60),
            ("guiabh.news", "publish_date", 6, 30),
        ]
        for model_name, date_field, limit, window_days in models_def:
            Model = self.env[model_name].sudo()
            cutoff = now - timedelta(days=window_days)
            domain = [
                (date_field, "!=", False),
                (date_field, ">=", cutoff),
                ("website_published", "=", True),
            ]
            fresh = Model.search(domain, order=f"{date_field} desc", limit=limit)
            if not fresh:
                continue
            # set featured on recent, off for others
            Model.search([("website_published", "=", True)]).write({"featured": False})
            fresh.write({"featured": True})

    def _auto_unpublish_expired(self):
        """Unpublish content considered expired by date."""
        now = fields.Datetime.now()
        # Events: end or start passed by more than 1 day
        Event = self.env["guiabh.event"].sudo()
        expired_events = Event.search(
            [
                ("website_published", "=", True),
                ("start_datetime", "!=", False),
                ("start_datetime", "<", now - timedelta(days=1)),
            ]
        )
        expired_events.write({"website_published": False, "featured": False})

        Match = self.env["guiabh.match"].sudo()
        expired_matches = Match.search(
            [
                ("website_published", "=", True),
                ("match_datetime", "!=", False),
                ("match_datetime", "<", now - timedelta(days=1)),
            ]
        )
        expired_matches.write({"website_published": False, "featured": False})

        Movie = self.env["guiabh.movie"].sudo()
        expired_movies = Movie.search(
            [
                ("website_published", "=", True),
                ("release_date", "!=", False),
                ("release_date", "<", (now - timedelta(days=365)).date()),
            ]
        )
        expired_movies.write({"featured": False})
