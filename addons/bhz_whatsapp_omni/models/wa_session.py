from odoo import _, api, fields, models
from odoo.exceptions import UserError
import requests


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
        IrConfig = self.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('starter_service.base_url')
        if not base_url:
            raise UserError(_("Parâmetro 'starter_service.base_url' não encontrado."))
        base_url = base_url.rstrip('/')
        url = f"{base_url}/api/whatsapp/qr"
        for rec in self:
            try:
                resp = requests.get(url, timeout=60)
                resp.raise_for_status()
                data = resp.json()
                qrcode = data.get('qr_image')
                if qrcode:
                    rec.qr_image = qrcode
                    rec.status = 'qr'
                    rec.last_qr_at = fields.Datetime.now()
                rec._apply_status_payload(data)
            except Exception:
                rec.status = 'error'
        return True

    def action_refresh_status(self):
        for rec in self:
            try:
                resp = requests.get(
                    rec._endpoint("/status"),
                    params={'session': rec.session_id},
                    timeout=10,
                )
                data = resp.json()
                rec._apply_status_payload(data)
            except Exception:
                rec.status = 'error'
        return True

    def action_logout(self):
        for rec in self:
            try:
                requests.post(
                    rec._endpoint('/logout'),
                    json={'session': rec.session_id},
                    timeout=10,
                )
                rec.status = 'disconnected'
                rec.paired_number = False
                rec.qr_image = False
            except Exception:
                rec.status = 'error'
        return True

    def _apply_status_payload(self, data):
        status = data.get('status')
        number = data.get('number') or data.get('me')
        if status == 'connected':
            self.status = 'connected'
            self.paired_number = number
            self.qr_image = False
        elif status in ('waiting_qr', 'loading'):
            self.status = 'qr'
        elif status in ('logged_out', 'disconnected'):
            self.status = 'disconnected'
            self.paired_number = False
        elif status == 'error':
            self.status = 'error'
