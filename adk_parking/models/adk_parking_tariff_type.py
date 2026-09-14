# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AdkParkingTariffType(models.Model):
    _name = 'adk.parking.tariff.type'
    _description = 'Type de tarification (parking)'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True, translate=True,
                        help="Ex : Par jour, Par semaine, Par mois, Par an...")
    unit_days = fields.Float(
        string='Nombre de jours par unité', required=True, default=1.0,
        help="Nombre de jours couverts par une unité de ce tarif. "
             "Ex : 1 pour 'Par jour', 7 pour 'Par semaine', 30 pour 'Par mois', "
             "365 pour 'Par an'. Sert à calculer automatiquement le montant total "
             "d'une réservation à partir de sa durée.")
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('unit_days_positive', 'CHECK(unit_days > 0)',
         "Le nombre de jours par unité doit être strictement positif."),
    ]

    def name_get(self):
        return [(rec.id, rec.name) for rec in self]
