# -*- coding: utf-8 -*-
from odoo import api, fields, models


class BhzSellerReputation(models.Model):
    _name = "bhz.seller.reputation"
    _description = "Reputação do seller"
    _order = "score desc"

    seller_id = fields.Many2one("bhz.marketplace.seller", required=True)
    total_orders = fields.Integer()
    late_ship_rate = fields.Float()
    cancel_rate = fields.Float()
    return_rate = fields.Float()
    rating_avg = fields.Float()
    score = fields.Float(compute="_compute_score", store=True)

    def init(self):
        super().init()
        cr = self._cr
        # Deduplicar reputações por seller, mantendo o menor id
        cr.execute(
            """
            DELETE FROM bhz_seller_reputation r
            USING bhz_seller_reputation d
            WHERE r.seller_id = d.seller_id AND r.id > d.id
            """
        )
        # Índice único para garantir 1 reputação por seller
        cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bhz_seller_reputation_seller_uniq ON bhz_seller_reputation (seller_id)"
        )

    @api.depends("total_orders", "late_ship_rate", "cancel_rate", "return_rate", "rating_avg")
    def _compute_score(self):
        for rec in self:
            # score simples: base em rating (0-100), penalidades
            base = (rec.rating_avg or 0) / 5.0 * 70  # até 70 pontos
            penalties = (rec.late_ship_rate or 0) * 50 + (rec.cancel_rate or 0) * 60 + (rec.return_rate or 0) * 40
            rec.score = max(0, min(100, base - penalties))
