from odoo import api, fields, models

class BHZWAMessage(models.Model):
    _name = 'bhz.wa.message'
    _description = 'Mensagem WhatsApp (Starter/Business)'
    _order = 'id desc'
    _inherit = ['mail.thread']

    account_id = fields.Many2one('bhz.wa.account', required=True, ondelete='cascade')
    session_id = fields.Many2one('bhz.wa.session', ondelete='set null')

    direction = fields.Selection([('in', 'Entrada'), ('out', 'Saída')], required=True)
    state = fields.Selection([('queued', 'Fila'), ('sent', 'Enviado'), ('received', 'Recebido'), ('error', 'Erro')], default='queued')
    provider = fields.Selection([('starter', 'Starter'), ('business', 'Business')], required=True)

    partner_id = fields.Many2one('res.partner')
    remote_jid = fields.Char(required=True)
    remote_phone = fields.Char()
    body = fields.Text()
