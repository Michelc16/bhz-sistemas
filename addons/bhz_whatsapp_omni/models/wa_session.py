import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
        ondelete='cascade',
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

    def _get_starter_base_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('starter_service.base_url')
        if not base_url:
            raise UserError(_("Parâmetro 'starter_service.base_url' não encontrado."))
        return base_url.rstrip('/')

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            if not vals.get('external_base_url'):
                base_url = None
                account_id = vals.get('account_id')
                if account_id:
                    account = self.env['bhz.wa.account'].browse(account_id)
                    if account:
                        base_url = account._get_starter_base_url()
                if not base_url:
                    base_url = self._get_starter_base_url()
                vals['external_base_url'] = base_url

        return super().create(vals_list)

    # Helpers
    def action_get_qr(self):
        for rec in self:
            rec.account_id._fetch_starter_qr(session_id=rec.session_id)
            rec.write({
                'qr_image': rec.account_id.starter_qr_image,
                'last_qr_at': rec.account_id.starter_qr_updated_at,
                'status': 'qr',
            })
        return True

    def action_refresh_status(self):
        for rec in self:
            try:
                resp = rec.account_id._starter_request(
                    'GET',
                    '/status',
                    session_id=rec.session_id,
                    params={'session': rec.session_id},
                )
                data = resp.json()
                rec._apply_status_payload(data)
                rec.account_id._sync_starter_status(data)
            except Exception:
                rec.status = 'error'
        return True

    def action_logout(self):
        for rec in self:
            try:
                rec.account_id._starter_request(
                    'POST',
                    '/logout',
                    session_id=rec.session_id,
                    json={'session': rec.session_id},
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
