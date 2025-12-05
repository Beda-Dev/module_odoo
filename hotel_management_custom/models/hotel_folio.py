# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Notes de séjour client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Référence de séjour client', required=True, copy=False, readonly=True,
                      default=lambda self: _('Nouveau'))
    
    # Client
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', string='Téléphone', readonly=True)
    partner_email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    
    # Réservation
    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', 
                                    required=True, readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Chambre', 
                             store=True, readonly=True)
    
    # Dates
    checkin_date = fields.Date(related='reservation_id.checkin_date', string='Check-in', 
                              store=True, readonly=True)
    checkout_date = fields.Date(related='reservation_id.checkout_date', string='Check-out', 
                               store=True, readonly=True)
    
    # Services et montants
    service_line_ids = fields.One2many('hotel.service.line', 'folio_id', string='Services')
    
    room_total = fields.Float(string='Total Chambres', compute='_compute_amounts', store=True)
    service_total = fields.Float(string='Total Services', compute='_compute_amounts', store=True)
    amount_total = fields.Float(string='Montant Total', compute='_compute_amounts', store=True)
    amount_paid = fields.Float(string='Montant Payé', compute='_compute_amounts', store=True)
    amount_due = fields.Float(string='Solde Dû', compute='_compute_amounts', store=True)
    
    # Paiements
    payment_ids = fields.One2many('account.payment', 'folio_id', string='Paiements')
    
    # Factures
    invoice_ids = fields.Many2many('account.move', 'folio_invoice_rel', 
                                   'folio_id', 'invoice_id', string='Factures')
    invoice_count = fields.Integer(string='Nombre de Factures', compute='_compute_invoice_count')
    
    # État
    state = fields.Selection([
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
    ], string='État', default='open', tracking=True)
    
    # Notes
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', string='Société', 
                                default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.folio') or _('Nouveau')
        return super(HotelFolio, self).create(vals_list)
    
    @api.depends('reservation_id.total_amount', 'service_line_ids.price_subtotal', 'payment_ids.state', 'payment_ids.amount', 'reservation_id.advance_payment_ids.state', 'reservation_id.advance_payment_ids.amount')
    def _compute_amounts(self):
        for folio in self:
            # Total chambre depuis la réservation
            folio.room_total = folio.reservation_id.total_amount - sum(
                folio.reservation_id.service_line_ids.mapped('price_subtotal')
            )
            
            # Total services
            folio.service_total = sum(folio.service_line_ids.mapped('price_subtotal'))
            
            # Total général
            folio.amount_total = folio.room_total + folio.service_total
            
            # Montant payé (paiements folio + acomptes réservation)
            folio_payments = sum(
                folio.payment_ids.filtered(lambda p: p.state == 'paid').mapped('amount')
            )
            reservation_deposits = sum(
                folio.reservation_id.advance_payment_ids.filtered(lambda p: p.state == 'paid').mapped('amount')
            )
            folio.amount_paid = folio_payments + reservation_deposits
            
            # Solde dû
            folio.amount_due = folio.amount_total - folio.amount_paid
    
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for folio in self:
            folio.invoice_count = len(folio.invoice_ids)
    
    def action_add_service(self):
        """Ajouter un service"""
        self.ensure_one()
        return {
            'name': _('Ajouter un Service'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.service.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folio_id': self.id,
                'default_reservation_id': self.reservation_id.id,
            },
        }
    
        
    def action_view_invoices(self):
        """Voir les factures"""
        self.ensure_one()
        return {
            'name': _('Factures'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }
    
    def action_close_folio(self):
        """Fermer le folio"""
        self.ensure_one()
        
        if self.amount_due > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('Il reste un solde dû de %s. Veuillez effectuer le paiement avant de fermer le folio.') % self.amount_due,
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        self.write({'state': 'closed'})
        self.message_post(body=_('Folio fermé'))
        
        return True
