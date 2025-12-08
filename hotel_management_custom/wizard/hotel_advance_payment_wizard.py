# -*- coding: utf-8 -*-
# Fichier: hotel_management_custom/wizard/hotel_advance_payment_wizard.py

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
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash'])]"
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Méthode de Paiement',
        required=True,
        domain="[('id', 'in', available_payment_method_line_ids)]"
    )
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_available_payment_method_line_ids'
    )
    
    payment_reference = fields.Char(string='Référence')
    memo = fields.Char(string='Note')
    
    # Champs informatifs - CORRECTION: Changer Monetary en Float
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
    total_amount = fields.Float(  # CORRECTION: Float au lieu de Monetary
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
    
    # Affichage conditionnel de l'acompte
    show_deposit_info = fields.Boolean(
        string='Afficher Info Acompte',
        compute='_compute_show_deposit_info',
        help='Affiche les informations d\'acompte si activé dans les paramètres'
    )
    
    # Warnings
    display_amount_warning = fields.Boolean(
        compute='_compute_display_amount_warning'
    )
    
    @api.depends('reservation_id')
    def _compute_show_deposit_info(self):
        """Vérifier si l'acompte est activé dans les paramètres"""
        deposit_required = self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_required', default='False'
        ) == 'True'
        
        for wizard in self:
            wizard.show_deposit_info = deposit_required and wizard.reservation_id.require_deposit
    
    @api.depends('journal_id')
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines('inbound')
            else:
                wizard.available_payment_method_line_ids = False
    
    @api.depends('deposit_paid', 'deposit_amount', 'total_amount')
    def _compute_remaining_amounts(self):
        for wizard in self:
            wizard.remaining_deposit = wizard.deposit_amount - wizard.deposit_paid
            wizard.remaining_total = wizard.total_amount - wizard.deposit_paid
    
    @api.depends('amount', 'remaining_total')
    def _compute_display_amount_warning(self):
        for wizard in self:
            wizard.display_amount_warning = wizard.amount > wizard.remaining_total
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """Pré-remplir le montant selon le type"""
        if self.payment_type == 'deposit':
            self.amount = self.remaining_deposit
        elif self.payment_type == 'full':
            self.amount = self.remaining_total
        else:
            self.amount = 0.0
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Réinitialiser la méthode de paiement"""
        self.payment_method_line_id = False
    
    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0:
                raise ValidationError(_('Le montant du paiement doit être strictement positif.'))
            
            # Utiliser float_compare pour éviter les erreurs d'arrondi
            # 2 décimales de précision par défaut
            if wizard.amount > wizard.remaining_total + 0.01:
                raise ValidationError(_(
                    'Le montant saisi (%s) est supérieur au solde restant à payer (%s).\n'
                    'Vous ne pouvez pas encaisser plus que le montant dû.'
                ) % (wizard.amount, wizard.remaining_total))
    
    def action_validate_payment(self):
        """Créer le paiement et mettre à jour la réservation"""
        self.ensure_one()
        
        # Validations
        if self.amount <= 0:
            raise UserError(_('Le montant doit être positif.'))
        
        if self.amount > self.remaining_total:
            raise UserError(_(
                'Le montant (%s) dépasse le solde restant (%s).'
            ) % (self.amount, self.remaining_total))
        
        # Créer le paiement
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'payment_reference': self.payment_reference or f"Acompte {self.reservation_id.name}",
            'memo': self.memo,
            'reservation_id': self.reservation_id.id,
            'is_advance_payment': True,
            'payment_category': self.payment_type,
        })
        
        # Poster le paiement
        payment.action_post()
        
        # Mettre à jour la réservation
        if self.payment_type == 'deposit' and self.reservation_id.deposit_paid >= self.reservation_id.deposit_amount:
            # Acompte complet payé
            if self.reservation_id.state == 'draft':
                self.reservation_id.action_confirm()
            
            self.reservation_id.write({
                'deposit_date': self.payment_date,
            })
            
            # Notification
            self.reservation_id.message_post(
                body=_("✅ Acompte de %s payé. Réservation confirmée.") % self.amount,
                subject=_("Acompte Reçu")
            )
        else:
            # Paiement partiel ou total
            self.reservation_id.message_post(
                body=_("💰 Paiement de %s reçu.") % self.amount,
                subject=_("Paiement Reçu")
            )
        
        # Mettre à jour le devis si existant
        proforma = self.env['hotel.proforma.invoice'].search([
            ('reservation_id', '=', self.reservation_id.id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)
        
        if proforma:
            proforma.write({'state': 'accepted'})
            proforma.message_post(
                body=_("💰 Paiement de %s reçu.") % self.amount,
                subject=_("Paiement Reçu")
            )
        
        # Notification de succès et fermeture
        return {
            'type': 'ir.actions.act_window_close',
            'effect': {
                'fadeout': 'slow',
                'message': _('Paiement de %s enregistré avec succès.') % self.amount,
                'type': 'rainbow_man',
            }
        }