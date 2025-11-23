{
    'name': 'Location de Véhicules',
    'version': '2.0',
    'category': 'Services/Location',
    'summary': 'Gestion complète des locations de véhicules avec facturation',
    'description': """
        Module de gestion de location de véhicules
        ==========================================
        
        Fonctionnalités:
        ----------------
        * Gestion complète des véhicules (images, caractéristiques techniques)
        * Gestion des contrats de location
        * Calcul automatique des tarifs et durées
        * Génération de contrats PDF professionnels
        * Intégration comptable (création de factures)
        * Suivi de l'état des véhicules (disponible, loué, maintenance)
        * Gestion des cautions
        * Historique complet des locations
        * Vues multiples (liste, kanban, calendrier, pivot, graphique)
        * Recherches et filtres avancés
        * Suivi des activités et discussions (chatter)
        
        Modules liés:
        -------------
        * Comptabilité (account) pour la facturation
        * Contacts (contacts) pour les clients
        * Base (base) pour les fonctionnalités de base
    """,
    'author': 'Beda',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'account',          # Module comptabilité pour les factures
        'mail',             # Module de messagerie pour le chatter
        'web',              # Module web pour les vues
    ],
    'data': [
        
        'security/location_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/vehicule_views.xml',
        'views/location_views.xml',
        'views/menus.xml',
        'reports/report_contract.xml',
        'reports/report_templates.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 0.00,
    'currency': 'XOF',
}