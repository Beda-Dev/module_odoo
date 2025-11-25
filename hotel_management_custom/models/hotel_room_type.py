# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Type de Chambre'
    _order = 'sequence, name'

    name = fields.Char(string='Nom du Type', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    capacity = fields.Integer(string='Capacité', required=True, default=2, 
                             help='Nombre maximum de personnes')
    
    # Tarifs semaine
    weekday_rate = fields.Float(string='Tarif Semaine (Lun-Ven)', required=True,
                               help='Tarif applicable du lundi au vendredi')
    
    # Tarifs week-end
    weekend_rate = fields.Float(string='Tarif Week-end (Ven-Dim)', required=True,
                               help='Tarif applicable du vendredi au dimanche')
    
    description = fields.Text(string='Description')
    amenities = fields.Text(string='Équipements',
                           help='Liste des équipements disponibles (WiFi, TV, Climatisation, etc.)')
    
    # Champs calculés
    room_count = fields.Integer(string='Nombre de Chambres', compute='_compute_room_count', store=True)
    available_room_count = fields.Integer(string='Chambres Disponibles', 
                                         compute='_compute_available_rooms')
    
    room_ids = fields.One2many('hotel.room', 'room_type_id', string='Chambres')
    
    active = fields.Boolean(string='Actif', default=True)
    color = fields.Integer(string='Couleur', help='Couleur pour l\'affichage Kanban')
    
    _sql_constraints = [
        ('capacity_check', 'CHECK(capacity > 0)', 'La capacité doit être supérieure à 0.'),
        ('weekday_rate_check', 'CHECK(weekday_rate >= 0)', 'Le tarif semaine doit être positif.'),
        ('weekend_rate_check', 'CHECK(weekend_rate >= 0)', 'Le tarif week-end doit être positif.'),
    ]
    
    @api.depends('room_ids')
    def _compute_room_count(self):
        for record in self:
            record.room_count = len(record.room_ids)
    
    def _compute_available_rooms(self):
        for record in self:
            record.available_room_count = len(
                record.room_ids.filtered(lambda r: r.status == 'available')
            )
    
    def get_rate_for_date(self, date):
        """Retourne le tarif applicable pour une date donnée"""
        self.ensure_one()
        # Vendredi (4), Samedi (5), Dimanche (6)
        if date.weekday() >= 4:  # 4 = vendredi, 5 = samedi, 6 = dimanche
            return self.weekend_rate
        return self.weekday_rate
