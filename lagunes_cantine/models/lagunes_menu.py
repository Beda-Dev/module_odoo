# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class LagunesMenuTemplate(models.Model):
    """Template de menu pouvant être partagé entre plusieurs entreprises"""
    _name = 'lagunes.menu.template'
    _description = 'Template de menu cantine'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom du template',
        required=True,
        translate=True,
        help='Ex: Menu Lundi, Menu Végétarien, Menu Standard'
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10,
        help='Ordre d\'affichage'
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_menu_template_plat_rel',
        'template_id',
        'plat_id',
        string='Plats du template'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    
    notes = fields.Text(
        string='Notes'
    )


class LagunesMenu(models.Model):
    _name = 'lagunes.menu'
    _description = 'Menu de la cantine'
    _order = 'date desc, entreprise_id'

    name = fields.Char(
        string='Nom du menu',
        compute='_compute_name',
        store=True
    )
    
    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='cascade'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )
    
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche'),
    ], string='Jour de la semaine', compute='_compute_day_of_week', store=True)
    
    # Système de validité
    validity_type = fields.Selection([
        ('daily', 'Journalier'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
    ], string='Type de validité', default='daily', required=True,
       help='Défini si ce menu s\'applique pour un jour, une semaine ou un mois')
    
    date_end = fields.Date(
        string='Date de fin de validité',
        compute='_compute_date_end',
        store=True,
        help='Calculée automatiquement selon le type de validité'
    )
    
    is_template_based = fields.Boolean(
        string='Basé sur un template',
        default=False,
        help='Cocher si ce menu est basé sur un template partagé'
    )
    
    template_id = fields.Many2one(
        'lagunes.menu.template',
        string='Template du menu',
        ondelete='set null',
        help='Template de menu partagé (optionnel)'
    )
    
    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_menu_plat_rel',
        'menu_id',
        'plat_id',
        string='Plats du menu'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    
    notes = fields.Text(
        string='Notes ou instructions spéciales'
    )
    
    commande_count = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_commande_count'
    )
    
    @api.depends('entreprise_id', 'date')
    def _compute_name(self):
        """Calcul automatique du nom du menu"""
        for menu in self:
            if menu.entreprise_id and menu.date:
                menu.name = f"{menu.entreprise_id.name} - {menu.date.strftime('%d/%m/%Y')}"
            else:
                menu.name = 'Nouveau menu'
    
    @api.depends('date')
    def _compute_day_of_week(self):
        """Calcul du jour de la semaine"""
        for menu in self:
            if menu.date:
                menu.day_of_week = str(menu.date.weekday())
            else:
                menu.day_of_week = False
    
    @api.depends('date', 'validity_type')
    def _compute_date_end(self):
        """Calculer la date de fin en fonction du type de validité"""
        for menu in self:
            if menu.date:
                if menu.validity_type == 'daily':
                    menu.date_end = menu.date
                elif menu.validity_type == 'weekly':
                    menu.date_end = menu.date + timedelta(days=6)
                elif menu.validity_type == 'monthly':
                    # Dernier jour du mois
                    next_month = menu.date.replace(day=28) + timedelta(days=4)
                    menu.date_end = next_month - timedelta(days=next_month.day)
            else:
                menu.date_end = False
    
    def _compute_commande_count(self):
        """Compter les commandes pour ce menu"""
        for menu in self:
            menu.commande_count = self.env['lagunes.commande'].search_count([
                ('menu_id', '=', menu.id)
            ])
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Charger les plats du template si sélectionné"""
        if self.template_id:
            self.is_template_based = True
            self.plat_ids = [(6, 0, self.template_id.plat_ids.ids)]
        else:
            self.is_template_based = False
    
    @api.constrains('entreprise_id', 'date')
    def _check_unique_menu_per_day(self):
        """Un seul menu par entreprise et par jour"""
        for menu in self:
            duplicate = self.search([
                ('id', '!=', menu.id),
                ('entreprise_id', '=', menu.entreprise_id.id),
                ('date', '=', menu.date)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Un menu existe déjà pour {menu.entreprise_id.name} "
                    f"le {menu.date.strftime('%d/%m/%Y')}"
                )
    
    @api.model
    def get_menu_for_entreprise(self, entreprise_id, target_date=None):
        """
        Récupérer le menu applicable pour une entreprise à une date donnée
        Considère la validité (journalière, hebdomadaire, mensuelle)
        
        :param entreprise_id: ID de l'entreprise
        :param target_date: Date ciblée (aujourd'hui par défaut)
        :return: recordset lagunes.menu
        """
        if target_date is None:
            target_date = date.today()
        
        return self.search([
            ('entreprise_id', '=', entreprise_id),
            ('date', '<=', target_date),
            ('date_end', '>=', target_date),
            ('active', '=', True)
        ], limit=1)
    
    def action_view_commandes(self):
        """Action pour voir les commandes de ce menu"""
        self.ensure_one()
        return {
            'name': f'Commandes - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.commande',
            'view_mode': 'list,form',
            'domain': [('menu_id', '=', self.id)],
            'context': {'default_menu_id': self.id}
        }
    
    def duplicate_menu(self):
        """Dupliquer ce menu pour une autre date"""
        self.ensure_one()
        new_date = self.date + timedelta(days=1)
        
        new_menu = self.copy(default={
            'date': new_date,
            'name': f"{self.entreprise_id.name} - {new_date.strftime('%d/%m/%Y')}"
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.menu',
            'res_id': new_menu.id,
            'view_mode': 'form',
            'target': 'current'
        }
