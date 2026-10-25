# -*- coding: utf-8 -*-
{
    'name': 'ADK Parking',
    'version': '18.0.1.1.0',
    'category': 'Operations/Parking',
    'summary': "Gestion complète des parkings d'entreprise (places, réservations, facturation, tableau de bord) - gratuit",
    'description': """
ADK Parking
===========
Module de gestion de parking pour Odoo 18 :
- Enregistrement de la société et de ses parkings, gratuits ou payants
- Localisation par pays (natif Odoo), ville et quartier
- Nombre de places par parking, calcul automatique des places libres/réservées
- Responsable Parking suivi à la fois sur le parking et sur chaque réservation (audit)
- Réservation des places par le personnel ou par des clients
- Facturation intégrée (Comptabilité) pour les parkings payants, paiement natif Odoo
- Types de tarification entièrement configurables (jour, mois, an, ou personnalisés)
- Tableau de bord "soft" avec KPI et graphique
- Rapports PDF (état du parking, paiements impayés, ticket de réservation,
  réservations par période)
""",
    'author': 'Kambeu Henang Ange Duval',
    'website': '',
    'support': 'duvalkambeu61@gmail.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'account'],
    'data': [
        'security/adk_parking_security.xml',
        'security/ir.model.access.csv',
        'data/adk_parking_sequence.xml',
        'data/adk_parking_product_data.xml',
        'data/adk_parking_tariff_type_data.xml',
        'report/adk_parking_reports.xml',
        'report/adk_parking_report_templates.xml',
        'views/adk_parking_tariff_type_views.xml',
        'views/adk_parking_views.xml',
        'views/adk_parking_place_views.xml',
        'views/adk_parking_reservation_views.xml',
        'views/adk_parking_report_wizard_views.xml',
        'views/adk_parking_dashboard_views.xml',
        'views/adk_parking_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'adk_parking/static/src/js/dashboard.js',
            'adk_parking/static/src/xml/dashboard.xml',
            'adk_parking/static/src/scss/dashboard.scss',
        ],
    },
    'images': ['static/description/banner.parking.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
