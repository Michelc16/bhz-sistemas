# Shared mixin helpers for GuiaBH models.
from odoo import fields


def guiabh_base_fields():
    """Common field definitions for GuiaBH content."""
    return {
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
