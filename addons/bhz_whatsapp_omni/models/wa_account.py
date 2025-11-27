from odoo import api, fields, models
from odoo.exceptions import UserError
from uuid import uuid4
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

    starter_session_id = fields.Char(
        string='Sessão Starter',
        copy=False,
        tracking=True,
        help='Identificador usado pelo starter_service.',
    )
    starter_status = fields.Selection(
        [
            ('new', 'Nova'),
            ('loading', 'Carregando'),
            ('waiting_qr', 'Aguardando QR'),
            ('connected', 'Conectada'),
            ('logged_out', 'Desconectada'),
            ('error', 'Erro'),
        ],
        default='new',
        copy=False,
        tracking=True,
    )
    starter_last_qr_request = fields.Datetime(
        string='Último pedido de QR',
        copy=False,
    )
    starter_last_number = fields.Char(
        string='Número pareado',
        copy=False,
    )

    # Starter (configurado globalmente via parâmetros do sistema)
    starter_base_url = fields.Char(
        string='Starter Base URL',
        compute='_compute_starter_settings',
        readonly=True,
    )
    webhook_secret = fields.Char(
        string='Starter Webhook Secret',
        compute='_compute_starter_settings',
        readonly=True,
    )

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

    def send_text(self, to_phone_or_jid, text, partner_id=False, session_id=None):
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
        base = self._get_starter_base_url()
        session_identifier = session_id or self._get_starter_session_identifier()
        payload = {
            'session': session_identifier,
            'to': to,
            'message': text,
        }
        try:
            r = requests.post(f"{base}/send", json=payload, timeout=20)
            r.raise_for_status()
            j = r.json()
            ok = j.get('status') == 'sent'
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
            'wa_from': self.starter_last_number,
            'wa_to': to,
            'payload_json': json.dumps(payload),
        })
        if ok and not self.env.context.get('bypass_limits'):
            self.sent_last_minute += 1
            self.sent_last_hour += 1
        return msg

    def business_send_message(self, to, message):
        self.ensure_one()
        if not self.business_phone_number_id or not self.business_token:
            raise UserError("Configure o Phone Number ID e o Token do Business para enviar mensagens.")
        dest = to
        if '@' in dest:
            dest = dest.replace('@s.whatsapp.net', '')
        dest = dest.replace('+', '').replace(' ', '')
        url = f"https://graph.facebook.com/v20.0/{self.business_phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.business_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': dest,
            'type': 'text',
            'text': {'body': message},
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            data = resp.json()
        except Exception as exc:
            self.message_post(body=f"❌ Erro ao enviar via Business: {exc}")
            return False, {}
        if resp.status_code not in (200, 201):
            self.message_post(body=f"❌ Erro Business ({resp.status_code}): {data}")
            return False, data
        return True, data

    def _business_send_text(self, to, text, partner_id):
        ok, payload_response = self.business_send_message(to, text)
        dest = to
        if '@' in dest:
            dest = dest.replace('@s.whatsapp.net', '')
        dest = dest.replace('+', '').replace(' ', '')

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
            'wa_from': self.business_phone_number_id,
            'wa_to': dest,
            'payload_json': json.dumps(payload_response or {}),
        })
        if ok and not self.env.context.get('bypass_limits'):
            self.sent_last_minute += 1
            self.sent_last_hour += 1
        return msg

    def action_business_test_message(self):
        self.ensure_one()
        if self.mode != 'business':
            raise UserError("Disponível apenas para contas Business.")
        partner = self.env.user.partner_id
        dest = partner.mobile or partner.phone
        if not dest:
            raise UserError("Configure um telefone no seu usuário para enviar o teste.")
        ok, _payload = self.business_send_message(dest, "Teste de envio via WhatsApp Business.")
        if not ok:
            raise UserError("Falha ao enviar a mensagem de teste. Verifique os logs.")
        self.message_post(body=f"✅ Mensagem de teste enviada para {dest}")
        return True

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

    # ----------------- Starter helpers -----------------

    def _compute_starter_settings(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        base_url = (IrConfig.get_param('starter_service.base_url') or '').strip()
        if base_url:
            base_url = base_url.rstrip('/')
        secret = IrConfig.get_param('starter_service.secret') or ''
        for account in self:
            account.starter_base_url = base_url
            account.webhook_secret = secret

    def _get_starter_base_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('starter_service.base_url')
        if not base_url:
            raise UserError(
                "URL do serviço Starter não está configurada. "
                "Peça ao administrador (BHZ) para configurar o parâmetro 'starter_service.base_url'."
            )
        return base_url.rstrip('/')

    def _get_starter_session_identifier(self):
        self.ensure_one()
        if self.starter_session_id:
            return self.starter_session_id
        session_code = f"acc-{self.id}" if self.id else f"tmp-{uuid4().hex[:6]}"
        self.starter_session_id = session_code
        return session_code

    def _ensure_session_record(self, session_identifier, base_url):
        Session = self.env['bhz.wa.session']
        session = Session.search([
            ('account_id', '=', self.id),
            ('session_id', '=', session_identifier),
        ], limit=1)
        vals = {
            'name': f"Sessão {self.name}",
            'session_id': session_identifier,
            'external_base_url': base_url,
            'account_id': self.id,
        }
        if session:
            session.write({'external_base_url': base_url})
        else:
            session = Session.create(vals)
        return session

    def button_starter_connect(self):
        """
        Cria ou reutiliza a sessão Starter e abre o QR em nova janela.
        """
        self.ensure_one()
        if self.mode != 'starter':
            raise UserError("Essa ação só é válida para contas no modo Starter.")
        base_url = self._get_starter_base_url()
        session_identifier = self._get_starter_session_identifier()
        self._ensure_session_record(session_identifier, base_url)
        self.starter_last_qr_request = fields.Datetime.now()
        self.starter_status = 'waiting_qr'
        url = f"{base_url}/qr?session={session_identifier}&format=img"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def button_starter_disconnect(self):
        self.ensure_one()
        if self.mode != 'starter':
            raise UserError("Disponível apenas para contas Starter.")
        session_identifier = self._get_starter_session_identifier()
        try:
            base_url = self._get_starter_base_url()
            requests.post(
                f"{base_url}/logout",
                json={'session': session_identifier},
                timeout=15,
            )
        except Exception:
            pass
        self.write({
            'starter_status': 'logged_out',
            'starter_last_number': False,
        })
        return True

    def button_starter_refresh_status(self):
        for account in self.filtered(lambda a: a.mode == 'starter'):
            session_identifier = account._get_starter_session_identifier()
            try:
                base_url = account._get_starter_base_url()
                resp = requests.get(
                    f"{base_url}/status",
                    params={'session': session_identifier},
                    timeout=10,
                )
                data = resp.json()
                account._sync_starter_status(data)
            except Exception:
                account.starter_status = 'error'
        return True

    def action_connect_starter(self):
        """Compatibilidade com chamadas antigas."""
        return self.button_starter_connect()

    def _sync_starter_status(self, data):
        status = data.get('status') or 'error'
        number = data.get('number')
        vals = {
            'starter_status': status,
        }
        if number:
            vals['starter_last_number'] = number
        self.write(vals)
