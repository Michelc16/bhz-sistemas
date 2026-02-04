from odoo import fields, models

class Website(models.Model):
    _inherit = "website"

    bhz_cineart_enabled = fields.Boolean(string="Ativar Cineart (/cineart) - BHZ Cineart")
    bhz_cineart_menu_id = fields.Many2one("website.menu", string="Menu Cineart (BHZ)", copy=False)

    def _bhz_cineart_sync_menu(self):
        Menu = self.env["website.menu"].sudo()
        main_menu = self.env.ref("website.main_menu")
        for website in self:
            if website.bhz_cineart_enabled:
                if not website.bhz_cineart_menu_id or not website.bhz_cineart_menu_id.exists():
                    menu = Menu.create({
                        "name": "Cineart",
                        "url": "/cineart",
                        "parent_id": main_menu.id,
                        "sequence": 60,
                        "website_id": website.id,
                    })
                    website.bhz_cineart_menu_id = menu.id
                else:
                    website.bhz_cineart_menu_id.write({
                        "website_id": website.id,
                        "url": "/cineart",
                        "name": "Cineart",
                        "parent_id": main_menu.id,
                        "sequence": 60,
                    })
            else:
                if website.bhz_cineart_menu_id and website.bhz_cineart_menu_id.exists():
                    website.bhz_cineart_menu_id.unlink()
                website.bhz_cineart_menu_id = False
