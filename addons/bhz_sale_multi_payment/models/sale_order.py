from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_line_ids = fields.One2many(
        "sale.order.payment.line",
        "sale_id",
        string="Formas de pagamento",
        copy=True,
    )
    amount_payment_total = fields.Monetary(
        string="Total dos pagamentos",
        compute="_compute_amount_payment_total",
        currency_field="currency_id",
        store=True,
    )

    @api.depends("payment_line_ids.amount")
    def _compute_amount_payment_total(self):
        for order in self:
            order.amount_payment_total = sum(order.payment_line_ids.mapped("amount"))

    @api.constrains("payment_line_ids", "amount_total")
    def _check_payment_lines_total(self):
        """Garante que o total das formas de pagamento bate com o total do pedido."""
        for order in self:
            # Só valida se o pedido já tem linhas e total
            if order.payment_line_ids:
                # arredonda pra evitar erro de cents
                total_pay = sum(order.payment_line_ids.mapped("amount"))
                if round(total_pay, 2) != round(order.amount_total, 2):
                    raise ValidationError(
                        _("A soma das formas de pagamento (%.2f) deve ser igual ao total do pedido (%.2f).")
                        % (total_pay, order.amount_total)
                    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Ao criar a fatura pela venda, já criamos os pagamentos de acordo com as linhas."""
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        # Só vamos gerar pagamentos se houver faturas e linhas de pagamento
        for order in self:
            if not order.payment_line_ids:
                continue
            # pode haver mais de uma fatura, então pagamos cada uma na ordem
            for invoice in invoices.filtered(lambda i: i.invoice_origin and order.name in i.invoice_origin):
                order._bhz_create_payments_from_lines(invoice)
        return invoices

    def _bhz_create_payments_from_lines(self, invoice):
        """Cria pagamentos (account.payment) para cada linha de pagamento e reconcilia com a fatura."""
        # garantir que a fatura está postada
        if invoice.state != "posted":
            invoice.action_post()

        for line in self.payment_line_ids:
            # cria pagamento direto
            payment_vals = {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_id.id,
                "amount": line.amount,
                "currency_id": self.currency_id.id,
                "date": line.payment_date or fields.Date.context_today(self),
                "journal_id": line.journal_id.id,
                "ref": _("Pagamento venda %s - %s") % (self.name, line.journal_id.name),
            }
            payment = self.env["account.payment"].create(payment_vals)
            payment.action_post()

            # reconciliar com a fatura
            (payment.line_ids + invoice.line_ids).filtered(
                lambda l: l.account_id == invoice.line_ids.filtered(lambda il: il.account_id.internal_type == "receivable").account_id
            ).reconcile()


class SaleOrderPaymentLine(models.Model):
    _name = "sale.order.payment.line"
    _description = "Linhas de pagamento da venda"
    _order = "sequence, id"

    sale_id = fields.Many2one("sale.order", string="Pedido de venda", ondelete="cascade")
    sequence = fields.Integer(default=10)
    journal_id = fields.Many2one(
        "account.journal",
        string="Forma de pagamento",
        domain="[('type', 'in', ('bank', 'cash'))]",
        required=True,
        help="Escolha o diário que representa a forma de pagamento: PIX, Dinheiro, Cartão etc.",
    )
    amount = fields.Monetary(string="Valor", required=True)
    currency_id = fields.Many2one(related="sale_id.currency_id", store=True, readonly=True)
    payment_date = fields.Date(string="Data do pagamento", default=fields.Date.context_today)
    note = fields.Char(string="Observação")
