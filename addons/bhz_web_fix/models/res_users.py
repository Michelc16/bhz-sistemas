# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _on_webclient_bootstrap(self):
        """Compat helper: em algumas bases o web chama este método.

        - Se a versão do Odoo já tiver implementação, delega para super.
        - Caso contrário, retorna um payload vazio para evitar crash.
        Remover este patch quando o ambiente tiver o método nativo.
        """
        if hasattr(super(), "_on_webclient_bootstrap"):
            return super()._on_webclient_bootstrap()
        return {}
