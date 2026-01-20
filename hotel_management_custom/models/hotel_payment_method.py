# -*- coding: utf-8 -*-
# hotel_management_custom/models/hotel_payment_method.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelPaymentMethod(models.Model):
    _name = 'hotel.payment.method'
    _description = 'Mode de Paiement Hôtel'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    code = fields.Char(string='Code', required=True, help='Code unique pour le mode de paiement')

    # Type de paiement
    payment_type = fields.Selection([
        ('cash', 'Espèces'),
        ('bank_card', 'Carte Bancaire'),
        ('check', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Virement Bancaire'),
    ], string='Type', required=True, default='cash')

    # Informations pour Mobile Money
    mobile_provider = fields.Selection([
        ('wave_ci', 'Wave CI'),
        ('orange_money', 'Orange Money'),
        ('moov_money', 'Moov Money'),
        ('mtn_money', 'MTN Money'),
    ], string='Opérateur Mobile Money')

    # Configuration
    require_reference = fields.Boolean(string='Référence Requise',
                                       help='Exiger un numéro de référence pour ce mode de paiement')
    require_phone = fields.Boolean(string='Téléphone Requis',
                                   help='Exiger un numéro de téléphone (pour mobile money)')

    # ============= CONFIGURATION COMPTABLE ODOO 18 =============
    # Journal comptable
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal Comptable',
        required=False,  # Changed to False to allow creation without journal
        domain=[('type', 'in', ['cash', 'bank'])],
        help='Journal comptable où les paiements seront enregistrés',
        default=lambda self: self._default_journal_id()
    )
    
    @api.model
    def _default_journal_id(self):
        # Default journal based on payment type, but since payment_type is not set yet, return False
        return False
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'cash':
            journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', self.env.company.id)], limit=1)
            self.journal_id = journal
        elif self.payment_type in ['bank_card', 'check', 'mobile_money', 'bank_transfer']:
            journal = self.env['account.journal'].search([('type', '=', 'bank'), ('company_id', '=', self.env.company.id)], limit=1)
            self.journal_id = journal
        else:
            self.journal_id = False
    inbound_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        string='Méthodes de Paiement Disponibles',
        compute='_compute_payment_method_line_ids',
        store=False
    )
    
    # Méthode de paiement par défaut (OBLIGATOIRE pour Odoo 18)
    default_payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Méthode de Paiement par Défaut',
        required=False,  # Changed to False to allow creation without it
        domain="[('id', 'in', inbound_payment_method_line_ids)]",
        help='Méthode de paiement utilisée par défaut pour ce mode'
    )
    
    # Comptes comptables (optionnels mais recommandés)
    account_debit_id = fields.Many2one(
        'account.account',
        string='Compte de Débit',
        help='Compte comptable pour débiter lors du paiement (ex: Caisse, Banque)',
        domain=[('deprecated', '=', False)]
    )
    account_credit_id = fields.Many2one(
        'account.account',
        string='Compte de Crédit',
        help='Compte comptable pour créditer lors du paiement (généralement Client ou Acomptes)',
        domain=[('deprecated', '=', False)]
    )
    
    # Compte spécifique pour les acomptes
    advance_payment_account_id = fields.Many2one(
        'account.account',
        string='Compte Acomptes',
        help='Compte comptable pour créditer les acomptes (doit être de type liability_current)',
        domain=[('account_type', '=', 'liability_current'), ('deprecated', '=', False)]
    )

    # Disponibilité
    active = fields.Boolean(string='Actif', default=True)

    # Statistiques
    usage_count = fields.Integer(string='Nombre d\'Utilisations',
                                 compute='_compute_usage_count')

    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Le code du mode de paiement doit être unique.'),
    ]

    # ============================================================================
    # ✅ CALCULS AUTOMATIQUES
    # ============================================================================
    
    @api.depends('journal_id')
    def _compute_payment_method_line_ids(self):
        """Calcule les méthodes de paiement disponibles selon le journal"""
        for method in self:
            if method.journal_id:
                method.inbound_payment_method_line_ids = method.journal_id._get_available_payment_method_lines('inbound')
            else:
                method.inbound_payment_method_line_ids = False

    def _compute_usage_count(self):
        for method in self:
            method.usage_count = self.env['account.payment'].search_count([
                ('hotel_payment_method_id', '=', method.id)
            ])

    # ============================================================================
    # ✅ ONCHANGE - AUTOMATISATIONS
    # ============================================================================
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Réinitialise et pré-sélectionne la méthode de paiement par défaut"""
        self.default_payment_method_line_id = False
        if self.journal_id:
            available_methods = self.journal_id._get_available_payment_method_lines('inbound')
            if available_methods:
                # Pré-sélectionner la première méthode disponible
                self.default_payment_method_line_id = available_methods[0]

    @api.onchange('mobile_provider')
    def _onchange_mobile_provider(self):
        if self.mobile_provider:
            self.payment_type = 'mobile_money'
            self.require_phone = True

    # ============================================================================
    # ✅ CONTRAINTES DE VALIDATION
    # ============================================================================
    
    @api.constrains('journal_id', 'default_payment_method_line_id')
    def _check_payment_method_line(self):
        """Vérifie que la méthode de paiement appartient bien au journal"""
        for method in self:
            if method.default_payment_method_line_id:
                if method.default_payment_method_line_id not in method.inbound_payment_method_line_ids:
                    raise ValidationError(_(
                        'La méthode de paiement sélectionnée n\'est pas disponible pour le journal "%s".'
                    ) % method.journal_id.name)

    @api.constrains('account_debit_id', 'account_credit_id', 'journal_id')
    def _check_accounting_config(self):
        """Vérifier que la configuration comptable est cohérente"""
        for method in self:
            # Si des comptes sont définis, ils doivent être valides
            if method.account_debit_id and method.account_debit_id.deprecated:
                raise ValidationError(_(
                    'Le compte de débit "%s" est obsolète. Veuillez en sélectionner un autre.'
                ) % method.account_debit_id.name)
            
            if method.account_credit_id and method.account_credit_id.deprecated:
                raise ValidationError(_(
                    'Le compte de crédit "%s" est obsolète. Veuillez en sélectionner un autre.'
                ) % method.account_credit_id.name)

    # ============================================================================
    # ✅ MÉTHODE PRINCIPALE : GÉNÉRER LES VALEURS DE PAIEMENT
    # ============================================================================
    
    def get_payment_vals(self, partner_id, amount, folio_id=None, reservation_id=None, 
                        memo=None, invoice_id=None):
        """
        ✅ Génère les valeurs COMPLÈTES pour créer un account.payment compatible Odoo 18
        
        Args:
            partner_id (int): ID du partenaire (client)
            amount (float): Montant du paiement
            folio_id (int, optional): ID du folio
            reservation_id (int, optional): ID de la réservation
            memo (str, optional): Note/mémo du paiement
            invoice_id (int, optional): ID de la facture à lettrer
            
        Returns:
            dict: Dictionnaire de valeurs pour créer un account.payment
            
        Raises:
            ValidationError: Si la configuration est incomplète
        """
        self.ensure_one()
        
        # Vérifications préalables
        if not self.journal_id:
            raise ValidationError(_(
                'Le mode de paiement "%s" n\'a pas de journal comptable configuré.\n'
                'Veuillez le configurer dans: Hôtel > Configuration > Modes de Paiement'
            ) % self.name)
        
        if not self.default_payment_method_line_id:
            raise ValidationError(_(
                'Le mode de paiement "%s" n\'a pas de méthode de paiement par défaut configurée.\n'
                'Veuillez la configurer dans: Hôtel > Configuration > Modes de Paiement'
            ) % self.name)
        
        # Construire les valeurs du paiement
        payment_vals = {
            # ✅ Champs obligatoires Odoo 18
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': partner_id,
            'amount': amount,
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.default_payment_method_line_id.id,
            
            # ✅ Référence et mémo
            'payment_reference': memo or f"Paiement hôtel - {self.name}",
            
            # ✅ Lien avec le module hôtel
            'hotel_payment_method_id': self.id,
        }
        
        # 🔥 CONFIGURATION COMPTABLE SPÉCIFIQUE
        # Pour les acomptes (pas de facture liée), utiliser le compte d'acompte
        if invoice_id is None and reservation_id:
            if self.advance_payment_account_id:
                payment_vals['destination_account_id'] = self.advance_payment_account_id.id
                _logger.info("Utilisation du compte d'acompte %s pour le paiement", self.advance_payment_account_id.code)
            else:
                # Chercher un compte d'acompte par défaut
                default_advance_account = self.env['account.account'].search([
                    ('account_type', '=', 'liability_current'),
                    ('name', 'ilike', 'acompte'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                if default_advance_account:
                    payment_vals['destination_account_id'] = default_advance_account.id
                    _logger.info("Utilisation du compte d'acompte par défaut %s", default_advance_account.code)
                else:
                    _logger.warning("Aucun compte d'acompte configuré, utilisation du compte client standard")
        
        # 🔥 LIER À LA FACTURE SI FOURNIE (crucial pour le lettrage)
        if invoice_id:
            payment_vals['reconciled_invoice_ids'] = [(6, 0, [invoice_id])]
        
        # Ajouter les relations hôtelières
        if folio_id:
            payment_vals['folio_id'] = folio_id
        if reservation_id:
            payment_vals['reservation_id'] = reservation_id
            
        return payment_vals

    # ============================================================================
    # ✅ MÉTHODE SIMPLIFIÉE : CRÉER ET VALIDER UN PAIEMENT
    # ============================================================================
    
    def create_and_post_payment(self, partner_id, amount, folio_id=None, 
                               reservation_id=None, memo=None, invoice_id=None,
                               mobile_phone=None, mobile_reference=None,
                               check_number=None, check_date=None, check_bank=None):
        """
        ✅ Crée un paiement complet et le valide immédiatement
        
        Returns:
            account.payment: Le paiement créé et validé
        """
        self.ensure_one()
        
        # Obtenir les valeurs de base
        payment_vals = self.get_payment_vals(
            partner_id=partner_id,
            amount=amount,
            folio_id=folio_id,
            reservation_id=reservation_id,
            memo=memo,
            invoice_id=invoice_id
        )
        
        # Ajouter les informations spécifiques selon le type
        if self.payment_type == 'mobile_money':
            payment_vals.update({
                'mobile_phone': mobile_phone,
                'mobile_reference': mobile_reference,
            })
        elif self.payment_type == 'check':
            payment_vals.update({
                'check_number': check_number,
                'check_date': check_date,
                'check_bank': check_bank,
            })
        
        # Créer le paiement
        payment = self.env['account.payment'].create(payment_vals)
        
        # ✅ VALIDER IMMÉDIATEMENT (crée les écritures comptables)
        payment.action_post()
        
        return payment

    # ============================================================================
    # ✅ ACTIONS INTERFACE
    # ============================================================================
    
    def action_view_payments(self):
        """Voir tous les paiements utilisant ce mode"""
        self.ensure_one()
        return {
            'name': _('Paiements - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('hotel_payment_method_id', '=', self.id)],
            'context': {'default_hotel_payment_method_id': self.id},
        }

    def action_configure_journal(self):
        """Ouvrir la configuration du journal"""
        self.ensure_one()
        if not self.journal_id:
            raise ValidationError(_('Aucun journal n\'est configuré pour ce mode de paiement.'))
        
        return {
            'name': _('Configuration Journal'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal',
            'res_id': self.journal_id.id,
            'view_mode': 'form',
            'target': 'current',
        }