# -*- coding: utf-8 -*-
from odoo import fields, models


class GuiaBHAd(models.Model):
    _name = "guiabh.ad"
    _description = "GuiaBH Ad"
    _order = "sequence, start_date desc"

    name = fields.Char("Título", required=True)
    image = fields.Image("Imagem")
    link_url = fields.Char("URL de destino")
    start_date = fields.Datetime("Início")
    end_date = fields.Datetime("Fim")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    website_id = fields.Many2one(
        "website",
        default=lambda self: self.env["website"].get_current_website(),
    )
    position = fields.Selection([
        ("home_top", "Home - Topo"),
        ("sidebar", "Listagens - Sidebar"),
        ("between_sections", "Entre seções"),
    ], required=True, default="home_top")
    editorial_state = fields.Selection([
        ('pending', 'Pendente'),
        ('approved', 'Aprovado'),
        ('rejected', 'Rejeitado'),
    ], string="Status editorial", default='pending')
    editorial_priority = fields.Integer('Prioridade editorial', default=50, help="Quanto menor, maior prioridade.")
    editorial_notes = fields.Text('Notas editoriais')
    editorial_reviewer_id = fields.Many2one('res.users', string='Revisor')
    editorial_date = fields.Datetime('Data de revisão')
