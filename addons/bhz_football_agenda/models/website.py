from odoo import fields, models

class Website(models.Model):
    _inherit = "website"

    bhz_football_agenda_enabled = fields.Boolean(string="Ativar Agenda de Futebol (BHZ)")
    bhz_football_agenda_menu_id = fields.Many2one("website.menu", string="Menu Agenda Futebol (BHZ)", copy=False)

    def _bhz_football_sync_menu(self):
        Menu = self.env["website.menu"].sudo()
        main_menu = self.env.ref("website.main_menu")
        for website in self:
            if website.bhz_football_agenda_enabled:
                if not website.bhz_football_agenda_menu_id or not website.bhz_football_agenda_menu_id.exists():
                    menu = Menu.create({
                        "name": "Agenda de Jogos",
                        "url": "/futebol/agenda",
                        "parent_id": main_menu.id,
                        "sequence": 60,
                        "website_id": website.id,
                    })
                    website.bhz_football_agenda_menu_id = menu.id
                else:
                    website.bhz_football_agenda_menu_id.write({
                        "website_id": website.id,
                        "url": "/futebol/agenda",
                        "name": "Agenda de Jogos",
                        "parent_id": main_menu.id,
                        "sequence": 60,
                    })
            else:
                if website.bhz_football_agenda_menu_id and website.bhz_football_agenda_menu_id.exists():
                    website.bhz_football_agenda_menu_id.unlink()
                website.bhz_football_agenda_menu_id = False
