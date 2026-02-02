# -*- coding: utf-8 -*-
{
    'name': 'Restaurant des Lagunes - Cantine',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Gestion de cantine d\'entreprise pour Restaurant des Lagunes',
    'description': """
        Module de gestion de cantine d'entreprise
        ==========================================
        
        Fonctionnalités :
        * Gestion des entreprises clientes (type Cantine)
        * Gestion des menus par entreprise et par jour
        * Gestion des plats (produits)
        * Commandes quotidiennes sans facturation immédiate
        * Site web pour prise de commande en ligne
        * Options de plat (sans sel, piment à part)
        * Accès sécurisé par entreprise avec code optionnel
    """,
    'author': 'Restaurant des Lagunes',
    'website': 'https://www.restaurantdeslagunes.com',
    'depends': [
        'base',
        'product',
        'sale_management',
        'website',
        'website_sale',
    ],
    'data': [
        # Sécurité
        'security/lagunes_security.xml',
        'security/ir.model.access.csv',
        'security/lagunes_ir_model_access.xml',
        
        # Données
        'data/product_data.xml',
        'data/plat_option_data.xml',
        
        # Vues
        'views/res_partner_views.xml',
        'views/lagunes_employee_views.xml',
        'views/lagunes_plat_option_views.xml',
        'views/lagunes_menu_template_views.xml',
        'views/lagunes_menu_views.xml',
        'views/lagunes_menu_views_v2.xml',
        'views/lagunes_plat_views.xml',
        'views/lagunes_commande_views.xml',
        'views/lagunes_menu_web.xml',
        
        # Templates Web
        'views/website_templates.xml',
        'views/website_menu_templates.xml',
        'views/website_commande_templates.xml',
        
        # Menus
        'views/lagunes_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'lagunes_cantine/static/src/css/lagunes_frontend.css',
            'lagunes_cantine/static/src/js/lagunes_commande.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
