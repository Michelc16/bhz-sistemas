# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _on_webclient_bootstrap(self):
        """Compat helper: em algumas bases o web chama este método.

        - Se a versão do Odoo já tiver implementação, delega para super.
        - Caso contrário, retorna um valor truthy para evitar crash.
        Remover este patch quando o ambiente tiver o método nativo.
        """
        parent = super(ResUsers, self)
        fn = getattr(parent, "_on_webclient_bootstrap", None)
        if callable(fn):
            return fn()
        return True
