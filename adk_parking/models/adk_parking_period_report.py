# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class AdkParkingReportWizard(models.TransientModel):
    _name = 'adk.parking.report.wizard'
    _description = 'Assistant : rapport des réservations par période'

    date_from = fields.Date(string='Du', required=True,
                             default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='Au', required=True,
                           default=fields.Date.context_today)
    parking_id = fields.Many2one(
        'adk.parking', string='Parking',
        help="Laisser vide pour inclure tous les parkings.")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError("La date de début doit être antérieure ou égale à la date de fin.")

    def action_print_report(self):
        self.ensure_one()
        data = {
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
            'parking_id': self.parking_id.id or False,
        }
        return self.env.ref('adk_parking.action_report_adk_parking_by_period').report_action(self, data=data)


class ReportAdkParkingByPeriod(models.AbstractModel):
    _name = 'report.adk_parking.report_adk_parking_by_period'
    _description = 'Rapport des réservations par période (contenu)'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        parking_id = data.get('parking_id')

        domain = [('state', '!=', 'cancelled')]
        if parking_id:
            domain.append(('parking_id', '=', parking_id))
        if date_from:
            domain.append(('date_end', '>=', date_from))
        if date_to:
            domain.append(('date_start', '<=', f"{date_to} 23:59:59"))

        reservations = self.env['adk.parking.reservation'].search(domain, order='parking_id, date_start')
        parking = self.env['adk.parking'].browse(parking_id) if parking_id else False

        return {
            'doc_ids': reservations.ids,
            'doc_model': 'adk.parking.reservation',
            'docs': reservations,
            'date_from': date_from,
            'date_to': date_to,
            'parking': parking,
            'total_amount': sum(reservations.mapped('amount_total')),
        }
