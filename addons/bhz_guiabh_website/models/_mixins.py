# Shared mixin helpers for GuiaBH models.
import re
import unicodedata

from odoo import fields


def guiabh_base_fields():
    """Common field definitions for GuiaBH content."""
    return {
        "slug": fields.Char(string="Slug", index=True),
        "cover_image": fields.Binary(string="Cover Image"),
        "featured": fields.Boolean(string="Destacado", default=False),
        "company_id": fields.Many2one(
            "res.company",
            string="Company",
            required=True,
            default=lambda self: self.env.company,
            index=True,
        ),
    }


def slugify_value(text):
    """Simple ASCII slugify without external dependencies."""
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9-]+", "-", text.lower())
    text = text.strip("-")
    return text or "item"
