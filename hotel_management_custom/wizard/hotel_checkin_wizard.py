# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckinWizard(models.TransientModel):
    _name = 'hotel.checkin.wizard'
    _description = 'Assistant Check-in'

    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', 
                                     required=True, readonly=True)
    partner_id = fields.Many2one(related='reservation_id.partner_id', string='Client', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Chambre', readonly=True)
    
    # Informations du check-in
    checkin_datetime = fields.Datetime(string='Date/Heure Check-in', 
                                       required=True, default=fields.Datetime.now)
    
    # Vérifications
    identity_verified = fields.Boolean(string='Identité Vérifiée', default=False)
    payment_verified = fields.Boolean(string='Paiement Vérifié', default=False)
    
    # Informations complémentaires
    actual_adults = fields.Integer(string='Nombre d\'Adultes', 
                                   default=lambda self: self._default_adults())
    actual_children = fields.Integer(string='Nombre d\'Enfants', 
                                     default=lambda self: self._default_children())
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Documents requis
    id_card_number = fields.Char(string='Numéro Pièce d\'Identité')
    vehicle_plate = fields.Char(string='Plaque d\'Immatriculation')
    
    def _default_adults(self):
        if self.env.context.get('default_reservation_id'):
            reservation = self.env['hotel.reservation'].browse(
                self.env.context.get('default_reservation_id')
            )
            return reservation.adults
        return 1
    
    def _default_children(self):
        if self.env.context.get('default_reservation_id'):
            reservation = self.env['hotel.reservation'].browse(
                self.env.context.get('default_reservation_id')
            )
            return reservation.children
        return 0
    
    @api.constrains('actual_adults', 'actual_children')
    def _check_capacity(self):
        for wizard in self:
            total = wizard.actual_adults + wizard.actual_children
            if total > wizard.room_id.capacity:
                raise UserError(_(
                    'Le nombre total de personnes (%d) dépasse la capacité de la chambre (%d).'
                ) % (total, wizard.room_id.capacity))
    
    def action_confirm_checkin(self):
        """Confirmer le check-in"""
        self.ensure_one()
        
        # Vérifications
        if not self.identity_verified:
            raise UserError(_('Veuillez vérifier l\'identité du client avant de continuer.'))
        
        # Créer le folio si il n'existe pas
        if not self.reservation_id.folio_id:
            folio = self.env['hotel.folio'].create({
                'partner_id': self.reservation_id.partner_id.id,
                'reservation_id': self.reservation_id.id,
            })
            self.reservation_id.folio_id = folio
        
        # Mettre à jour la réservation
        self.reservation_id.write({
            'state': 'checkin',
            'actual_checkin_date': self.checkin_datetime,
            'adults': self.actual_adults,
            'children': self.actual_children,
        })
        
        # Mettre à jour le statut de la chambre
        self.room_id.write({'status': 'occupied'})
        
        # Ajouter des notes si nécessaire
        if self.notes:
            self.reservation_id.message_post(
                body=_('Notes de check-in: %s') % self.notes
            )
        
        # Message de confirmation
        self.reservation_id.message_post(
            body=_('Check-in effectué le %s') % self.checkin_datetime,
            subject='Check-in Confirmé'
        )
        
        # Retourner une action pour afficher le folio
        return {
            'type': 'ir.actions.act_window',
            'name': _('Folio'),
            'res_model': 'hotel.folio',
            'res_id': self.reservation_id.folio_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_print_checkin(self):
        """Imprimer la fiche de check-in"""
        self.ensure_one()
        return self.env.ref('hotel_management_custom.action_report_checkin').report_action(self.reservation_id)
