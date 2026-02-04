from odoo import api, fields, models


class Website(models.Model):
    _inherit = "website"

    bhz_featured_carousel_autoplay = fields.Boolean(
        string="Autoplay do carrossel de destaques",
        help="Se marcado, o carrossel de destaques roda automaticamente.",
    )
    bhz_featured_carousel_interval_ms = fields.Integer(
        string="Intervalo do carrossel (ms)",
        help="Tempo entre slides do carrossel de destaques.",
    )
    bhz_featured_carousel_refresh_ms = fields.Integer(
        string="Atualização do carrossel (ms)",
        help="Frequência de atualização automática do carrossel. 0 desabilita.",
    )

    # Agenda / Events pages (multi-website control)
    bhz_agenda_enabled = fields.Boolean(
        string="Ativar Agenda (/agenda) neste site",
        help="Se marcado, este site terá o menu 'Agenda' e as rotas /agenda ficarão acessíveis. "
             "Se desmarcado, /agenda retornará 404 neste site (evita SEO duplicado entre sites).",
        default=False,
    )
    bhz_agenda_menu_id = fields.Many2one(
        "website.menu",
        string="Menu da Agenda",
        help="Menu criado automaticamente por este módulo quando a Agenda está ativa.",
        copy=False,
        ondelete="set null",
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _bhz_agenda_menu_vals(self):
        self.ensure_one()
        return {
            "name": "Agenda",
            "url": "/agenda",
            "parent_id": self.env.ref("website.main_menu").id,
            "sequence": 35,
            "website_id": self.id,
        }

    def _bhz_agenda_set_menu_visibility(self, menu, visible):
        Menu = self.env["website.menu"]
        for field in ("is_visible", "is_published", "website_published", "active"):
            if field in Menu._fields:
                menu.write({field: bool(visible)})
                return
        if not visible:
            menu.unlink()

    def _bhz_agenda_ensure_menu(self):
        self.ensure_one()
        Menu = self.env["website.menu"].sudo()
        if self.bhz_agenda_menu_id and self.bhz_agenda_menu_id.exists():
            # Ensure it is linked to this website and active
            self.bhz_agenda_menu_id.write({"website_id": self.id, "name": "Agenda"})
            self._bhz_agenda_set_menu_visibility(self.bhz_agenda_menu_id, True)
            return self.bhz_agenda_menu_id

        # Try to reuse an existing per-website menu if it already exists
        existing = Menu.search(
            [
                ("website_id", "=", self.id),
                ("url", "=", "/agenda"),
                ("parent_id", "=", self.env.ref("website.main_menu").id),
            ],
            limit=1,
        )
        if existing:
            existing.write({"name": "Agenda"})
            self._bhz_agenda_set_menu_visibility(existing, True)
            self.bhz_agenda_menu_id = existing.id
            return existing

        menu = Menu.create(self._bhz_agenda_menu_vals())
        self.bhz_agenda_menu_id = menu.id
        return menu

    def _bhz_agenda_disable_menu(self):
        self.ensure_one()
        if self.bhz_agenda_menu_id and self.bhz_agenda_menu_id.exists():
            # Keep record for potential re-enable, just hide it
            self._bhz_agenda_set_menu_visibility(self.bhz_agenda_menu_id.sudo(), False)
        # Also hide any stray /agenda menus for this website
        Menu = self.env["website.menu"].sudo()
        stray = Menu.search([("website_id", "=", self.id), ("url", "=", "/agenda")])
        if stray:
            self._bhz_agenda_set_menu_visibility(stray, False)

    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        for w, vals in zip(websites, vals_list):
            if vals.get("bhz_agenda_enabled"):
                w._bhz_agenda_ensure_menu()
        return websites

    def write(self, vals):
        res = super().write(vals)
        if "bhz_agenda_enabled" in vals:
            for w in self:
                if w.bhz_agenda_enabled:
                    w._bhz_agenda_ensure_menu()
                else:
                    w._bhz_agenda_disable_menu()
        return res
