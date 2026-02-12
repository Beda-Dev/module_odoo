# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LagunesMenuPack(models.Model):
    """
    Pack de menus réutilisable pour créer rapidement des menus
    Remplace l'ancien concept de 'template'
    """
    _name = 'lagunes.menu.pack'
    _description = 'Pack de menus réutilisable'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom du pack',
        required=True,
        translate=True,
        help='Ex: Pack Semaine 1, Pack Végétarien, Pack Standard'
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help='Ordre d\'affichage'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description du pack de menus'
    )
    
    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_menu_pack_plat_rel',
        'pack_id',
        'plat_id',
        string='Plats du pack',
        help='Ensemble de plats qui composent ce pack'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Désactiver pour archiver le pack sans le supprimer'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Notes internes sur ce pack'
    )
    
    plat_count = fields.Integer(
        string='Nombre de plats',
        compute='_compute_plat_count',
        store=True
    )
    
    @api.depends('plat_ids')
    def _compute_plat_count(self):
        """Compter le nombre de plats dans le pack"""
        for pack in self:
            pack.plat_count = len(pack.plat_ids)
    
    @api.constrains('plat_ids')
    def _check_plat_ids(self):
        """Vérifier qu'il y a au moins un plat dans le pack"""
        for pack in self:
            if not pack.plat_ids:
                raise ValidationError(
                    'Un pack de menus doit contenir au moins un plat.'
                )
    
    def toggle_active(self):
        """Activer/Désactiver le pack"""
        for pack in self:
            pack.active = not pack.active