# -*- coding: utf-8 -*-

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

    # ============= CORRECTION PRINCIPALE =============
    # Journal comptable (OBLIGATOIRE pour Odoo 18)
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal Comptable',
        required=False,  # ✅ Rendu optionnel pour l'installation
        domain=[('type', 'in', ['cash', 'bank'])],
        help='Journal comptable où les paiements seront enregistrés'
    )
    
    # Méthode de paiement Odoo (OBLIGATOIRE pour Odoo 18)
    inbound_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        string='Méthodes de Paiement Disponibles',
        compute='_compute_payment_method_line_ids',
        store=False
    )
    
    default_payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Méthode de Paiement par Défaut',
        domain="[('id', 'in', inbound_payment_method_line_ids)]",
        help='Méthode de paiement utilisée par défaut pour ce mode'
    )
    
    # Comptes comptables
    account_debit_id = fields.Many2one(
        'account.account',
        string='Compte de Débit',
        help='Compte comptable pour débiter lors du paiement (ex: Caisse, Banque)',
        domain=[('deprecated', '=', False)]
    )
    account_credit_id = fields.Many2one(
        'account.account',
        string='Compte de Crédit',
        help='Compte comptable pour créditer lors du paiement (généralement Client)',
        domain=[('deprecated', '=', False)]
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

    @api.depends('journal_id')
    def _compute_payment_method_line_ids(self):
        """Calcule les méthodes de paiement disponibles selon le journal"""
        for method in self:
            if method.journal_id:
                method.inbound_payment_method_line_ids = method.journal_id._get_available_payment_method_lines('inbound')
            else:
                method.inbound_payment_method_line_ids = False

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Réinitialise la méthode de paiement par défaut si le journal change"""
        self.default_payment_method_line_id = False
        if self.journal_id:
            available_methods = self.journal_id._get_available_payment_method_lines('inbound')
            if available_methods:
                self.default_payment_method_line_id = available_methods[0]

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
        """Vérifier que la configuration comptable est complète"""
        for method in self:
            if method.journal_id:
                if not method.account_debit_id or not method.account_credit_id:
                    raise ValidationError(_(
                        'Pour le mode de paiement "%s", vous devez configurer les comptes '
                        'de débit et crédit si un journal est lié.'
                    ) % method.name)

    def _compute_usage_count(self):
        for method in self:
            method.usage_count = self.env['account.payment'].search_count([
                ('hotel_payment_method_id', '=', method.id)
            ])

    @api.onchange('mobile_provider')
    def _onchange_mobile_provider(self):
        if self.mobile_provider:
            self.payment_type = 'mobile_money'
            self.require_phone = True
    
    # ============= NOUVELLE MÉTHODE =============
    def get_payment_vals(self, partner_id, amount, folio_id=None, reservation_id=None, memo=None):
        """
        Génère les valeurs correctes pour créer un account.payment
        Compatible Odoo 18
        """
        self.ensure_one()
        
        if not self.journal_id:
            raise ValidationError(_(
                'Le mode de paiement "%s" n\'a pas de journal comptable configuré.'
            ) % self.name)
        
        if not self.default_payment_method_line_id:
            raise ValidationError(_(
                'Le mode de paiement "%s" n\'a pas de méthode de paiement par défaut configurée.'
            ) % self.name)
        
        partner = self.env['res.partner'].browse(partner_id)
        
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': partner_id,
            'amount': amount,
            'date': fields.Date.today(),
            'journal_id': self.journal_id.id,  # ✅ OBLIGATOIRE
            'payment_method_line_id': self.default_payment_method_line_id.id,  # ✅ OBLIGATOIRE Odoo 18
            'hotel_payment_method_id': self.id,
            'memo': memo or f"Paiement hôtel",
        }
        
        # Ajouter les relations hôtelières
        if folio_id:
            payment_vals['folio_id'] = folio_id
        if reservation_id:
            payment_vals['reservation_id'] = reservation_id
            
        return payment_vals