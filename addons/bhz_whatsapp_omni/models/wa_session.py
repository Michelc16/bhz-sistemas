from odoo import api, fields, models
import requests
import base64

class BHZWASession(models.Model):
    _name = 'bhz.wa.session'
    _description = 'Sessão WhatsApp – Starter (QR)'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    session_id = fields.Char(required=True, default='default')
    external_base_url = fields.Char(required=True)
    account_id = fields.Many2one('bhz.wa.account', domain=[('mode', '=', 'starter')])

    status = fields.Selection([
        ('new', 'Novo'), ('qr', 'Aguardando QR'), ('connected', 'Conectado'),
        ('disconnected', 'Desconectado'), ('error', 'Erro')
    ], default='new', readonly=True)

    paired_number = fields.Char(readonly=True)
    last_qr_at = fields.Datetime(readonly=True)
    qr_image = fields.Binary(string='QR Code (PNG)', readonly=True)

    def _endpoint(self, path):
        return f"{(self.external_base_url or '').rstrip('/')}{path}"

    def action_get_qr(self):
        for r in self:
            try:
                resp = requests.get(r._endpoint(f"/qr?session={r.session_id}"), timeout=20)
                if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('image/'):
                    r.qr_image = base64.b64encode(resp.content)
                    r.status = 'qr'
                    r.last_qr_at = fields.Datetime.now()
                else:
                    r.status = 'error'
            except Exception:
                r.status = 'error'
        return True

    def action_refresh_status(self):
        for r in self:
            try:
                j = requests.get(r._endpoint(f"/status?session={r.session_id}"), timeout=10).json()
                if j.get('connected'):
                    r.status = 'connected'
                    r.paired_number = j.get('me')
                    r.qr_image = False
                else:
                    r.status = 'qr' if j.get('awaiting_qr') else 'disconnected'
            except Exception:
                r.status = 'error'
        return True

    def action_logout(self):
        for r in self:
            try:
                requests.post(r._endpoint('/logout'), json={'session': r.session_id}, timeout=10)
                r.status = 'disconnected'
                r.paired_number = False
                r.qr_image = False
            except Exception:
                r.status = 'error'
        return True
