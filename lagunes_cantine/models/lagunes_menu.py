# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


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
        string='Date de début',
        required=True,
        default=fields.Date.today,
        index=True
    )
    
    date_end = fields.Date(
        string='Date de fin',
        required=True,
        default=fields.Date.today,
        index=True,
        help='Date de fin de validité du menu (incluse)'
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
    
    menu_type = fields.Selection([
        ('individual', 'Plats individuels'),
        ('pack', 'Pack de plats'),
    ], string='Type de menu', default='individual', required=True)
    
    is_pack_based = fields.Boolean(
        string='Basé sur un pack',
        compute='_compute_is_pack_based',
        store=True
    )
    
    pack_id = fields.Many2one(
        'lagunes.menu.pack',
        string='Pack de menus',
        ondelete='set null',
        help='Pack de menus réutilisable (optionnel)'
    )
    
    plat_ids = fields.Many2many(
        'lagunes.plat',
        'lagunes_menu_plat_rel',
        'menu_id',
        'plat_id',
        string='Plats du menu',
        help='Liste des plats disponibles dans ce menu'
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True,
        help='Un seul menu actif par entreprise et par jour'
    )
    
    notes = fields.Text(
        string='Notes ou instructions spéciales'
    )
    
    commande_count = fields.Integer(
        string='Nombre de commandes',
        compute='_compute_commande_count'
    )
    
    commande_ids = fields.One2many(
        'lagunes.commande',
        'menu_id',
        string='Commandes'
    )
    
    @api.depends('entreprise_id', 'date', 'date_end')
    def _compute_name(self):
        """Calcul automatique du nom du menu"""
        for menu in self:
            if menu.entreprise_id and menu.date:
                if menu.date == menu.date_end:
                    menu.name = f"{menu.entreprise_id.name} - {menu.date.strftime('%d/%m/%Y')}"
                else:
                    menu.name = f"{menu.entreprise_id.name} - du {menu.date.strftime('%d/%m/%Y')} au {menu.date_end.strftime('%d/%m/%Y')}"
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
    
    @api.depends('menu_type')
    def _compute_is_pack_based(self):
        """Calculer si le menu est basé sur un pack"""
        for menu in self:
            menu.is_pack_based = (menu.menu_type == 'pack')
    
    def _compute_commande_count(self):
        """Compter les commandes pour ce menu"""
        for menu in self:
            menu.commande_count = self.env['lagunes.commande'].search_count([
                ('menu_id', '=', menu.id)
            ])
    
    @api.onchange('menu_type')
    def _onchange_menu_type(self):
        """Gérer le changement de type de menu"""
        if self.menu_type == 'individual':
            # Mode individuel : vider le pack et garder les plats manuels
            self.pack_id = False
        elif self.menu_type == 'pack':
            # Mode pack : vider les plats individuels
            self.plat_ids = [(5, 0, 0)]  # Vider la liste
    
    @api.onchange('pack_id')
    def _onchange_pack_id(self):
        """Charger les plats du pack si sélectionné"""
        if self.pack_id:
            self.plat_ids = [(6, 0, self.pack_id.plat_ids.ids)]
        else:
            self.plat_ids = [(5, 0, 0)]  # Vider si pas de pack
    
    @api.constrains('date', 'date_end')
    def _check_dates(self):
        """Vérifier que la date de fin est après la date de début"""
        for menu in self:
            if menu.date_end and menu.date and menu.date_end < menu.date:
                raise ValidationError(
                    'La date de fin ne peut pas être antérieure à la date de début.'
                )
    
    @api.constrains('entreprise_id', 'date', 'date_end', 'active')
    def _check_unique_active_menu_per_day(self):
        """
        CONTRAINTE STRICTE: Un seul menu actif par entreprise et par période
        Empêche les chevauchements
        """
        for menu in self:
            if menu.active:
                # Chercher d'autres menus actifs pour la même entreprise avec chevauchement
                overlapping = self.search([
                    ('id', '!=', menu.id),
                    ('entreprise_id', '=', menu.entreprise_id.id),
                    ('active', '=', True),
                    '|', '&', 
                    ('date', '<=', menu.date_end),
                    ('date_end', '>=', menu.date),
                    ('date', '<=', menu.date),
                    ('date_end', '>=', menu.date)
                ], limit=1)
                
                if overlapping:
                    raise ValidationError(
                        f"Un menu actif existe déjà pour {menu.entreprise_id.name} "
                        f"pendant la période du {menu.date.strftime('%d/%m/%Y')} au {menu.date_end.strftime('%d/%m/%Y')}.\n\n"
                        f"Menu existant: {overlapping.name}\n"
                        f"Les périodes de menu ne peuvent pas se chevaucher."
                    )
    
    @api.constrains('plat_ids')
    def _check_plat_ids(self):
        """Vérifier qu'il y a au moins un plat dans le menu"""
        for menu in self:
            if menu.active and not menu.plat_ids:
                raise ValidationError(
                    'Un menu actif doit contenir au moins un plat.'
                )
    
    @api.model
    def get_menu_for_entreprise(self, entreprise_id, target_date=None):
        """
        Récupérer le menu actif pour une entreprise à une date donnée
        
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
        
        # Vérifier qu'il n'existe pas déjà un menu actif pour cette date
        existing = self.search([
            ('entreprise_id', '=', self.entreprise_id.id),
            ('date', '=', new_date),
            ('active', '=', True)
        ])
        
        if existing:
            raise ValidationError(
                f"Un menu actif existe déjà pour {self.entreprise_id.name} "
                f"le {new_date.strftime('%d/%m/%Y')}."
            )
        
        new_menu = self.copy(default={
            'date': new_date,
            'active': True
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.menu',
            'res_id': new_menu.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    def toggle_active(self):
        """Activer/Désactiver le menu"""
        for menu in self:
            menu.active = not menu.active