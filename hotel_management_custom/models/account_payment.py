# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Lien avec le folio
    folio_id = fields.Many2one('hotel.folio', string='Notes de séjour client', ondelete='set null')
    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', ondelete='set null')

    # Mode de paiement hôtel
    hotel_payment_method_id = fields.Many2one('hotel.payment.method', string='Mode de Paiement Hôtel')

    # Informations pour mobile money
    mobile_phone = fields.Char(string='Numéro de Téléphone')
    mobile_reference = fields.Char(string='Référence Transaction')

    # Informations pour chèque
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')

    @api.onchange('hotel_payment_method_id')
    def _onchange_hotel_payment_method_id(self):
        if self.hotel_payment_method_id and self.hotel_payment_method_id.journal_id:
            self.journal_id = self.hotel_payment_method_id.journal_id