from odoo import fields, models

class Website(models.Model):
    _inherit = "website"

    bhz_city_places_enabled = fields.Boolean(string="Ativar Locais (/lugares) - BHZ City Places")
    bhz_city_places_menu_id = fields.Many2one("website.menu", string="Menu Locais (BHZ)", copy=False)

    def _bhz_city_places_sync_menu(self):
        Menu = self.env["website.menu"].sudo()
        main_menu = self.env.ref("website.main_menu")
        for website in self:
            if website.bhz_city_places_enabled:
                if not website.bhz_city_places_menu_id or not website.bhz_city_places_menu_id.exists():
                    menu = Menu.create({
                        "name": "Locais",
                        "url": "/lugares",
                        "parent_id": main_menu.id,
                        "sequence": 45,
                        "website_id": website.id,
                    })
                    website.bhz_city_places_menu_id = menu.id
                else:
                    website.bhz_city_places_menu_id.write({
                        "website_id": website.id,
                        "url": "/lugares",
                        "name": "Locais",
                        "parent_id": main_menu.id,
                        "sequence": 45,
                    })
            else:
                if website.bhz_city_places_menu_id and website.bhz_city_places_menu_id.exists():
                    website.bhz_city_places_menu_id.unlink()
                website.bhz_city_places_menu_id = False
