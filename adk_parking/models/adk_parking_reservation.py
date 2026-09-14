# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AdkParkingReservation(models.Model):
    _name = 'adk.parking.reservation'
    _description = 'Réservation de place de parking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string='Référence', required=True, copy=False,
                        readonly=True, default='Nouveau')

    parking_id = fields.Many2one(
        'adk.parking', string='Parking', required=True, tracking=True,
        ondelete='restrict')
    company_id = fields.Many2one(
        related='parking_id.company_id', string='Société', store=True, readonly=True)
    currency_id = fields.Many2one(
        related='parking_id.currency_id', string='Devise', readonly=True)

    place_id = fields.Many2one(
        'adk.parking.place', string='Place', required=True, tracking=True,
        domain="[('parking_id', '=', parking_id)]",
        help="Place physique attribuée à cette réservation.")

    responsible_id = fields.Many2one(
        'res.users', string='Responsable Parking', tracking=True,
        help="Personne en charge du parking au moment de cette réservation. "
             "Conservé sur chaque réservation (indépendamment du responsable "
             "actuel du parking) pour la traçabilité en cas d'audit, notamment "
             "si les responsables sont permutés sur certaines périodes.")

    user_type = fields.Selection([
        ('employee', 'Personnel'),
        ('client', 'Client'),
    ], string='Type de bénéficiaire', required=True, default='client', tracking=True)

    partner_id = fields.Many2one(
        'res.partner', string='Bénéficiaire', required=True, tracking=True,
        help="Employé (personnel interne) ou client selon le type sélectionné.")
    phone = fields.Char(related='partner_id.phone', string='Téléphone', readonly=False)
    vehicle_plate = fields.Char(string="Plaque d'immatriculation")

    date_start = fields.Datetime(string='Date de début', required=True,
                                  default=fields.Datetime.now, tracking=True)
    date_end = fields.Datetime(string='Date de fin', required=True, tracking=True)

    tariff_type_id = fields.Many2one(
        'adk.parking.tariff.type', string='Type de tarification', tracking=True,
        default=lambda self: self.env.ref(
            'adk_parking.adk_parking_tariff_type_day', raise_if_not_found=False))
    tariff_amount = fields.Monetary(
        string='Tarif unitaire', currency_field='currency_id', default=0.0, tracking=True)
    duration_days = fields.Integer(
        string='Durée (jours)', compute='_compute_amount_total', store=True)
    amount_total = fields.Monetary(
        string='Montant total', compute='_compute_amount_total', store=True,
        currency_field='currency_id', tracking=True)

    is_unlocked = fields.Boolean(
        string='Déverrouillé pour modification', default=False, copy=False,
        help="Une fois la réservation confirmée, le bénéficiaire, le parking, la "
             "place, le type de tarif, le tarif unitaire, le montant et les dates "
             "sont verrouillés. Un manager doit cliquer sur 'Déverrouiller pour "
             "modification' pour pouvoir les modifier. Le déverrouillage est "
             "tracé dans le chatter et se referme automatiquement au prochain "
             "enregistrement.")

    payment_status = fields.Selection([
        ('not_paid', 'Non payé'),
        ('partial', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('na', 'Non applicable'),
    ], string='Statut de paiement', default='not_paid', required=True, tracking=True)

    is_free = fields.Boolean(related='parking_id.is_free', string='Parking gratuit')

    company_initials = fields.Char(
        compute='_compute_company_initials', string='Initiales société')

    invoice_id = fields.Many2one(
        'account.move', string='Facture', readonly=True, copy=False, tracking=True)
    invoice_state = fields.Selection(related='invoice_id.state', string='État facture')
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state', string='État paiement facture')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'adk.parking.reservation') or 'Nouveau'
        return super().create(vals_list)

    @api.onchange('user_type', 'parking_id')
    def _onchange_user_type(self):
        self.partner_id = False
        if self.parking_id and self.parking_id.is_free:
            self.payment_status = 'na'
            self.tariff_amount = 0.0
        elif self.user_type == 'employee':
            self.payment_status = 'na'
        else:
            self.payment_status = 'not_paid'

    @api.onchange('parking_id')
    def _onchange_parking_id(self):
        if self.place_id and self.place_id.parking_id != self.parking_id:
            self.place_id = False
        if self.parking_id and self.parking_id.responsible_id and not self.responsible_id:
            self.responsible_id = self.parking_id.responsible_id
        return {'domain': {'place_id': [('parking_id', '=', self.parking_id.id)]}}

    @api.depends('date_start', 'date_end', 'tariff_type_id.unit_days', 'tariff_amount', 'parking_id.is_free')
    def _compute_amount_total(self):
        for rec in self:
            days = 0
            if rec.date_start and rec.date_end and rec.date_end > rec.date_start:
                delta = rec.date_end - rec.date_start
                days = max(delta.days, 1)
            rec.duration_days = days
            if rec.parking_id and rec.parking_id.is_free:
                rec.amount_total = 0.0
                continue
            unit_days = rec.tariff_type_id.unit_days if rec.tariff_type_id else 0
            units = math.ceil(days / unit_days) if days and unit_days else 0
            rec.amount_total = units * (rec.tariff_amount or 0.0)

    @api.depends('company_id.name')
    def _compute_company_initials(self):
        for rec in self:
            words = (rec.company_id.name or '').split()
            rec.company_initials = ''.join(w[0] for w in words[:2]).upper() if words else ''

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end <= rec.date_start:
                raise ValidationError(
                    "La date de fin doit être postérieure à la date de début.")

    @api.constrains('place_id', 'parking_id')
    def _check_place_parking_match(self):
        for rec in self:
            if rec.place_id and rec.parking_id and rec.place_id.parking_id != rec.parking_id:
                raise ValidationError(
                    "La place sélectionnée n'appartient pas au parking choisi.")

    @api.constrains('parking_id', 'tariff_amount')
    def _check_free_parking_no_tariff(self):
        for rec in self:
            if rec.parking_id and rec.parking_id.is_free and rec.tariff_amount:
                raise ValidationError(
                    "Le parking '%s' est gratuit : aucun tarif ne peut être saisi sur "
                    "une réservation de ce parking." % rec.parking_id.name)

    @api.constrains('place_id', 'state')
    def _check_place_availability(self):
        for rec in self:
            if rec.state != 'confirmed' or not rec.place_id:
                continue
            other_confirmed = self.search([
                ('place_id', '=', rec.place_id.id),
                ('state', '=', 'confirmed'),
                ('id', '!=', rec.id),
            ])
            if other_confirmed:
                raise ValidationError(
                    "La place '%s' est déjà occupée par une autre réservation "
                    "confirmée (%s)." % (rec.place_id.name, other_confirmed[0].name))

    def write(self, vals):
        """Reverrouille automatiquement les champs sensibles après tout
        enregistrement qui ne consiste pas à les déverrouiller explicitement.
        Empêche un déverrouillage laissé ouvert par erreur de rester actif
        indéfiniment sur une réservation confirmée."""
        to_relock = self.env['adk.parking.reservation']
        if 'is_unlocked' not in vals:
            to_relock = self.filtered(lambda r: r.is_unlocked and r.state != 'draft')
        res = super().write(vals)
        if to_relock:
            to_relock.write({'is_unlocked': False})
        return res

    def action_unlock_fields(self):
        """Déverrouille temporairement les champs sensibles (bénéficiaire,
        parking, place, dates, tarif, montant) d'une réservation confirmée,
        pour permettre une correction. L'action est tracée dans le chatter
        pour la traçabilité (anti-fraude)."""
        if not self.env.user.has_group('adk_parking.group_adk_parking_manager'):
            raise UserError(_(
                "Seul un Manager Parking peut déverrouiller les champs "
                "sensibles d'une réservation confirmée."))
        for rec in self:
            rec.is_unlocked = True
            rec.message_post(body=_(
                "🔓 Champs sensibles déverrouillés pour modification par %s "
                "(bénéficiaire, parking, place, dates, tarif, montant). "
                "Le verrouillage sera réactivé automatiquement au prochain "
                "enregistrement."
            ) % rec.env.user.name)
        return True

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_mark_paid(self):
        self.write({'payment_status': 'paid'})

    def action_mark_not_paid(self):
        self.write({'payment_status': 'not_paid'})

    def _get_invoice_product(self):
        product = self.env.ref('adk_parking.product_adk_parking_reservation', raise_if_not_found=False)
        if not product:
            product = self.env['product.product'].search(
                [('default_code', '=', 'ADK-PARKING')], limit=1)
        return product

    def action_create_invoice(self):
        """Crée une facture client (account.move) pour cette réservation.
        Réservé aux parkings payants, aux réservations Client, et ne peut être
        fait qu'une seule fois par réservation."""
        for rec in self:
            if rec.is_free:
                raise UserError(_(
                    "Le parking '%s' est gratuit : aucune facture n'est nécessaire."
                ) % rec.parking_id.name)
            if rec.user_type != 'client':
                raise UserError(_(
                    "Seules les réservations de type Client peuvent être facturées."))
            if rec.invoice_id:
                raise UserError(_("Une facture existe déjà pour cette réservation."))
            if not rec.amount_total:
                raise UserError(_("Le montant total est nul, il n'y a rien à facturer."))
            if not rec.partner_id:
                raise UserError(_("Aucun bénéficiaire n'est défini sur cette réservation."))
        for rec in self:
            product = rec._get_invoice_product()
            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'company_id': rec.company_id.id,
                'invoice_origin': rec.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id if product else False,
                    'name': _("Réservation parking %(parking)s — place %(place)s (%(start)s au %(end)s)") % {
                        'parking': rec.parking_id.name,
                        'place': rec.place_id.name,
                        'start': fields.Date.to_string(rec.date_start),
                        'end': fields.Date.to_string(rec.date_end),
                    },
                    'quantity': 1.0,
                    'price_unit': rec.amount_total,
                })],
            }
            move = self.env['account.move'].sudo().create(move_vals)
            rec.invoice_id = move.id
        return True

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }
