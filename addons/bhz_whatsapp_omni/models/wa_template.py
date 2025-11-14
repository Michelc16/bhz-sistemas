from odoo import api, fields, models
import requests, json

class BHZWATemplate(models.Model):
    _name = 'bhz.wa.template'
    _description = 'Template WhatsApp – Business'

    name = fields.Char(required=True)
    namespace = fields.Char(help='Opcional')
    language = fields.Char(default='pt_BR', required=True)
    category = fields.Selection([
        ('MARKETING','MARKETING'),
        ('UTILITY','UTILITY'),
        ('AUTHENTICATION','AUTHENTICATION'),
    ], default='UTILITY')

    body_example = fields.Text()
    status = fields.Selection([('APPROVED','Aprovado'),('REJECTED','Rejeitado'),('PENDING','Pendente')], default='APPROVED')
    account_id = fields.Many2one('bhz.wa.account', domain=[('mode','=','business')], required=True)

    def send(self, to_phone, params=None):
        self.ensure_one()
        acc = self.account_id
        headers = {'Authorization': f'Bearer {acc.business_token}', 'Content-Type': 'application/json'}
        comp = []
        if params:
            comp = [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(p)} for p in params]}]
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_phone.replace('+', '').replace(' ', ''),
            'type': 'template',
            'template': {
                'name': self.name,
                'language': {'code': self.language},
                'components': comp
            }
        }
        url = f"https://graph.facebook.com/v20.0/{acc.business_phone_number_id}/messages"
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        ok = r.status_code in (200, 201)
        state = 'sent' if ok else 'error'
        return self.env['bhz.wa.message'].create({
            'account_id': acc.id,
            'direction': 'out',
            'provider': 'business',
            'remote_jid': f"{payload['to']}@s.whatsapp.net",
            'remote_phone': payload['to'],
            'body': f"[TEMPLATE:{self.name}] {self.body_example or ''}",
            'state': state,
        })
