# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


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

    # Journal comptable
    journal_id = fields.Many2one('account.journal', string='Journal Comptable',
                                 domain=[('type', 'in', ['cash', 'bank'])])

    # Disponibilité
    active = fields.Boolean(string='Actif', default=True)

    # Statistiques
    usage_count = fields.Integer(string='Nombre d\'Utilisations',
                                 compute='_compute_usage_count')

    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Le code du mode de paiement doit être unique.'),
    ]

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