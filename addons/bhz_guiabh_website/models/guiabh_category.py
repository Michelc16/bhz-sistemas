import re
import unicodedata

from odoo import api, fields, models
from ._mixins import guiabh_base_fields


class GuiaBHCategory(models.Model):
    _name = "guiabh.category"
    _description = "GuiaBH Category"
    _inherit = [
        "website.published.mixin",
        "website.seo.metadata",
        "website.slug.mixin",
    ]
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Text()
    parent_id = fields.Many2one("guiabh.category", string="Categoria Pai", ondelete="restrict")
    child_ids = fields.One2many("guiabh.category", "parent_id", string="Subcategorias")

    website_menu_ids = fields.One2many("website.menu", "guiabh_category_id", string="Menus do site")

    locals().update(guiabh_base_fields())

    _sql_constraints = [
        ("guiabh_category_name_company_uniq", "unique(name, company_id)", "Categoria já existe para esta empresa."),
        ("guiabh_category_slug_company_uniq", "unique(slug, company_id)", "Slug deve ser único por empresa."),
    ]

    def _slug_name(self):
        return self.name

    def _slugify(self, text):
        """Local slugify compatível com versões sem o helper no odoo.tools."""
        text = unicodedata.normalize("NFKD", text or "")
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9-]+", "-", text.lower())
        return text.strip("-")

    @api.model
    def create(self, vals):
        if not vals.get("slug") and vals.get("name"):
            vals["slug"] = self._slugify(vals["name"])
        records = super().create(vals)
        records._sync_website_menus()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("name", "slug", "website_published", "company_id")):
            self._sync_website_menus()
        return res

    def unlink(self):
        self._remove_website_menus()
        return super().unlink()

    # Menu helpers
    def _sync_website_menus(self):
        Website = self.env["website"]
        Menu = self.env["website.menu"]
        websites = Website.search([])
        for category in self:
            if not category.website_published or not category.slug:
                category._remove_website_menus()
                continue
            for website in websites:
                url = f"/{category.slug}"
                home_menu = Menu.search(
                    [("website_id", "=", website.id), ("url", "=", "/")], limit=1
                )
                main_menu = Menu.search(
                    [
                        ("website_id", "=", website.id),
                        ("guiabh_category_id", "=", category.id),
                        ("parent_id", "=", False),
                    ],
                    limit=1,
                )
                if main_menu:
                    main_menu.write({"name": category.name, "url": url})
                else:
                    Menu.create(
                        {
                            "name": category.name,
                            "url": url,
                            "website_id": website.id,
                            "guiabh_category_id": category.id,
                            "sequence": 30,
                        }
                    )
                if home_menu:
                    submenu = Menu.search(
                        [
                            ("website_id", "=", website.id),
                            ("guiabh_category_id", "=", category.id),
                            ("parent_id", "=", home_menu.id),
                        ],
                        limit=1,
                    )
                    if submenu:
                        submenu.write({"name": category.name, "url": url})
                    else:
                        Menu.create(
                            {
                                "name": category.name,
                                "url": url,
                                "website_id": website.id,
                                "guiabh_category_id": category.id,
                                "parent_id": home_menu.id,
                                "sequence": 40,
                            }
                        )

    def _remove_website_menus(self):
        menus = self.env["website.menu"].search([("guiabh_category_id", "in", self.ids)])
        menus.unlink()
