# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class LagunesMenuDuplicateWizard(models.TransientModel):
    _name = 'lagunes.menu.duplicate.wizard'
    _description = 'Assistant de duplication de menu'
    
    menu_id = fields.Many2one('lagunes.menu', required=True)
    target_date = fields.Date(string='Date cible', required=True, default=fields.Date.today)
    target_entreprise_ids = fields.Many2many(
        'res.partner',
        string='Entreprises cibles',
        domain=[('is_cantine_client', '=', True)]
    )
    duplicate_mode = fields.Selection([
        ('single', 'Une seule date'),
        ('range', 'Période (tous les jours)'),
        ('weekly', 'Chaque semaine'),
    ], default='single', required=True)
    
    date_end = fields.Date(string='Date de fin')
    
    @api.onchange('menu_id')
    def _onchange_menu_id(self):
        if self.menu_id:
            self.target_entreprise_ids = [(6, 0, [self.menu_id.entreprise_id.id])]
    
    def action_duplicate(self):
        self.ensure_one()
        
        if not self.target_entreprise_ids:
            raise ValidationError("Veuillez sélectionner au moins une entreprise cible.")
        
        if self.duplicate_mode in ['range', 'weekly'] and not self.date_end:
            raise ValidationError("Veuillez spécifier une date de fin pour ce mode de duplication.")
        
        created_menus = self.env['lagunes.menu']
        
        for entreprise in self.target_entreprise_ids:
            if self.duplicate_mode == 'single':
                try:
                    new_menu = self.menu_id.duplicate_menu(
                        target_date=self.target_date,
                        target_entreprise_id=entreprise.id
                    )
                    if new_menu and new_menu.get('res_id'):
                        created_menus |= self.env['lagunes.menu'].browse(new_menu['res_id'])
                except ValidationError as e:
                    # Menu déjà existant, on continue
                    continue
                    
            elif self.duplicate_mode == 'range':
                current_date = self.target_date
                while current_date <= self.date_end:
                    try:
                        new_menu = self.menu_id.duplicate_menu(
                            target_date=current_date,
                            target_entreprise_id=entreprise.id
                        )
                        if new_menu and new_menu.get('res_id'):
                            created_menus |= self.env['lagunes.menu'].browse(new_menu['res_id'])
                    except ValidationError:
                        # Menu déjà existant, on passe
                        pass
                    current_date += timedelta(days=1)
                    
            elif self.duplicate_mode == 'weekly':
                current_date = self.target_date
                while current_date <= self.date_end:
                    # Ne dupliquer que pour les jours de semaine (lundi-vendredi)
                    if current_date.weekday() < 5:  # 0-4 = Lundi-Vendredi
                        try:
                            new_menu = self.menu_id.duplicate_menu(
                                target_date=current_date,
                                target_entreprise_id=entreprise.id
                            )
                            if new_menu and new_menu.get('res_id'):
                                created_menus |= self.env['lagunes.menu'].browse(new_menu['res_id'])
                        except ValidationError:
                            # Menu déjà existant, on passe
                            pass
                    current_date += timedelta(days=7)  # Sauter une semaine
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Menus créés',
            'res_model': 'lagunes.menu',
            'domain': [('id', 'in', created_menus.ids)],
            'view_mode': 'list,form',
            'context': {'create': False}
        }
