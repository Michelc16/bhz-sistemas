from odoo import fields, models
import requests
import json


class BHZWATemplate(models.Model):
    _name = 'bhz.wa.template'
    _description = 'Template WhatsApp – Business'

    name = fields.Char(required=True)
    namespace = fields.Char(help='Opcional, depende da configuração da WABA')
    language = fields.Char(default='pt_BR', required=True)
    category = fields.Selection(
        [
            ('MARKETING', 'MARKETING'),
            ('UTILITY', 'UTILITY'),
            ('AUTHENTICATION', 'AUTHENTICATION'),
        ],
        default='UTILITY',
    )

    body_example = fields.Text(string="Exemplo do corpo")
    status = fields.Selection(
        [
            ('APPROVED', 'Aprovado'),
            ('REJECTED', 'Rejeitado'),
            ('PENDING', 'Pendente'),
        ],
        default='APPROVED',
    )
    account_id = fields.Many2one(
        'bhz.wa.account',
        domain=[('mode', '=', 'business')],
        required=True,
    )

    def send(self, to_phone, params=None):
        """
        Dispara template via Cloud API (Business).
        """
        self.ensure_one()
        acc = self.account_id
        headers = {
            'Authorization': f'Bearer {acc.business_token}',
            'Content-Type': 'application/json',
        }

        components = []
        if params:
            components = [{
                'type': 'body',
                'parameters': [{'type': 'text', 'text': str(p)} for p in params],
            }]

        dest = to_phone.replace('+', '').replace(' ', '')

        payload = {
            'messaging_product': 'whatsapp',
            'to': dest,
            'type': 'template',
            'template': {
                'name': self.name,
                'language': {'code': self.language},
                'components': components,
            },
        }
        url = f"https://graph.facebook.com/v20.0/{acc.business_phone_number_id}/messages"
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
            ok = r.status_code in (200, 201)
        except Exception:
            ok = False

        state = 'sent' if ok else 'error'
        return self.env['bhz.wa.message'].create({
            'account_id': acc.id,
            'direction': 'out',
            'provider': 'business',
            'remote_jid': f"{dest}@s.whatsapp.net",
            'remote_phone': dest,
            'body': f"[TEMPLATE:{self.name}] {self.body_example or ''}",
            'state': state,
        })
