# -*- coding: utf-8 -*-
from odoo import api, fields, models

class BhzAiMemory(models.Model):
    _name = "bhz.ai.memory"
    _description = "Memória Corporativa"
    _order = "create_date desc"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True, index=True)
    tags = fields.Char(help="Tags separadas por vírgula", index=True)
    content = fields.Text(required=True)
    active = fields.Boolean(default=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Anexos')

    @api.model
    def search_memory(self, query=None, tags=None, limit=5):
        domain = [('company_id', '=', self.env.company.id), ('active', '=', True)]
        if tags:
            tag_parts = [t.strip() for t in tags.split(',') if t.strip()]
            for t in tag_parts:
                domain.append(('tags', 'ilike', t))
        if query:
            domain += ['|', '|', ('name', 'ilike', query), ('tags', 'ilike', query), ('content', 'ilike', query)]
        records = self.search(domain, limit=limit, order='create_date desc')
        result = []
        for rec in records:
            snippet = (rec.content or '')[:400]
            result.append({
                'id': rec.id,
                'name': rec.name,
                'tags': rec.tags,
                'excerpt': snippet,
            })
        return result
