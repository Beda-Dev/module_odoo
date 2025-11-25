# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Chambre d\'Hôtel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Numéro de Chambre', required=True, tracking=True, copy=False)
    room_type_id = fields.Many2one('hotel.room.type', string='Type de Chambre',
                                   required=True, tracking=True)

    # Statut de la chambre
    status = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupée'),
        ('reserved', 'Réservée'),
        ('cleaning', 'À Nettoyer'),
        ('maintenance', 'En Maintenance'),
        ('blocked', 'Bloquée'),
    ], string='Statut', default='available', required=True, tracking=True)

    # Informations de la chambre
    floor = fields.Integer(string='Étage')
    capacity = fields.Integer(related='room_type_id.capacity', string='Capacité', store=True)
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes Internes')

    # Tarifs (hérités du type mais modifiables)
    weekday_rate = fields.Float(string='Tarif Semaine',
                                compute='_compute_rates', store=True, readonly=False)
    weekend_rate = fields.Float(string='Tarif Week-end',
                                compute='_compute_rates', store=True, readonly=False)

    # Relations
    current_reservation_id = fields.Many2one('hotel.reservation', string='Réservation Actuelle',
                                             compute='_compute_current_reservation', store=False)
    reservation_ids = fields.One2many('hotel.reservation', 'room_id', string='Réservations')
    housekeeping_ids = fields.One2many('hotel.housekeeping', 'room_id', string='Nettoyages')

    # Maintenance
    last_maintenance_date = fields.Date(string='Dernière Maintenance')
    next_maintenance_date = fields.Date(string='Prochaine Maintenance')

    active = fields.Boolean(string='Actif', default=True)
    color = fields.Integer(string='Couleur Kanban')

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Le numéro de chambre doit être unique.'),
    ]

    @api.depends('room_type_id.weekday_rate', 'room_type_id.weekend_rate')
    def _compute_rates(self):
        for room in self:
            if room.room_type_id:
                if not room.weekday_rate:
                    room.weekday_rate = room.room_type_id.weekday_rate
                if not room.weekend_rate:
                    room.weekend_rate = room.room_type_id.weekend_rate

    def _compute_current_reservation(self):
        today = fields.Date.today()
        for room in self:
            current = self.env['hotel.reservation'].search([
                ('room_id', '=', room.id),
                ('state', 'in', ['confirmed', 'checkin']),
                ('checkin_date', '<=', today),
                ('checkout_date', '>=', today),
            ], limit=1)
            room.current_reservation_id = current

    @api.constrains('status')
    def _check_status_change(self):
        for room in self:
            if room.status == 'occupied' and room.current_reservation_id:
                if room.current_reservation_id.state not in ['confirmed', 'checkin']:
                    raise ValidationError(_(
                        'Impossible de marquer la chambre comme occupée '
                        'sans réservation confirmée ou check-in effectué.'
                    ))

    def action_set_available(self):
        """Marquer la chambre comme disponible"""
        self.write({'status': 'available'})
        self.message_post(body=_('Chambre marquée comme disponible'))
        return True

    def action_set_cleaning(self):
        """Marquer la chambre pour nettoyage"""
        self.write({'status': 'cleaning'})
        # Créer une tâche de nettoyage
        self.env['hotel.housekeeping'].create({
            'room_id': self.id,
            'cleaning_type': 'checkout',
            'state': 'pending',
        })
        self.message_post(body=_('Chambre marquée pour nettoyage'))
        return True

    def action_set_maintenance(self):
        """Marquer la chambre en maintenance"""
        self.write({'status': 'maintenance'})
        self.message_post(body=_('Chambre en maintenance'))
        return True

    def action_view_reservations(self):
        """Afficher les réservations de la chambre"""
        self.ensure_one()
        return {
            'name': _('Réservations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form,calendar',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def action_view_housekeeping(self):
        """Afficher l'historique de nettoyage"""
        self.ensure_one()
        return {
            'name': _('Nettoyages - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.housekeeping',
            'view_mode': 'tree,form',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def get_rate_for_date(self, date):
        """Retourne le tarif applicable pour une date donnée"""
        self.ensure_one()
        # Vendredi (4), Samedi (5), Dimanche (6)
        if date.weekday() >= 4:
            return self.weekend_rate
        return self.weekday_rate

    def is_available(self, checkin_date, checkout_date):
        """Vérifie si la chambre est disponible pour les dates données"""
        self.ensure_one()

        # Vérifier si la chambre n'est pas bloquée ou en maintenance
        if self.status in ['blocked', 'maintenance']:
            return False

        # Vérifier les réservations existantes
        overlapping = self.env['hotel.reservation'].search([
            ('room_id', '=', self.id),
            ('state', 'in', ['draft', 'confirmed', 'checkin']),
            '|',
            '&', ('checkin_date', '<=', checkin_date), ('checkout_date', '>', checkin_date),
            '&', ('checkin_date', '<', checkout_date), ('checkout_date', '>=', checkout_date),
        ])

        return not overlapping

    def _cron_check_availability(self):
        """Tâche planifiée: Vérifier la disponibilité des chambres"""
        today = fields.Date.today()

        # Trouver les réservations qui devraient être terminées
        expired_reservations = self.env['hotel.reservation'].search([
            ('state', 'in', ['confirmed', 'checkin']),
            ('checkout_date', '<', today),
        ])

        for reservation in expired_reservations:
            # Créer une activité pour le suivi
            reservation.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=reservation.create_uid.id,
                summary=_('Réservation expirée - Check-out requis'),
                note=_('La réservation %s est expirée. Veuillez effectuer le check-out.') % reservation.name,
            )

        # Vérifier les chambres qui devraient être disponibles
        rooms_to_check = self.search([
            ('status', 'in', ['occupied', 'reserved']),
        ])

        for room in rooms_to_check:
            if not room.current_reservation_id:
                room.write({'status': 'cleaning'})

    def _cron_stock_alert(self):
        pass