# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    adk_reservation_ids = fields.One2many(
        'adk.parking.reservation', 'invoice_id', string='Réservations de parking')

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals:
            mapping = {
                'paid': 'paid',
                'in_payment': 'paid',
                'partial': 'partial',
                'not_paid': 'not_paid',
                'reversed': 'not_paid',
            }
            for move in self:
                new_status = mapping.get(move.payment_state)
                if new_status and move.adk_reservation_ids:
                    move.adk_reservation_ids.write({'payment_status': new_status})
        return res
