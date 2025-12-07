{
    'name': 'Gestion Hôtelière',
    'version': '18.0.1.0.1',
    'category': 'DIGIFAZ',
    'summary': 'Module complet de gestion d\'hôtel avec réservations, check-in/out, nettoyage et facturation',
    'description': """
        Module de Gestion Hôtelière Complète
        =====================================

        Fonctionnalités principales:
        * Gestion des chambres (types, tarifs, statuts)
        * Tarifs différenciés semaine/week-end
        * Réservations en ligne et sur place
        * Check-in / Check-out automatisé
        * Gestion du nettoyage et maintenance
        * Facturation multi-modes de paiement (Wave CI, Orange Money, Moov, MTN, etc.)
        * Gestion du stock interne
        * Services consommés (room service, bar)
        * Rapports et tableaux de bord détaillés
        * Notifications automatiques

        Fonctionnalités Comptables:
        • Intégration complète avec la comptabilité
        • Gestion des acomptes et paiements partiels
        • Acomptes paramétrables (obligatoire ou non, pourcentage configurable)
        • Paiements anticipés (partiels ou totaux)
        • Modes de paiement liés à des comptes comptables
        • Facturation automatique et comptabilisation
        • Écritures comptables créées automatiquement
        • Rapport comptable détaillé (Pivot, Graphique, Tableau)
        • Paiements d'avance traçables
        • Créditage automatique des dépôts
        • Support Multi-paiement (Espèces, Carte, Chèque, Mobile Money, Virement)
    """,
    'author': 'DIGIFAZ',
    'images': ['static/description/banner.png'], 
    'depends': [
        'base',
        'contacts',
        'account',
        'stock',
        'hr',
        'mail',
        'product',
        'sale',
        'portal',
        'web',
        'base_setup',
    ],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',

        'data/hotel_data.xml',
        'data/hotel_sequence.xml',
        'data/hotel_cron.xml',
        'data/payment_method_data.xml',
        'data/hotel_accounting_data.xml',

        'views/hotel_room_views.xml',
        'views/hotel_room_type_views.xml',

        'views/hotel_reservation_views.xml',
        'views/hotel_folio_views.xml',

        'views/hotel_service_views.xml',
        'views/hotel_service_line_views.xml',

        'views/hotel_housekeeping_views.xml',

        'views/hotel_payment_method_views.xml',

        'wizard/hotel_checkin_wizard_views.xml',
        'wizard/hotel_checkout_wizard_views.xml',

        'views/hotel_menu_views.xml',

        # Vues - Comptabilité (chargées après les vues de base)
        'views/hotel_accounting_views.xml',
        'views/hotel_config_settings_views.xml',

        # Rapports (doivent être chargés avant les boutons d'impression)
        'report/hotel_report_views.xml',
        'report/hotel_reservation_report.xml',
        'report/hotel_folio_report.xml',


        'views/hotel_dashboard_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'currency': 'XOF',
}