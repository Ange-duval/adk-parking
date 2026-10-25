# -*- coding: utf-8 -*-
from odoo import fields, models

# Correspondance entre l'état de paiement de la facture Odoo et le statut de
# paiement de la réservation de parking.
PAYMENT_STATE_MAPPING = {
    'paid': 'paid',
    'in_payment': 'paid',
    'partial': 'partial',
    'not_paid': 'not_paid',
    'reversed': 'not_paid',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    adk_reservation_ids = fields.One2many(
        'adk.parking.reservation', 'invoice_id', string='Réservations de parking')

    def _compute_payment_state(self):
        """Odoo recalcule `payment_state` en interne (sans passer par write()) :
        on se branche donc sur le calcul pour tenir la réservation à jour."""
        super()._compute_payment_state()
        self._adk_sync_reservation_payment()

    def _adk_sync_reservation_payment(self):
        for move in self:
            if not isinstance(move.id, int):
                continue
            status = PAYMENT_STATE_MAPPING.get(move.payment_state)
            reservations = move.adk_reservation_ids.filtered(
                lambda r: status and r.payment_status != status)
            if reservations:
                reservations.write({'payment_status': status})

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals:
            self._adk_sync_reservation_payment()
        return res
