from odoo import api, models


class AutoCompanyMixin(models.AbstractModel):
    _name = "bhz.auto.company.mixin"
    _description = "Preenche company_id com a empresa do usuário"

    @api.model
    def _bhz_default_company_vals(self, vals):
        """
        Aceita tanto um dict quanto uma lista de dicts.
        Se não tiver company_id, coloca a empresa atual.
        """
        company_id = self.env.company.id

        # caso seja uma lista de dicionários
        if isinstance(vals, list):
            for item in vals:
                if "company_id" not in item or not item.get("company_id"):
                    item["company_id"] = company_id
            return vals

        # caso seja só um dicionário
        if "company_id" not in vals or not vals.get("company_id"):
            vals["company_id"] = company_id
        return vals

    @api.model
    def create(self, vals):
        vals = self._bhz_default_company_vals(vals)
        return super(AutoCompanyMixin, self).create(vals)
