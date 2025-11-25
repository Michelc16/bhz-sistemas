from odoo import fields, models


class BHZWAMessage(models.Model):
    _name = 'bhz.wa.message'
    _description = 'Mensagem WhatsApp (Starter/Business)'
    _order = 'id desc'
    _inherit = ['mail.thread']

    account_id = fields.Many2one('bhz.wa.account', required=True, ondelete='cascade')
    session_id = fields.Many2one('bhz.wa.session', ondelete='set null')

    direction = fields.Selection(
        [('in', 'Entrada'), ('out', 'Saída')],
        required=True,
    )
    state = fields.Selection(
        [
            ('new', 'Nova'),
            ('processed', 'Processada'),
            ('queued', 'Fila'),
            ('sent', 'Enviado'),
            ('received', 'Recebido'),
            ('error', 'Erro'),
        ],
        default='new',
    )
    provider = fields.Selection(
        [('starter', 'Starter'), ('business', 'Business')],
        required=True,
    )

    partner_id = fields.Many2one('res.partner', string="Contato")
    remote_jid = fields.Char(required=True)
    remote_phone = fields.Char(string="Telefone")
    wa_from = fields.Char(string='Remetente (wa_from)')
    wa_to = fields.Char(string='Destinatário (wa_to)')
    wa_timestamp = fields.Datetime(
        string='Horário mensagem',
        default=lambda self: fields.Datetime.now(),
    )
    body = fields.Text(string="Mensagem")
    payload_json = fields.Text(string='Payload bruto')

    def process_with_ai(self):
        """Hook futuro para orquestrar IA/assistentes."""
        return True
