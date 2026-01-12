# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _on_webclient_bootstrap(self):
        """Compat helper: ensure method exists even if upstream changes."""
        # call super if defined, otherwise no-op
        if hasattr(super(), "_on_webclient_bootstrap"):
            return super()._on_webclient_bootstrap()
        return None
