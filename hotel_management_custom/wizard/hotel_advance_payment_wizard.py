# -*- coding: utf-8 -*-
# hotel_management_custom/wizard/hotel_advance_payment_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HotelAdvancePaymentWizard(models.TransientModel):
    _name = 'hotel.advance.payment.wizard'
    _description = 'Wizard Paiement Anticipé Hôtel'
    
    # Réservation liée
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Réservation',
        required=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        related='reservation_id.partner_id',
        string='Client',
        readonly=True
    )
    
    # Type de paiement
    payment_type = fields.Selection([
        ('deposit', 'Acompte'),
        ('partial', 'Paiement Partiel'),
        ('full', 'Paiement Total'),
    ], string='Type de Paiement', required=True, default='deposit')
    
    # Montant
    amount = fields.Monetary(
        string='Montant',
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='reservation_id.currency_id',
        readonly=True
    )
    
    # Informations paiement
    payment_date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True
    )
    
    # ✅ MODE DE PAIEMENT HÔTEL
    hotel_payment_method_id = fields.Many2one(
        'hotel.payment.method',
        string='Mode de Paiement',
        required=True
    )
    
    # Informations Mobile Money
    mobile_phone = fields.Char(
        string='Numéro de Téléphone',
        help='Requis pour les paiements Mobile Money'
    )
    mobile_reference = fields.Char(
        string='Référence Transaction',
        help='Numéro de transaction Mobile Money'
    )
    
    # Informations Chèque
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')
    
    payment_reference = fields.Char(string='Référence')
    memo = fields.Char(string='Note')
    
    # Champs informatifs
    deposit_amount = fields.Float(
        related='reservation_id.deposit_amount',
        string='Acompte Requis',
        readonly=True
    )
    deposit_paid = fields.Float(
        related='reservation_id.deposit_paid',
        string='Déjà Payé',
        readonly=True
    )
    total_amount = fields.Float(
        related='reservation_id.total_amount',
        string='Montant Total',
        readonly=True
    )
    remaining_deposit = fields.Float(
        string='Acompte Restant',
        compute='_compute_remaining_amounts'
    )
    remaining_total = fields.Float(
        string='Solde Restant',
        compute='_compute_remaining_amounts'
    )
    
    # Affichage conditionnel
    show_deposit_info = fields.Boolean(
        string='Afficher Info Acompte',
        compute='_compute_show_deposit_info'
    )
    
    # Affichage conditionnel des champs selon le mode de paiement
    show_mobile_fields = fields.Boolean(
        compute='_compute_show_fields'
    )
    show_check_fields = fields.Boolean(
        compute='_compute_show_fields'
    )
    
    # Warnings
    display_amount_warning = fields.Boolean(
        compute='_compute_display_amount_warning'
    )
    
    # ============================================================================
    # ✅ CALCULS AUTOMATIQUES
    # ============================================================================
    
    @api.depends('reservation_id')
    def _compute_show_deposit_info(self):
        """Vérifier si l'acompte est activé dans les paramètres"""
        deposit_required = self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_required', default='False'
        ) == 'True'
        
        for wizard in self:
            wizard.show_deposit_info = deposit_required and wizard.reservation_id.require_deposit
    
    @api.depends('deposit_paid', 'deposit_amount', 'total_amount')
    def _compute_remaining_amounts(self):
        for wizard in self:
            wizard.remaining_deposit = max(0, wizard.deposit_amount - wizard.deposit_paid)
            wizard.remaining_total = max(0, wizard.total_amount - wizard.deposit_paid)
    
    @api.depends('amount', 'remaining_total')
    def _compute_display_amount_warning(self):
        for wizard in self:
            wizard.display_amount_warning = wizard.amount > wizard.remaining_total + 0.01
    
    @api.depends('hotel_payment_method_id')
    def _compute_show_fields(self):
        """Afficher les champs selon le type de paiement"""
        for wizard in self:
            if wizard.hotel_payment_method_id:
                wizard.show_mobile_fields = wizard.hotel_payment_method_id.payment_type == 'mobile_money'
                wizard.show_check_fields = wizard.hotel_payment_method_id.payment_type == 'check'
            else:
                wizard.show_mobile_fields = False
                wizard.show_check_fields = False
    
    # ============================================================================
    # ✅ ONCHANGE - AUTOMATISATIONS
    # ============================================================================
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Pré-remplir le montant selon le type"""
        if self.payment_type == 'deposit':
            self.amount = self.remaining_deposit
        elif self.payment_type == 'full':
            self.amount = self.remaining_total
        else:
            self.amount = 0.0
    
    # ============================================================================
    # ✅ CONTRAINTES DE VALIDATION
    # ============================================================================
    
    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_('Le montant du paiement doit être strictement positif.'))
            
            # Tolérance de 0.01 pour éviter les erreurs d'arrondi
            if wizard.amount > wizard.remaining_total + 0.01:
                raise ValidationError(_(
                    'Le montant saisi (%.2f) est supérieur au solde restant à payer (%.2f).\n'
                    'Vous ne pouvez pas encaisser plus que le montant dû.'
                ) % (wizard.amount, wizard.remaining_total))
    
    @api.constrains('hotel_payment_method_id', 'mobile_phone', 'check_number')
    def _check_required_fields(self):
        """Vérifier que les champs requis sont remplis"""
        for wizard in self:
            if wizard.hotel_payment_method_id:
                # Mobile Money : téléphone requis
                if wizard.hotel_payment_method_id.payment_type == 'mobile_money':
                    if wizard.hotel_payment_method_id.require_phone and not wizard.mobile_phone:
                        raise ValidationError(_(
                            'Le numéro de téléphone est requis pour les paiements %s.'
                        ) % wizard.hotel_payment_method_id.name)
                
                # Chèque : numéro requis
                elif wizard.hotel_payment_method_id.payment_type == 'check':
                    if not wizard.check_number:
                        raise ValidationError(_(
                            'Le numéro de chèque est requis.'
                        ))
    
    # ============================================================================
    # ✅ ACTION PRINCIPALE : VALIDER LE PAIEMENT
    # ============================================================================
    
    def action_validate_payment(self):
        """
        ✅ Crée le paiement anticipé, le valide et met à jour la réservation
        """
        self.ensure_one()
        
        # Validations finales
        if self.amount <= 0:
            raise UserError(_('Le montant doit être positif.'))
        
        if self.amount > self.remaining_total + 0.01:
            raise UserError(_(
                'Le montant (%.2f) dépasse le solde restant (%.2f).'
            ) % (self.amount, self.remaining_total))
        
        # ✅ CRÉER ET VALIDER LE PAIEMENT
        payment = self._create_and_post_payment()
        
        # ✅ METTRE À JOUR LA RÉSERVATION
        self._update_reservation_status()
        
        # ✅ NOTIFICATION DE SUCCÈS
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Paiement Enregistré'),
                'message': _('Paiement de %.2f enregistré avec succès via %s.') % (
                    self.amount, 
                    self.hotel_payment_method_id.name
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    # ============================================================================
    # ✅ CRÉATION DU PAIEMENT
    # ============================================================================
    
    def _create_and_post_payment(self):
        """Crée et valide le paiement anticipé"""
        self.ensure_one()
        
        # Préparer les valeurs via la méthode du mode de paiement
        payment_vals = self.hotel_payment_method_id.get_payment_vals(
            partner_id=self.partner_id.id,
            amount=self.amount,
            reservation_id=self.reservation_id.id,
            memo=self.memo or f"Paiement anticipé - {self.reservation_id.name}",
            invoice_id=None  # Pas de facture pour un paiement anticipé
        )
        
        # Ajouter les informations spécifiques
        payment_vals.update({
            'date': self.payment_date,
            'payment_reference': self.payment_reference or f"Acompte {self.reservation_id.name}",
            'is_advance_payment': True,
            'payment_category': self.payment_type,
        })
        
        # Informations Mobile Money
        if self.hotel_payment_method_id.payment_type == 'mobile_money':
            payment_vals.update({
                'mobile_phone': self.mobile_phone,
                'mobile_reference': self.mobile_reference,
            })
        
        # Informations Chèque
        elif self.hotel_payment_method_id.payment_type == 'check':
            payment_vals.update({
                'check_number': self.check_number,
                'check_date': self.check_date,
                'check_bank': self.check_bank,
            })
        
        # Créer le paiement
        payment = self.env['account.payment'].create(payment_vals)
        
        # ✅ VALIDER LE PAIEMENT
        payment.action_post()
        
        return payment
    
    # ============================================================================
    # ✅ MISE À JOUR DE LA RÉSERVATION
    # ============================================================================
    
    def _update_reservation_status(self):
        """Met à jour le statut de la réservation après paiement"""
        self.ensure_one()
        
        # Recalculer les montants
        self.reservation_id._compute_deposit_paid()
        self.reservation_id._compute_amount_paid()
        
        # Marquer la date d'acompte si c'est le premier paiement
        if self.payment_type == 'deposit' and not self.reservation_id.deposit_date:
            self.reservation_id.deposit_date = self.payment_date
        
        # Confirmer automatiquement la réservation si acompte complet payé
        if self.payment_type == 'deposit' and \
           self.reservation_id.deposit_paid >= self.reservation_id.deposit_amount and \
           self.reservation_id.state == 'draft':
            self.reservation_id.action_confirm()
            message = _("✅ Acompte complet de %.2f payé. Réservation confirmée automatiquement.") % self.amount
        else:
            message = _("💰 Paiement de %.2f reçu.") % self.amount
        
        # Message sur la réservation
        self.reservation_id.message_post(
            body=message,
            subject=_("Paiement Anticipé Reçu")
        )
        
        # Mettre à jour le devis si existant
        proforma = self.env['hotel.proforma.invoice'].search([
            ('reservation_id', '=', self.reservation_id.id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)
        
        if proforma:
            proforma.write({'state': 'accepted'})
            proforma.message_post(
                body=_("💰 Paiement de %.2f reçu.") % self.amount,
                subject=_("Paiement Reçu")
            )