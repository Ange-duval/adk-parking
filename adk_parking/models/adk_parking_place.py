# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkParkingPlace(models.Model):
    _name = 'adk.parking.place'
    _description = 'Place de parking'
    _order = 'name'

    name = fields.Char(string='N° de place', required=True)
    parking_id = fields.Many2one(
        'adk.parking', string='Parking', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        related='parking_id.company_id', string='Société', store=True, readonly=True)

    reservation_ids = fields.One2many(
        'adk.parking.reservation', 'place_id', string='Réservations')

    state = fields.Selection([
        ('libre', 'Libre'),
        ('reserve', 'Réservée'),
    ], string='Statut', compute='_compute_state', store=True)

    current_reservation_id = fields.Many2one(
        'adk.parking.reservation', string='Réservation en cours',
        compute='_compute_state', store=True)
    current_partner_id = fields.Many2one(
        'res.partner', string='Occupant actuel',
        related='current_reservation_id.partner_id', store=True)
    current_user_type = fields.Selection(
        related='current_reservation_id.user_type', string='Type occupant', store=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_parking_uniq', 'unique(name, parking_id)',
         'Ce numéro de place existe déjà pour ce parking.'),
    ]

    @api.depends('reservation_ids.state')
    def _compute_state(self):
        for place in self:
            active_res = place.reservation_ids.filtered(lambda r: r.state == 'confirmed')
            place.current_reservation_id = active_res[:1]
            place.state = 'reserve' if active_res else 'libre'
