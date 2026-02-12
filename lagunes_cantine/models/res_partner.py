# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cantine_client = fields.Boolean(
        string='Client Cantine',
        default=False,
        help='Cocher si ce partenaire est un client de la cantine d\'entreprise'
    )
    
    cantine_access_code = fields.Char(
        string='Code d\'accès',
        help='Code unique OBLIGATOIRE pour accéder au menu',
        copy=False
    )
    
    max_orders_per_day = fields.Integer(
        string='Limite de commandes par jour',
        default=0,
        help='Nombre maximum de commandes par jour (0 = illimité)'
    )
    
    menu_ids = fields.One2many(
        'lagunes.menu',
        'entreprise_id',
        string='Menus'
    )
    
    commande_ids = fields.One2many(
        'lagunes.commande',
        'entreprise_id',
        string='Commandes'
    )
    
    menu_count = fields.Integer(
        string='Nombre de menus',
        compute='_compute_menu_count',
        store=True
    )
    
    commande_count = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_commande_count',
        store=True
    )
    
    @api.depends('menu_ids')
    def _compute_menu_count(self):
        """Compter les menus"""
        for partner in self:
            partner.menu_count = len(partner.menu_ids)
    
    @api.depends('commande_ids')
    def _compute_commande_count(self):
        """Compter les commandes"""
        for partner in self:
            partner.commande_count = len(partner.commande_ids)
    
    @api.constrains('cantine_access_code', 'is_cantine_client')
    def _check_access_code_required(self):
        """Le code d'accès est obligatoire pour les clients cantine"""
        for partner in self:
            if partner.is_cantine_client and not partner.cantine_access_code:
                raise ValidationError(
                    'Le code d\'accès est obligatoire pour les clients de la cantine.\n'
                    'Veuillez définir un code unique (ex: ACME2025, DIGIFAZ123, etc.)'
                )
    
    @api.constrains('cantine_access_code', 'is_cantine_client')
    def _check_access_code_unique(self):
        """Vérifier l'unicité du code d'accès"""
        for partner in self:
            if partner.is_cantine_client and partner.cantine_access_code:
                # Chercher les doublons
                duplicate = self.search([
                    ('id', '!=', partner.id),
                    ('cantine_access_code', '=', partner.cantine_access_code),
                    ('is_cantine_client', '=', True)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        f"Le code d'accès '{partner.cantine_access_code}' est déjà "
                        f"utilisé par {duplicate.name}.\n\n"
                        f"Veuillez choisir un code unique."
                    )
    
    @api.constrains('max_orders_per_day')
    def _check_max_orders_per_day(self):
        """Vérifier que la limite est >= 0"""
        for partner in self:
            if partner.max_orders_per_day < 0:
                raise ValidationError(
                    'La limite de commandes par jour ne peut pas être négative.'
                )
    
    @api.model
    def verify_cantine_access(self, access_code):
        """
        Vérifier l'accès avec le code entreprise uniquement
        
        :param access_code: Code d'accès de l'entreprise
        :return: dict avec statut et message
        """
        if not access_code or len(access_code.strip()) < 3:
            return {
                'success': False, 
                'message': 'Veuillez entrer un code d\'accès valide (minimum 3 caractères)'
            }
        
        access_code = access_code.strip()
        
        # Chercher l'entreprise par code (insensible à la casse)
        entreprise = self.search([
            ('is_cantine_client', '=', True),
            ('cantine_access_code', '=ilike', access_code)
        ], limit=1)
        
        if not entreprise:
            return {
                'success': False, 
                'message': 'Code d\'accès incorrect. Veuillez vérifier et réessayer.'
            }
        
        # Succès
        return {
            'success': True,
            'message': f'Bienvenue chez {entreprise.name}',
            'entreprise_name': entreprise.name,
            'entreprise_id': entreprise.id,
            'max_orders_per_day': entreprise.max_orders_per_day
        }