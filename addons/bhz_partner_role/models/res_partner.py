from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_transporter = fields.Boolean("Transportador")

    business_role = fields.Selection(
        [
            ('person', 'Pessoa'),
            ('company', 'Empresa'),
            ('supplier', 'Fornecedor'),
            ('transporter', 'Transportador'),
            ('none', 'Sem classificação'),
        ],
        string="Classificação",
        default='person',
        compute='_compute_business_role',
        inverse='_inverse_business_role',
        store=True,
    )

    @api.depends('company_type', 'is_transporter')
    def _compute_business_role(self):
        for p in self:
            supplier_rank = getattr(p, 'supplier_rank', 0)  # seguro se purchase não estiver carregado ainda
            if supplier_rank >= 1:
                p.business_role = 'supplier'
            elif p.is_transporter:
                p.business_role = 'transporter'
            elif p.company_type in ('person', 'company'):
                p.business_role = p.company_type
            else:
                p.business_role = 'none'

    def _inverse_business_role(self):
        for p in self:
            if p.business_role == 'person':
                p.company_type = 'person'
                p.is_transporter = False
                if hasattr(p, 'supplier_rank'):
                    p.supplier_rank = 0
            elif p.business_role == 'company':
                p.company_type = 'company'
            elif p.business_role == 'supplier':
                p.company_type = 'company'
                if hasattr(p, 'supplier_rank') and (p.supplier_rank or 0) < 1:
                    p.supplier_rank = 1
                p.is_transporter = False
            elif p.business_role == 'transporter':
                p.company_type = 'company'
                p.is_transporter = True
                if hasattr(p, 'supplier_rank'):
                    p.supplier_rank = 0
