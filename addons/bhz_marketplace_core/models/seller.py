# -*- coding: utf-8 -*-
import secrets
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class BhzMarketplaceSeller(models.Model):
    _name = "bhz.marketplace.seller"
    _description = "Marketplace Seller"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    user_id = fields.Many2one("res.users", tracking=True, help="Usuário responsável (portal ou interno).")
    state = fields.Selection([
        ("draft", "Rascunho"),
        ("pending", "Pendente"),
        ("approved", "Aprovado"),
        ("rejected", "Rejeitado"),
        ("suspended", "Suspenso"),
    ], default="draft", tracking=True)
    shop_slug = fields.Char(string="Slug da loja", required=True, tracking=True)
    shop_title = fields.Char(string="Título da loja")
    shop_description = fields.Text()
    shop_logo = fields.Image(max_width=512, max_height=512)
    kyc_doc = fields.Binary("Documento KYC")
    kyc_filename = fields.Char("Nome do arquivo")
    payout_bank_name = fields.Char("Banco")
    payout_bank_account = fields.Char("Conta")
    payout_bank_holder = fields.Char("Titular")
    commission_rate = fields.Float("Comissão padrão (%)", default=10.0)

    api_token_ids = fields.One2many("bhz.marketplace.api.token", "seller_id", string="Tokens API")
    product_count = fields.Integer(compute="_compute_counts")
    order_count = fields.Integer(compute="_compute_counts")

    _sql_constraints = [
        ("shop_slug_uniq", "unique(shop_slug)", "Slug já está em uso."),
    ]

    @api.depends("shop_slug")
    def _compute_counts(self):
        Product = self.env["product.template"]
        OrderLine = self.env["sale.order.line"]
        for seller in self:
            seller.product_count = Product.search_count([("bhz_seller_id", "=", seller.id)])
            seller.order_count = OrderLine.search_count([("bhz_seller_id", "=", seller.id)])

    @api.constrains("shop_slug")
    def _check_slug(self):
        for rec in self:
            if rec.shop_slug and " " in rec.shop_slug:
                raise ValidationError("Slug não pode conter espaços.")

    def action_set_pending(self):
        self.write({"state": "pending"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_suspend(self):
        self.write({"state": "suspended"})


class BhzMarketplaceApiToken(models.Model):
    _name = "bhz.marketplace.api.token"
    _description = "Token de API do Marketplace"
    _order = "create_date desc"

    name = fields.Char(default="Token", required=True)
    seller_id = fields.Many2one("bhz.marketplace.seller", required=True, ondelete="cascade")
    token = fields.Char(required=True, default=lambda self: self._generate_token(), copy=False)
    last_used_at = fields.Datetime()

    def _generate_token(self):
        return secrets.token_hex(20)

    def action_rotate(self):
        for rec in self:
            rec.token = self._generate_token()
            rec.last_used_at = False
