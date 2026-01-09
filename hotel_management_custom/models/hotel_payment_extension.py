# -*- coding: utf-8 -*-
# Extension du modèle account.payment pour les paiements hôteliers

import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


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

    def action_post(self):
        """Surcharge pour ajouter des logs lors de la validation des paiements"""
        _logger.info("[HOTEL_PAYMENT_EXTENSION] DÉBUT VALIDATION PAIEMENT - Paiement: %s, Montant: %s, Catégorie: %s", 
                    self.name, self.amount, self.payment_category)
        
        # Logs supplémentaires pour le débogage
        _logger.info("[HOTEL_PAYMENT_EXTENSION] Détails paiement:")
        _logger.info("  - Partenaire: %s", self.partner_id.name if self.partner_id else 'N/A')
        _logger.info("  - Journal: %s", self.journal_id.name if self.journal_id else 'N/A')
        _logger.info("  - État: %s", self.state)
        _logger.info("  - Réservation: %s", self.reservation_id.name if self.reservation_id else 'N/A')
        _logger.info("  - Folio: %s", self.folio_id.name if hasattr(self, 'folio_id') and self.folio_id else 'N/A')
        
        try:
            result = super(AccountPayment, self).action_post()
            _logger.info("[HOTEL_PAYMENT_EXTENSION] VALIDATION PAIEMENT RÉUSSIE - Paiement: %s", self.name)
            return result
        except Exception as e:
            _logger.error("[HOTEL_PAYMENT_EXTENSION] ERREUR VALIDATION PAIEMENT - Paiement: %s, Erreur: %s", 
                         self.name, str(e))
            raise
