# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckoutWizard(models.TransientModel):
    _name = 'hotel.checkout.wizard'
    _description = 'Assistant Check-out'

    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', 
                                     required=True, readonly=True)
    folio_id = fields.Many2one(related='reservation_id.folio_id', string='Folio', readonly=True)
    partner_id = fields.Many2one(related='reservation_id.partner_id', string='Client', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Chambre', readonly=True)
    
    # Informations du check-out
    checkout_datetime = fields.Datetime(string='Date/Heure Check-out', 
                                        required=True, default=fields.Datetime.now)
    
    # Montants
    total_amount = fields.Float(related='folio_id.amount_total', string='Montant Total', readonly=True)
    amount_paid = fields.Float(related='folio_id.amount_paid', string='Montant Payé', readonly=True)
    amount_due = fields.Float(related='folio_id.amount_due', string='Solde Dû', readonly=True)
    
    # Paiement
    payment_required = fields.Boolean(string='Paiement Requis', 
                                     compute='_compute_payment_required')
    payment_method_id = fields.Many2one('hotel.payment.method', string='Mode de Paiement')
    payment_amount = fields.Float(string='Montant du Paiement')
    
    # Informations pour mobile money
    mobile_phone = fields.Char(string='Numéro de Téléphone')
    mobile_reference = fields.Char(string='Référence Transaction')
    
    # Informations pour chèque
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')
    
    # Vérifications
    room_inspection = fields.Selection([
        ('ok', 'Chambre OK'),
        ('damage', 'Dommages Constatés'),
        ('cleaning_needed', 'Nettoyage Approfondi Requis'),
    ], string='Inspection de la Chambre', default='ok')
    
    damage_description = fields.Text(string='Description des Dommages')
    damage_cost = fields.Float(string='Coût des Dommages')
    
    # Minibar et services
    minibar_check = fields.Boolean(string='Minibar Vérifié', default=False)
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Satisfaction client
    satisfaction_rating = fields.Selection([
        ('1', 'Très Insatisfait'),
        ('2', 'Insatisfait'),
        ('3', 'Neutre'),
        ('4', 'Satisfait'),
        ('5', 'Très Satisfait'),
    ], string='Satisfaction Client')
    
    @api.depends('amount_due')
    def _compute_payment_required(self):
        for wizard in self:
            wizard.payment_required = wizard.amount_due > 0
    
    @api.onchange('payment_method_id')
    def _onchange_payment_method(self):
        if self.payment_method_id:
            # Pré-remplir le montant avec le solde dû
            self.payment_amount = self.amount_due
    
    @api.onchange('damage_cost')
    def _onchange_damage_cost(self):
        if self.damage_cost > 0:
            # Ajouter le coût des dommages au montant du paiement
            self.payment_amount = self.amount_due + self.damage_cost
    
    def action_confirm_checkout(self):
        """Confirmer le check-out"""
        self.ensure_one()
        
        # Vérifier que tout est payé ou qu'un paiement est enregistré
        total_to_pay = self.amount_due + self.damage_cost
        
        if total_to_pay > 0 and not self.payment_method_id:
            raise UserError(_(
                'Il reste un solde de %s à payer. Veuillez sélectionner un mode de paiement.'
            ) % total_to_pay)
        
        # Ajouter les frais de dommages AVANT le paiement
        if self.damage_cost > 0:
            self._add_damage_charge()
        
        # Enregistrer le paiement si nécessaire
        if self.payment_method_id and self.payment_amount > 0:
            self._create_payment()
        
        # Mettre à jour la réservation
        self.reservation_id.write({
            'state': 'checkout',
            'actual_checkout_date': self.checkout_datetime,
        })
        
        # Mettre à jour le statut de la chambre
        self.room_id.write({'status': 'cleaning'})
        
        # Créer une tâche de nettoyage
        self.env['hotel.housekeeping'].create({
            'room_id': self.room_id.id,
            'cleaning_type': 'checkout',
            'state': 'pending',
            'date': fields.Date.today(),
        })
        
        # Fermer le folio
        self.folio_id.write({'state': 'closed'})
        
        # Ajouter des notes
        notes_body = _('Check-out effectué le %s') % self.checkout_datetime
        if self.notes:
            notes_body += '\n' + _('Notes: %s') % self.notes
        if self.satisfaction_rating:
            notes_body += '\n' + _('Satisfaction client: %s/5') % self.satisfaction_rating
        
        self.reservation_id.message_post(
            body=notes_body,
            subject='Check-out Confirmé'
        )
        
        # Générer la facture si elle n'existe pas
        if not self.folio_id.invoice_ids:
            self.folio_id.action_create_invoice()
        
        # Retourner une action pour afficher le folio (pas la facture)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Folio'),
            'res_model': 'hotel.folio',
            'res_id': self.folio_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_payment(self):
        """
        ✅ CORRECTION PRINCIPALE
        Créer un paiement comptable CORRECT compatible Odoo 18
        """
        self.ensure_one()
        
        # Utiliser la nouvelle méthode du mode de paiement
        payment_vals = self.payment_method_id.get_payment_vals(
            partner_id=self.partner_id.id,
            amount=self.payment_amount,
            folio_id=self.folio_id.id,
            reservation_id=self.reservation_id.id,
            memo=f"Paiement check-out - {self.folio_id.name}"
        )
        
        # Ajouter les informations spécifiques selon le mode de paiement
        if self.payment_method_id.payment_type == 'mobile_money':
            payment_vals.update({
                'mobile_phone': self.mobile_phone,
                'mobile_reference': self.mobile_reference,
            })
        elif self.payment_method_id.payment_type == 'check':
            payment_vals.update({
                'check_number': self.check_number,
                'check_date': self.check_date,
                'check_bank': self.check_bank,
            })
        
        # Créer le paiement
        payment = self.env['account.payment'].create(payment_vals)
        
        # ✅ IMPORTANT : Poster le paiement pour créer les écritures comptables
        payment.action_post()
        
        # Message de confirmation
        self.folio_id.message_post(
            body=_('💰 Paiement de %s enregistré via %s') % (
                self.payment_amount,
                self.payment_method_id.name
            ),
            subject='Paiement Reçu'
        )
        
        return payment
    
    def _add_damage_charge(self):
        """Ajouter les frais de dommages au folio"""
        self.ensure_one()
        
        # Créer une ligne de service pour les dommages
        damage_service = self.env.ref(
            'hotel_management_custom.service_damage',
            raise_if_not_found=False
        )
        
        if not damage_service:
            # Créer le service de dommages s'il n'existe pas
            damage_service = self.env['hotel.service'].create({
                'name': 'Frais de Dommages',
                'category': 'other',
                'price': 0,  # Le prix sera défini par ligne
                'active': True,
            })
        
        self.env['hotel.service.line'].create({
            'folio_id': self.folio_id.id,
            'reservation_id': self.reservation_id.id,
            'service_id': damage_service.id,
            'quantity': 1,
            'price_unit': self.damage_cost,
            'notes': self.damage_description or 'Dommages constatés au check-out',
        })
    
    def action_print_folio(self):
        """Imprimer le folio"""
        self.ensure_one()
        return self.env.ref('hotel_management_custom.action_report_folio').report_action(self.folio_id)