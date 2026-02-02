# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LagunesEmployee(models.Model):
    _name = 'lagunes.employee'
    _description = 'Employé de la cantine'
    _order = 'name, entreprise_id'

    name = fields.Char(
        string='Nom',
        required=True,
        help='Nom complet de l\'employé'
    )
    
    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade',
        help='Entreprise pour laquelle travaille l\'employé'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Marquer comme inactif pour archiver l\'employé'
    )
    
    commande_ids = fields.One2many(
        'lagunes.commande',
        'employee_id',
        string='Commandes'
    )
    
    commande_count = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_commande_count'
    )
    
    _sql_constraints = [
        ('unique_employee_per_entreprise', 
         'unique(name, entreprise_id)', 
         'Un employé avec ce nom existe déjà dans cette entreprise!')
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        """Normaliser les noms et vérifier l'unicité insensible à la casse"""
        for vals in vals_list:
            if 'name' in vals:
                # Normaliser le nom : trimmer les espaces et utiliser la casse exacte
                vals['name'] = vals['name'].strip()
        
        return super(LagunesEmployee, self).create(vals_list)
    
    def write(self, vals):
        """Normaliser le nom lors de la mise à jour"""
        if 'name' in vals:
            vals['name'] = vals['name'].strip()
        
        return super(LagunesEmployee, self).write(vals)
    
    @api.constrains('name', 'entreprise_id')
    def _check_unique_name_case_insensitive(self):
        """Vérifier l'unicité du nom (insensible à la casse)"""
        for employee in self:
            if employee.name:
                # Chercher les doublons avec LOWER pour l'insensibilité à la casse
                duplicates = self.search([
                    ('id', '!=', employee.id),
                    ('entreprise_id', '=', employee.entreprise_id.id),
                    ('name', '=ilike', employee.name)  # ilike = case-insensitive
                ])
                if duplicates:
                    raise ValidationError(
                        f"Un employé avec le nom '{employee.name}' existe déjà "
                        f"dans l'entreprise '{employee.entreprise_id.name}' "
                        f"(enregistrement: {duplicates[0].name})"
                    )
    
    def _compute_commande_count(self):
        """Compter les commandes de cet employé"""
        for employee in self:
            employee.commande_count = self.env['lagunes.commande'].search_count([
                ('employee_id', '=', employee.id)
            ])
    
    def toggle_active(self):
        """Activer/Désactiver l'employé"""
        for employee in self:
            employee.active = not employee.active
