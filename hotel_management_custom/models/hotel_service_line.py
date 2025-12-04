# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelServiceLine(models.Model):
    _name = 'hotel.service.line'
    _description = 'Ligne de Service'
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', compute='_compute_name', store=True)

    # Relations
    folio_id = fields.Many2one('hotel.folio', string='Notes de séjour client',
                               compute='_compute_folio_id', store=True,
                               readonly=False, ondelete='cascade')
    reservation_id = fields.Many2one('hotel.reservation', string='Réservation',
                                     required=True, ondelete='cascade')
    service_id = fields.Many2one('hotel.service', string='Service', required=True)

    # Informations client et chambre
    partner_id = fields.Many2one(related='reservation_id.partner_id', string='Client',
                                 store=True, readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Chambre',
                              store=True, readonly=True)

    # Date et quantité
    date = fields.Datetime(string='Date/Heure', required=True, default=fields.Datetime.now)
    quantity = fields.Float(string='Quantité', required=True, default=1.0)

    # Prix
    price_unit = fields.Float(string='Prix Unitaire', required=True)
    price_subtotal = fields.Float(string='Sous-total', compute='_compute_price_subtotal',
                                  store=True)

    # Notes
    notes = fields.Text(string='Notes')

    # Mouvement de stock
    stock_move_id = fields.Many2one('stock.move', string='Mouvement de Stock', readonly=True)

    company_id = fields.Many2one('res.company', string='Société',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')

    @api.depends('reservation_id', 'reservation_id.folio_id')
    def _compute_folio_id(self):
        """Calculer automatiquement le folio_id depuis la réservation"""
        for line in self:
            if line.reservation_id and line.reservation_id.folio_id:
                line.folio_id = line.reservation_id.folio_id
            elif not line.folio_id and line.reservation_id:
                # Si la réservation n'a pas encore de folio, on attend
                line.folio_id = False

    @api.depends('service_id', 'quantity', 'date')
    def _compute_name(self):
        for line in self:
            if line.service_id:
                line.name = _('%s x%s') % (line.service_id.name, line.quantity)
            else:
                line.name = _('Nouveau Service')

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.price_unit = self.service_id.price

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('La quantité doit être supérieure à zéro.'))

    @api.model_create_multi
    def create(self, vals_list):
        """Crée les lignes de service et assurer que folio_id est défini"""
        for vals in vals_list:
            if 'reservation_id' in vals and not vals.get('folio_id'):
                reservation = self.env['hotel.reservation'].browse(vals['reservation_id'])
                if reservation.folio_id:
                    vals['folio_id'] = reservation.folio_id.id

        lines = super(HotelServiceLine, self).create(vals_list)

        # Si le service est lié à un produit, créer un mouvement de stock
        for line in lines:
            if line.service_id.product_id:
                line._create_stock_move()

        return lines

    def _create_stock_move(self):
        """Créer un mouvement de stock pour le service consommé"""
        self.ensure_one()

        if not self.service_id.product_id:
            return

        # Trouver l'emplacement source (stock) et destination (consommation)
        StockLocation = self.env['stock.location']
        location_src = StockLocation.search([('usage', '=', 'internal')], limit=1)
        location_dest = StockLocation.search([('usage', '=', 'customer')], limit=1)

        if not location_src or not location_dest:
            return

        origin = self.folio_id.name if self.folio_id else (
            self.reservation_id.name if self.reservation_id else 'Service'
        )

        move = self.env['stock.move'].create({
            'name': _('Consommation: %s') % self.service_id.name,
            'product_id': self.service_id.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.service_id.product_id.uom_id.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': origin,
        })

        move._action_confirm()
        move._action_assign()
        move._action_done()

        self.stock_move_id = move