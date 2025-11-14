from odoo import api, fields, models
import requests
import json


class BHZWAAccount(models.Model):
    _name = 'bhz.wa.account'
    _description = 'Conta WhatsApp – Starter/Business'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, default='Conta WhatsApp', tracking=True)
    mode = fields.Selection(
        [
            ('starter', 'Starter (QR – Baileys)'),
            ('business', 'Business (Cloud API)'),
        ],
        required=True,
        default='starter',
        tracking=True,
    )

    # Starter
    starter_base_url = fields.Char(string='Starter Base URL', help='URL do serviço Node/Baileys')
    webhook_secret = fields.Char(string='Starter Webhook Secret')

    # Business (Meta Cloud)
    business_phone_number_id = fields.Char(string="Phone Number ID")
    business_token = fields.Char(string='Business API Token')
    business_verify_token = fields.Char(string='Webhook Verify Token')

    # Anti-abuso
    max_msgs_per_minute = fields.Integer(default=8)
    max_msgs_per_hour = fields.Integer(default=120)
    max_msgs_per_contact_per_hour = fields.Integer(default=30)
    quiet_hours = fields.Char(
        string='Horário Silencioso',
        help='Ex: 22:00-07:59. Dentro desse intervalo, IA não responde.',
    )

    # IA
    ai_enabled = fields.Boolean(string="IA Atendente ativa", default=True)
    ai_endpoint = fields.Char(string="Endpoint IA (Webhook)")
    ai_token = fields.Char(string="Token IA (opcional)")

    # Contadores
    sent_last_minute = fields.Integer(default=0, readonly=True)
    sent_last_hour = fields.Integer(default=0, readonly=True)

    # ----------------- Envio unificado -----------------

    def send_text(self, to_phone_or_jid, text, partner_id=False, session_id='default'):
        """
        Envio unificado, respeitando limites:
        - global por minuto,
        - global por hora,
        - por contato / hora.
        """
        self.ensure_one()

        # Respeita limites, exceto quando chamado com bypass (interno, IA, etc.)
        if not self.env.context.get('bypass_limits'):
            if self.sent_last_minute >= self.max_msgs_per_minute:
                raise ValueError('Limite global por minuto atingido para esta conta.')
            if self.sent_last_hour >= self.max_msgs_per_hour:
                raise ValueError('Limite global por hora atingido para esta conta.')

            one_hour_ago = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
            jids = [to_phone_or_jid] if '@' in to_phone_or_jid else [f"{to_phone_or_jid}@s.whatsapp.net"]
            per_contact = self.env['bhz.wa.message'].search_count([
                ('account_id', '=', self.id),
                ('direction', '=', 'out'),
                ('remote_jid', 'in', jids),
                ('create_date', '>=', one_hour_ago),
            ])
            if per_contact >= self.max_msgs_per_contact_per_hour:
                raise ValueError('Limite por contato/hora atingido para esta conta.')

        if self.mode == 'starter':
            return self._starter_send_text(to_phone_or_jid, text, partner_id, session_id)
        else:
            return self._business_send_text(to_phone_or_jid, text, partner_id)

    def _starter_send_text(self, to, text, partner_id, session_id):
        base = (self.starter_base_url or '').rstrip('/')
        payload = {
            'session': session_id,
            'to': to,
            'text': text,
        }
        try:
            r = requests.post(f"{base}/send", json=payload, timeout=20)
            j = r.json()
            ok = bool(j.get('ok'))
        except Exception:
            ok = False

        state = 'sent' if ok else 'error'
        msg = self.env['bhz.wa.message'].create({
            'account_id': self.id,
            'direction': 'out',
            'partner_id': partner_id,
            'remote_jid': to if '@' in to else f"{to}@s.whatsapp.net",
            'remote_phone': to.replace('@s.whatsapp.net', '') if '@' in to else to,
            'body': text,
            'state': state,
            'provider': 'starter',
        })
        if ok and not self.env.context.get('bypass_limits'):
            self.sent_last_minute += 1
            self.sent_last_hour += 1
        return msg

    def _business_send_text(self, to, text, partner_id):
        phone_id = self.business_phone_number_id
        token = self.business_token

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        dest = to
        if '@' in dest:
            dest = dest.replace('@s.whatsapp.net', '')
        dest = dest.replace('+', '').replace(' ', '')

        payload = {
            'messaging_product': 'whatsapp',
            'to': dest,
            'type': 'text',
            'text': {
                'body': text,
            },
        }
        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
            ok = r.status_code in (200, 201)
        except Exception:
            ok = False

        state = 'sent' if ok else 'error'
        msg = self.env['bhz.wa.message'].create({
            'account_id': self.id,
            'direction': 'out',
            'partner_id': partner_id,
            'remote_jid': f"{dest}@s.whatsapp.net",
            'remote_phone': dest,
            'body': text,
            'state': state,
            'provider': 'business',
        })
        if ok and not self.env.context.get('bypass_limits'):
            self.sent_last_minute += 1
            self.sent_last_hour += 1
        return msg

    # ----------------- IA Atendente -----------------

    def try_ai_autoreply(self, inbound_msg):
        """
        Chama IA externa via webhook para responder mensagem de entrada, respeitando:
        - quiet_hours
        - pequeno anti-spam de IA (não responder várias vezes seguidas em segundos)
        """
        self.ensure_one()
        if not self.ai_enabled:
            return False
        if not self.ai_endpoint:
            return False
        if self._within_quiet_hours():
            return False

        # Evitar spam da IA pro mesmo contato
        last = self.env['bhz.wa.message'].search([
            ('account_id', '=', self.id),
            ('remote_jid', '=', inbound_msg.remote_jid),
        ], order='id desc', limit=1)
        if last and last.id != inbound_msg.id:
            delta = fields.Datetime.now() - last.create_date
            # se houve movimento há menos de 120s, não responde de novo
            if delta.total_seconds() < 120:
                return False

        try:
            headers = {'Content-Type': 'application/json'}
            if self.ai_token:
                headers['Authorization'] = f"Bearer {self.ai_token}"

            body = {
                'from': inbound_msg.remote_phone or inbound_msg.remote_jid,
                'text': inbound_msg.body,
                'context': {
                    'provider': inbound_msg.provider,
                    'account_id': self.id,
                },
            }
            resp = requests.post(self.ai_endpoint, headers=headers, data=json.dumps(body), timeout=20)
            j = resp.json()
            reply = (j or {}).get('reply')
            if reply:
                self.send_text(
                    inbound_msg.remote_jid,
                    reply,
                    partner_id=inbound_msg.partner_id.id if inbound_msg.partner_id else False,
                )
                return True
        except Exception:
            return False
        return False

    # ----------------- Quiet hours -----------------

    def _within_quiet_hours(self):
        """
        quiet_hours = '22:00-07:59'
        Se hora atual (TZ usuário) estiver dentro do range, retorna True.
        """
        if not self.quiet_hours:
            return False
        try:
            start, end = [x.strip() for x in self.quiet_hours.split('-')]
            now = fields.Datetime.context_timestamp(self, fields.Datetime.now()).time()
            now_min = now.hour * 60 + now.minute

            def to_min(s):
                h, m = s.split(':')
                return int(h) * 60 + int(m)

            s_min = to_min(start)
            e_min = to_min(end)

            # Range normal (ex: 08:00-18:00)
            if s_min <= e_min:
                return s_min <= now_min <= e_min
            # Range passando da meia-noite (ex: 22:00-07:00)
            return now_min >= s_min or now_min <= e_min
        except Exception:
            return False

    # ----------------- Crons -----------------

    def cron_reset_minute(self):
        for rec in self.search([]):
            rec.sent_last_minute = 0
        return True

    def cron_reset_hour(self):
        for rec in self.search([]):
            rec.sent_last_hour = 0
        return True
