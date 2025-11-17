from odoo import api, fields, models
import requests
import base64


class BHZWASession(models.Model):
    _name = 'bhz.wa.session'
    _description = 'Sessão WhatsApp – Starter (QR)'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    session_id = fields.Char(required=True, default='default')
    external_base_url = fields.Char(required=True, string="Starter Base URL")
    account_id = fields.Many2one(
        'bhz.wa.account',
        string="Conta",
        domain=[('mode', '=', 'starter')],
        required=True,
    )

    status = fields.Selection(
        [
            ('new', 'Novo'),
            ('qr', 'Aguardando QR'),
            ('connected', 'Conectado'),
            ('disconnected', 'Desconectado'),
            ('error', 'Erro'),
        ],
        default='new',
        readonly=True,
    )

    paired_number = fields.Char(readonly=True)
    last_qr_at = fields.Datetime(readonly=True)
    qr_image = fields.Binary(string='QR Code (PNG)', readonly=True)

    @api.model
    def create(self, vals):
        if not vals.get('external_base_url') and vals.get('account_id'):
            account = self.env['bhz.wa.account'].browse(vals['account_id'])
            if account:
                vals['external_base_url'] = account._get_starter_base_url()
        return super().create(vals)

    # Helpers
    def _endpoint(self, path):
        return f"{(self.external_base_url or '').rstrip('/')}{path}"

    # Actions

    def action_get_qr(self):
        for rec in self:
            try:
                resp = requests.get(rec._endpoint(f"/qr?session={rec.session_id}"), timeout=20)
                if resp.status_code == 200 and resp.headers.get('Content-Type', '').startswith('image/'):
                    rec.qr_image = base64.b64encode(resp.content)
                    rec.status = 'qr'
                    rec.last_qr_at = fields.Datetime.now()
                else:
                    rec.status = 'error'
            except Exception:
                rec.status = 'error'
        return True

    def action_refresh_status(self):
        for rec in self:
            try:
                j = requests.get(rec._endpoint(f"/status?session={rec.session_id}"), timeout=10).json()
                if j.get('connected'):
                    rec.status = 'connected'
                    rec.paired_number = j.get('me')
                    rec.qr_image = False
                else:
                    rec.status = 'qr' if j.get('awaiting_qr') else 'disconnected'
            except Exception:
                rec.status = 'error'
        return True

    def action_logout(self):
        for rec in self:
            try:
                requests.post(rec._endpoint('/logout'), json={'session': rec.session_id}, timeout=10)
                rec.status = 'disconnected'
                rec.paired_number = False
                rec.qr_image = False
            except Exception:
                rec.status = 'error'
        return True
