# -*- coding: utf-8 -*-
# Extension du modèle account.payment pour les paiements hôteliers

from odoo import models, fields


class AccountPayment(models.Model):
    """Extension du modèle account.payment pour les paiements hôteliers"""
    _inherit = 'account.payment'
    
    # Lien avec la réservation
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Réservation',
        ondelete='cascade',
        index=True
    )
    
    # Type de paiement hôtelier
    is_advance_payment = fields.Boolean(
        string='Paiement Anticipé',
        default=False,
        help='Cocher si c\'est un paiement avant le check-in'
    )
    
    payment_category = fields.Selection([
        ('deposit', 'Acompte'),
        ('partial', 'Paiement Partiel'),
        ('full', 'Paiement Total'),
        ('checkout', 'Paiement au Check-out'),
        ('refund', 'Remboursement'),
    ], string='Catégorie de Paiement')
    
    # Lien avec le devis
    proforma_invoice_id = fields.Many2one(
        'hotel.proforma.invoice',
        string='Devis Lié'
    )
