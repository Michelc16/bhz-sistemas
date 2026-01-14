# -*- coding: utf-8 -*-
from odoo import models


class QuotationDocument(models.Model):
    _inherit = "quotation.document"

    def _compute_form_field_ids(self):
        docs = self.exists()
        missing = self - docs
        for rec in missing:
            rec.form_field_ids = False
        return super(QuotationDocument, docs)._compute_form_field_ids()
