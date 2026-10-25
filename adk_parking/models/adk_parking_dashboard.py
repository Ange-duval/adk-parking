# -*- coding: utf-8 -*-
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

MONTHS_FR = ['Janv.', 'Févr.', 'Mars', 'Avr.', 'Mai', 'Juin',
             'Juil.', 'Août', 'Sept.', 'Oct.', 'Nov.', 'Déc.']


class AdkParkingDashboard(models.AbstractModel):
    """Données du tableau de bord ADK Parking.

    Les recherches passent par l'ORM : les règles d'accès (multi-sociétés)
    s'appliquent automatiquement à l'utilisateur connecté.
    """
    _name = 'adk.parking.dashboard'
    _description = "Données du tableau de bord ADK Parking"

    @api.model
    def get_data(self, parking_id=0, period='all'):
        today = fields.Date.context_today(self)
        Parking = self.env['adk.parking']
        Reservation = self.env['adk.parking.reservation']
        company = self.env.company
        cur = company.currency_id

        all_parkings = Parking.search([])
        parkings = all_parkings.filtered(lambda p: p.id == parking_id) if parking_id else all_parkings

        r_dom = [('parking_id', 'in', parkings.ids)]
        days = {'30': 30, '90': 90, '365': 365}.get(period)
        if days:
            r_dom.append(('date_start', '>=', today - timedelta(days=days)))
        reservations = Reservation.search(r_dom)
        active = reservations.filtered(lambda r: r.state != 'cancelled')
        clients = active.filtered(lambda r: r.user_type == 'client')
        paid = clients.filtered(lambda r: r.payment_status == 'paid')
        unpaid = clients.filtered(lambda r: r.payment_status == 'not_paid')

        total_places = sum(parkings.mapped('total_places'))
        reserved = sum(parkings.mapped('reserved_places'))
        kpis = {
            'parkings': len(parkings),
            'total_places': total_places,
            'reserved_places': reserved,
            'available_places': sum(parkings.mapped('available_places')),
            'occupation': round(reserved / total_places * 100, 1) if total_places else 0.0,
            'revenue': sum(paid.mapped('amount_total')),
            'due': sum(unpaid.mapped('amount_total')),
            'due_count': len(unpaid),
            'reservations': len(reservations),
            'confirmed': len(reservations.filtered(lambda r: r.state == 'confirmed')),
            'done': len(reservations.filtered(lambda r: r.state == 'done')),
            'collect_rate': round(len(paid) / len(clients) * 100, 1) if clients else 0.0,
        }

        places_split = [
            {'key': 'free', 'label': "Libres", 'value': kpis['available_places']},
            {'key': 'employee', 'label': "Personnel", 'value': sum(parkings.mapped('reserved_employee'))},
            {'key': 'client', 'label': "Clients", 'value': sum(parkings.mapped('reserved_client'))},
        ]
        res_state = [
            {'key': 'draft', 'label': "Brouillon", 'value': len(reservations.filtered(lambda r: r.state == 'draft'))},
            {'key': 'confirmed', 'label': "Confirmées", 'value': kpis['confirmed']},
            {'key': 'done', 'label': "Terminées", 'value': kpis['done']},
            {'key': 'cancelled', 'label': "Annulées", 'value': len(reservations.filtered(lambda r: r.state == 'cancelled'))},
        ]
        payment = [
            {'key': 'paid', 'label': "Payées", 'value': len(paid)},
            {'key': 'not_paid', 'label': "En attente", 'value': len(unpaid)},
            {'key': 'na', 'label': "Sans paiement", 'value': len(active) - len(clients) + len(clients.filtered(lambda r: r.payment_status not in ('paid', 'not_paid')))},
        ]

        by_parking = [{
            'id': p.id, 'name': p.name, 'city': p.city or '', 'district': p.district or '',
            'free': p.is_free, 'total': p.total_places, 'reserved': p.reserved_places,
            'rate': round(p.occupation_rate, 1),
            'revenue': sum(paid.filtered(lambda r: r.parking_id == p).mapped('amount_total')),
            'due': sum(unpaid.filtered(lambda r: r.parking_id == p).mapped('amount_total')),
        } for p in parkings]
        by_parking.sort(key=lambda r: -r['rate'])

        # Évolution sur 6 mois (par date de début)
        first = today.replace(day=1) - relativedelta(months=5)
        monthly = []
        for i in range(6):
            m0 = first + relativedelta(months=i)
            m1 = m0 + relativedelta(months=1)
            mres = active.filtered(lambda r: m0 <= fields.Date.to_date(r.date_start) < m1)
            monthly.append({
                'label': MONTHS_FR[m0.month - 1],
                'bar': len(mres),
                'line': sum(mres.filtered(lambda r: r.user_type == 'client' and r.payment_status == 'paid').mapped('amount_total')),
            })

        tariffs = []
        for tt in clients.mapped('tariff_type_id'):
            sub = clients.filtered(lambda r: r.tariff_type_id == tt)
            tariffs.append({'name': tt.name, 'count': len(sub),
                            'amount': sum(sub.filtered(lambda r: r.payment_status == 'paid').mapped('amount_total'))})
        tariffs.sort(key=lambda r: -r['count'])

        top = []
        for partner in clients.mapped('partner_id'):
            sub = clients.filtered(lambda r: r.partner_id == partner)
            top.append({'name': partner.name, 'count': len(sub),
                        'total': sum(sub.mapped('amount_total')),
                        'paid': sum(sub.filtered(lambda r: r.payment_status == 'paid').mapped('amount_total'))})
        top.sort(key=lambda r: -r['total'])

        managers = []
        for user in active.mapped('responsible_id'):
            sub = active.filtered(lambda r: r.responsible_id == user)
            sub_c = sub.filtered(lambda r: r.user_type == 'client')
            managers.append({
                'name': user.name, 'count': len(sub),
                'revenue': sum(sub_c.filtered(lambda r: r.payment_status == 'paid').mapped('amount_total')),
                'due': sum(sub_c.filtered(lambda r: r.payment_status == 'not_paid').mapped('amount_total')),
            })
        managers.sort(key=lambda r: -r['count'])

        current = reservations.filtered(lambda r: r.state == 'confirmed').sorted(lambda r: r.date_end)[:6]
        unpaid_list = unpaid.sorted(lambda r: r.date_start)[:6]
        user_label = dict(Reservation._fields['user_type'].selection)

        def fmt(dt_):
            return fields.Datetime.context_timestamp(self, dt_).strftime('%d/%m/%Y') if dt_ else ''

        return {
            'today': today.strftime('%d/%m/%Y'),
            'currency': {'symbol': cur.symbol, 'position': cur.position, 'decimals': cur.decimal_places},
            'parkings_all': [{'id': p.id, 'name': p.name} for p in all_parkings],
            'kpis': kpis,
            'places_split': places_split,
            'res_state': res_state,
            'payment': payment,
            'by_parking': by_parking,
            'monthly': monthly,
            'tariffs': tariffs[:5],
            'top_clients': top[:5],
            'managers': managers,
            'current': [{
                'id': r.id, 'name': r.name, 'place': r.place_id.name, 'who': r.partner_id.name,
                'kind': user_label.get(r.user_type), 'parking': r.parking_id.name,
                'end': fmt(r.date_end), 'plate': r.vehicle_plate or '',
            } for r in current],
            'unpaid': [{
                'id': r.id, 'name': r.name, 'who': r.partner_id.name, 'parking': r.parking_id.name,
                'amount': r.amount_total, 'start': fmt(r.date_start), 'invoiced': bool(r.invoice_id),
            } for r in unpaid_list],
        }
