# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Service Hôtel'
    _order = 'sequence, name'

    name = fields.Char(string='Nom du Service', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    
    # Catégorie
    category = fields.Selection([
        ('room_service', 'Room Service'),
        ('bar', 'Bar'),
        ('restaurant', 'Restaurant'),
        ('laundry', 'Blanchisserie'),
        ('spa', 'Spa'),
        ('minibar', 'Minibar'),
        ('parking', 'Parking'),
        ('other', 'Autre'),
    ], string='Catégorie', required=True, default='other')
    
    # Prix
    price = fields.Float(string='Prix Unitaire', required=True)
    
    # Taxes
    tax_ids = fields.Many2many('account.tax', string='Taxes', 
                              help='Taxes applicables à ce service')
    
    # Produit lié (pour la gestion du stock)
    product_id = fields.Many2one('product.product', string='Produit', 
                                 help='Lier à un produit pour gérer le stock')
    
    # Description
    description = fields.Text(string='Description')
    
    # Disponibilité
    active = fields.Boolean(string='Actif', default=True)
    available_24h = fields.Boolean(string='Disponible 24h/24', default=False)
    
    # Compteurs
    usage_count = fields.Integer(string='Nombre d\'Utilisations', 
                                 compute='_compute_usage_count')
    
    company_id = fields.Many2one('res.company', string='Société', 
                                default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')
    
    def _compute_usage_count(self):
        for service in self:
            service.usage_count = self.env['hotel.service.line'].search_count([
                ('service_id', '=', service.id)
            ])
    
    def action_view_usage(self):
        """Voir l'historique d'utilisation du service"""
        self.ensure_one()
        return {
            'name': _('Utilisations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.service.line',
            'view_mode': 'list,form',
            'domain': [('service_id', '=', self.id)],
        }
