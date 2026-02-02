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
    def verify_cantine_access(self, entreprise_id, employee_name, access_code=None):
        """
        Vérifier l'accès d'un employé au menu de son entreprise
        
        :param entreprise_id: ID de l'entreprise
        :param employee_name: Nom de l'employé
        :param access_code: Code d'accès (optionnel)
        :return: dict avec statut et message
        """
        entreprise = self.browse(entreprise_id)
        
        if not entreprise.exists() or not entreprise.is_cantine_client:
            return {'success': False, 'message': 'Entreprise non trouvée ou non cliente'}
        
        # Si le code est requis
        if entreprise.cantine_code_required:
            if not access_code:
                return {'success': False, 'message': 'Code d\'accès requis'}
            if access_code != entreprise.cantine_access_code:
                return {'success': False, 'message': 'Code d\'accès incorrect'}
        
        # Vérifier que le nom de l'employé n'est pas vide
        if not employee_name or len(employee_name.strip()) < 2:
            return {'success': False, 'message': 'Veuillez entrer votre nom complet'}
        
        return {
            'success': True,
            'message': f'Bienvenue {employee_name}',
            'entreprise_name': entreprise.name
        }
