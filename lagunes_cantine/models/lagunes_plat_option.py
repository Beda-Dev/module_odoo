# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LaguesePlatOption(models.Model):
    _name = 'lagunes.plat.option'
    _description = 'Options pour les plats'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom de l\'option',
        required=True,
        translate=True,
        help='Ex: Sans sel, Piment à part, Sauce à côté'
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help='Ordre d\'affichage des options'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Description détaillée de l\'option'
    )
    
    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_plat_option_rel',
        'option_id',
        'plat_id',
        string='Plats concernés',
        help='Plats auxquels cette option peut s\'appliquer'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Marquer comme inactif pour désactiver l\'option sans la supprimer'
    )
    
    prix_supplementaire = fields.Float(
        string='Prix supplémentaire',
        default=0.0,
        help='Surcoût éventuel pour cette option (0 si gratuit)'
    )
    
    is_global = fields.Boolean(
        string='Option globale',
        default=False,
        help='Si coché, cette option s\'applique automatiquement à tous les plats'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    _sql_constraints = [
        ('unique_option_name', 'unique(name)', 'Une option avec ce nom existe déjà!')
    ]
    
    def toggle_active(self):
        """Activer/Désactiver l'option"""
        for option in self:
            option.active = not option.active
    
    @api.constrains('prix_supplementaire')
    def _check_prix_supplementaire(self):
        """Vérifier que le prix supplémentaire n'est pas négatif"""
        for option in self:
            if option.prix_supplementaire < 0:
                raise ValidationError('Le prix supplémentaire ne peut pas être négatif!')
