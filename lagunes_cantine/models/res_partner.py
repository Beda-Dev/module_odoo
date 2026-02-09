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
        help='Code unique pour que les employés accèdent au menu de leur entreprise',
        copy=False
    )
    
    cantine_code_required = fields.Boolean(
        string='Code requis',
        default=False,
        help='Si activé, les employés devront entrer le code d\'accès pour voir le menu'
    )
    
    max_employees = fields.Integer(
        string='Nombre max d\'employés',
        default=0,
        help='Nombre maximum de personnes autorisées à passer commande (0 = illimité)'
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
    
    lagunes_employee_ids = fields.One2many(
        'lagunes.employee',
        'entreprise_id',
        string='Employés'
    )
    
    employee_count = fields.Integer(
        string='Nombre d\'employés',
        compute='_compute_employee_count',
        store=True
    )
    
    active_employee_count = fields.Integer(
        string='Employés actifs',
        compute='_compute_employee_count',
        store=True
    )
    
    @api.depends('lagunes_employee_ids', 'lagunes_employee_ids.active')
    def _compute_employee_count(self):
        """Compter les employés totaux et actifs"""
        for partner in self:
            partner.employee_count = len(partner.lagunes_employee_ids)
            partner.active_employee_count = len(partner.lagunes_employee_ids.filtered(lambda e: e.active))
    
    @api.constrains('cantine_access_code', 'is_cantine_client')
    def _check_access_code_unique(self):
        """Vérifier l'unicité du code d'accès"""
        for partner in self:
            if partner.is_cantine_client and partner.cantine_access_code:
                duplicate = self.search([
                    ('id', '!=', partner.id),
                    ('cantine_access_code', '=', partner.cantine_access_code),
                    ('is_cantine_client', '=', True)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f"Le code d'accès '{partner.cantine_access_code}' est déjà utilisé par {duplicate.name}"
                    )
    
    @api.model
    def verify_cantine_access(self, employee_name, access_code=None, entreprise_id=None):
        """
        Vérifier l'accès d'un employé au menu
        
        :param employee_name: Nom de l'employé
        :param access_code: Code d'accès (optionnel)
        :param entreprise_id: ID de l'entreprise (optionnel, pour compatibilité)
        :return: dict avec statut et message
        """
        # 1. Identifier l'entreprise ou les entreprises candidates
        if access_code:
            entreprises = self.search([
                ('is_cantine_client', '=', True),
                ('cantine_access_code', '=', access_code)
            ])
            if not entreprises:
                return {'success': False, 'message': 'Code d\'accès incorrect'}
        elif entreprise_id:
            entreprises = self.browse(entreprise_id)
            if not entreprises.exists() or not entreprises.is_cantine_client:
                return {'success': False, 'message': 'Entreprise non trouvée'}
        else:
            # Recherche dans toutes les entreprises ne demandant pas de code
            entreprises = self.search([
                ('is_cantine_client', '=', True),
                ('cantine_code_required', '=', False)
            ])
            if not entreprises:
                return {'success': False, 'message': 'Veuillez entrer un code d\'accès pour votre entreprise'}

        if not employee_name or len(employee_name.strip()) < 2:
            return {'success': False, 'message': 'Veuillez entrer votre nom complet'}
        
        employee_name = employee_name.strip()
        
        # 2. Chercher l'employé dans les entreprises candidates
        # On utilise une recherche insensible à la casse
        employee = self.env['lagunes.employee'].sudo().search([
            ('entreprise_id', 'in', entreprises.ids),
            ('name', '=ilike', employee_name),
            ('active', '=', True)
        ], limit=2) # On en prend 2 pour détecter les doublons ambigus
        
        if not employee:
            return {
                'success': False, 
                'message': 'Employé non reconnu ou inactif. Veuillez contacter votre administrateur.'
            }
        
        if len(employee) > 1:
            return {
                'success': False,
                'message': 'Ambiguïté : plusieurs employés portent ce nom dans différentes entreprises. Veuillez fournir un code d\'accès.'
            }
        
        # Succès
        return {
            'success': True,
            'message': f'Bienvenue {employee.name}',
            'entreprise_name': employee.entreprise_id.name,
            'entreprise_id': employee.entreprise_id.id,
            'employee_id': employee.id,
            'employee_name': employee.name
        }
