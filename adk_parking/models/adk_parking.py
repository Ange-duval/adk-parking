# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdkParking(models.Model):
    _name = 'adk.parking'
    _description = 'Parking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nom du parking', required=True, tracking=True)
    code = fields.Char(string='Code')
    image_1920 = fields.Image(string='Image')
    image_128 = fields.Image(
        string='Image 128', related='image_1920', max_width=128, max_height=128, store=True)
    company_id = fields.Many2one(
        'res.company', string='Société', required=True,
        default=lambda self: self.env.company, tracking=True)
    country_id = fields.Many2one('res.country', string='Pays', tracking=True)
    city = fields.Char(string='Ville', tracking=True)
    district = fields.Char(string='Quartier', tracking=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')

    total_places = fields.Integer(string='Nombre total de places', required=True, default=0, tracking=True)

    responsible_id = fields.Many2one(
        'res.users', string='Responsable Parking', tracking=True,
        help="Personne actuellement en charge de ce parking. Peut être différente "
             "du responsable indiqué sur chaque réservation, notamment si les "
             "responsables sont permutés sur certaines périodes.")

    is_free = fields.Boolean(
        string='Parking gratuit', tracking=True,
        help="Si coché, les réservations Client de ce parking n'ont aucun tarif : "
             "pas de montant, pas de facture, statut de paiement 'Non applicable'.")

    reservation_ids = fields.One2many(
        'adk.parking.reservation', 'parking_id', string='Réservations')

    place_ids = fields.One2many(
        'adk.parking.place', 'parking_id', string='Places')
    place_count = fields.Integer(
        string='Places créées', compute='_compute_place_count')

    reserved_places = fields.Integer(
        string='Places réservées', compute='_compute_places', store=True)
    available_places = fields.Integer(
        string='Places disponibles', compute='_compute_places', store=True)
    occupation_rate = fields.Float(
        string="Taux d'occupation (%)", compute='_compute_places', store=True)

    reserved_employee = fields.Integer(
        string='Places Personnel', compute='_compute_places', store=True)
    reserved_client = fields.Integer(
        string='Places Client', compute='_compute_places', store=True)

    amount_due = fields.Monetary(
        string='Montant impayé (clients)', compute='_compute_amount_due',
        currency_field='currency_id', store=True)
    revenue_total = fields.Monetary(
        string="Chiffre d'affaires (encaissé)", compute='_compute_amount_due',
        currency_field='currency_id', store=True,
        help="Somme des réservations Client entièrement payées sur ce parking "
             "(hors réservations annulées).")

    active = fields.Boolean(default=True)
    color = fields.Integer(string='Couleur Kanban')

    _sql_constraints = [
        ('total_places_positive', 'CHECK(total_places >= 0)',
         'Le nombre total de places ne peut pas être négatif.'),
    ]

    @api.depends('total_places', 'place_ids.state', 'place_ids.current_user_type')
    def _compute_places(self):
        for parking in self:
            reserved_places = parking.place_ids.filtered(lambda p: p.state == 'reserve')
            reserved = len(reserved_places)
            parking.reserved_places = reserved
            parking.available_places = max(parking.total_places - reserved, 0)
            parking.occupation_rate = (
                (reserved / parking.total_places) * 100 if parking.total_places else 0.0)
            parking.reserved_employee = len(
                reserved_places.filtered(lambda p: p.current_user_type == 'employee'))
            parking.reserved_client = len(
                reserved_places.filtered(lambda p: p.current_user_type == 'client'))

    @api.depends('place_ids')
    def _compute_place_count(self):
        for parking in self:
            parking.place_count = len(parking.place_ids)

    def action_generate_places(self):
        """Crée automatiquement les places manquantes jusqu'à atteindre
        le nombre total de places défini sur le parking."""
        Place = self.env['adk.parking.place']
        for parking in self:
            existing = len(parking.place_ids)
            missing = parking.total_places - existing
            if missing <= 0:
                continue
            prefix = (parking.code or 'P').upper()
            existing_names = set(parking.place_ids.mapped('name'))
            vals_list = []
            n = 1
            created = 0
            while created < missing:
                candidate = '%s-%03d' % (prefix, n)
                if candidate not in existing_names:
                    vals_list.append({'name': candidate, 'parking_id': parking.id})
                    existing_names.add(candidate)
                    created += 1
                n += 1
            if vals_list:
                Place.create(vals_list)
        return True

    def action_view_places(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Places',
            'res_model': 'adk.parking.place',
            'view_mode': 'list,form',
            'domain': [('parking_id', '=', self.id)],
            'context': {'default_parking_id': self.id},
        }

    @api.depends('reservation_ids.amount_total', 'reservation_ids.payment_status',
                 'reservation_ids.user_type', 'reservation_ids.state')
    def _compute_amount_due(self):
        for parking in self:
            client_reservations = parking.reservation_ids.filtered(
                lambda r: r.user_type == 'client' and r.state != 'cancelled')
            unpaid = client_reservations.filtered(lambda r: r.payment_status == 'not_paid')
            paid = client_reservations.filtered(lambda r: r.payment_status == 'paid')
            parking.amount_due = sum(unpaid.mapped('amount_total'))
            parking.revenue_total = sum(paid.mapped('amount_total'))

    @api.constrains('total_places')
    def _check_total_places(self):
        for parking in self:
            if parking.total_places < parking.reserved_places:
                raise ValidationError(
                    "Le nombre total de places ne peut pas être inférieur "
                    "au nombre de places déjà réservées.")
