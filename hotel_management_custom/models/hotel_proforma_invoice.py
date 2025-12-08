# -*- coding: utf-8 -*-
# Fichier: hotel_management_custom/models/hotel_proforma_invoice.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class HotelProformaInvoice(models.Model):
    """Facture Pro-Forma (Devis) pour réservations hôtelières"""
    _name = 'hotel.proforma.invoice'
    _description = 'Facture Pro-Forma / Devis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_proforma desc, id desc'

    # Identification
    name = fields.Char(
        string='Numéro',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )

    # Relations
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Réservation',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True
    )

    # Dates
    date_proforma = fields.Date(
        string='Date du Devis',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    validity_date = fields.Date(
        string='Valable jusqu\'au',
        compute='_compute_validity_date',
        store=True,
        readonly=False,
        tracking=True,
        help='Date limite de validité du devis'
    )
    validity_days = fields.Integer(
        string='Validité (jours)',
        default=15,
        help='Nombre de jours de validité du devis'
    )

    # Informations réservation
    room_id = fields.Many2one(
        related='reservation_id.room_id',
        string='Chambre',
        store=True
    )
    checkin_date = fields.Date(
        related='reservation_id.checkin_date',
        string='Date d\'Arrivée',
        store=True
    )
    checkout_date = fields.Date(
        related='reservation_id.checkout_date',
        string='Date de Départ',
        store=True
    )
    duration_days = fields.Integer(
        related='reservation_id.duration_days',
        string='Nombre de Nuits',
        store=True
    )

    # Montants
    total_amount = fields.Float(
        string='Montant Total',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )
    room_total = fields.Float(
        string='Total Hébergement',
        compute='_compute_amounts',
        store=True
    )
    service_total = fields.Float(
        string='Total Services',
        compute='_compute_amounts',
        store=True
    )

    # Gestion acompte (conditionnel)
    deposit_required = fields.Boolean(
        string='Acompte Requis',
        compute='_compute_deposit_required',
        store=True,
        help='Déterminé par les paramètres du module'
    )
    deposit_percentage = fields.Float(
        string='Pourcentage Acompte (%)',
        compute='_compute_deposit_percentage',
        store=True
    )
    deposit_amount = fields.Float(
        string='Montant Acompte',
        compute='_compute_deposit_amount',
        store=True
    )
    balance_amount = fields.Float(
        string='Solde à Régler',
        compute='_compute_deposit_amount',
        store=True
    )

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('accepted', 'Accepté'),
        ('expired', 'Expiré'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', required=True, tracking=True)

    # Informations complémentaires
    notes = fields.Text(string='Notes')
    terms_conditions = fields.Text(
        string='Conditions Générales',
        default=lambda self: self._default_terms_conditions()
    )

    # Société et devise
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Devise'
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Générer le numéro de séquence à la création"""
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.proforma.invoice') or _('Nouveau')
        return super().create(vals_list)

    @api.depends('date_proforma', 'validity_days')
    def _compute_validity_date(self):
        """Calculer la date de validité"""
        for proforma in self:
            if proforma.date_proforma and proforma.validity_days:
                proforma.validity_date = proforma.date_proforma + timedelta(days=proforma.validity_days)
            else:
                proforma.validity_date = False

    @api.depends('reservation_id')
    def _compute_deposit_required(self):
        """Vérifier si l'acompte est requis selon les paramètres"""
        deposit_required = self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_required', default='False'
        ) == 'True'
        
        for proforma in self:
            proforma.deposit_required = deposit_required

    @api.depends('reservation_id')
    def _compute_deposit_percentage(self):
        """Récupérer le pourcentage d'acompte depuis les paramètres"""
        deposit_percentage = float(self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_percentage', default='0'
        ))
        
        for proforma in self:
            proforma.deposit_percentage = deposit_percentage

    @api.depends('reservation_id.total_amount', 'reservation_id.service_line_ids.price_subtotal')
    def _compute_amounts(self):
        """Calculer les montants depuis la réservation"""
        for proforma in self:
            if proforma.reservation_id:
                # Total hébergement (chambres)
                room_total = 0.0
                if proforma.reservation_id.room_id and proforma.checkin_date and proforma.checkout_date:
                    current_date = proforma.checkin_date
                    while current_date < proforma.checkout_date:
                        room_total += proforma.reservation_id.room_id.get_rate_for_date(current_date)
                        current_date += timedelta(days=1)
                
                # Total services
                service_total = sum(proforma.reservation_id.service_line_ids.mapped('price_subtotal'))
                
                proforma.room_total = room_total
                proforma.service_total = service_total
                proforma.total_amount = room_total + service_total
            else:
                proforma.room_total = 0.0
                proforma.service_total = 0.0
                proforma.total_amount = 0.0

    @api.depends('total_amount', 'deposit_required', 'deposit_percentage')
    def _compute_deposit_amount(self):
        """Calculer le montant de l'acompte si requis"""
        for proforma in self:
            if proforma.deposit_required and proforma.deposit_percentage > 0:
                proforma.deposit_amount = (proforma.total_amount * proforma.deposit_percentage) / 100
                proforma.balance_amount = proforma.total_amount - proforma.deposit_amount
            else:
                proforma.deposit_amount = 0.0
                proforma.balance_amount = proforma.total_amount

    def _default_terms_conditions(self):
        """Conditions générales par défaut"""
        return _(
            "• Le présent devis est valable jusqu'à la date indiquée.\n"
            "• La réservation sera confirmée après réception de l'acompte (si requis).\n"
            "• Les tarifs sont exprimés en devise locale et incluent toutes les taxes.\n"
            "• Toute annulation doit être notifiée par écrit.\n"
            "• Les conditions d'annulation sont disponibles sur demande."
        )

    def action_send_by_email(self):
        """Envoyer le devis par email"""
        self.ensure_one()
        
        # Marquer comme envoyé
        if self.state == 'draft':
            self.state = 'sent'
        
        # Préparer le template email
        template = self.env.ref('hotel_management_custom.email_template_proforma_invoice', raise_if_not_found=False)
        
        return {
            'name': _('Envoyer le Devis'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'hotel.proforma.invoice',
                'default_res_id': self.id,
                'default_use_template': bool(template),
                'default_template_id': template.id if template else False,
                'default_partner_ids': [(6, 0, [self.partner_id.id])],
                'force_email': True,
            },
        }

    def action_mark_accepted(self):
        """Marquer le devis comme accepté"""
        for proforma in self:
            if proforma.state in ['draft', 'sent']:
                proforma.state = 'accepted'
                proforma.message_post(body=_('Devis accepté par le client'))

    def action_cancel(self):
        """Annuler le devis"""
        for proforma in self:
            if proforma.state not in ['accepted']:
                proforma.state = 'cancelled'
                proforma.message_post(body=_('Devis annulé'))

    def action_set_to_draft(self):
        """Remettre en brouillon"""
        for proforma in self:
            if proforma.state in ['sent', 'cancelled']:
                proforma.state = 'draft'

    def action_print_proforma(self):
        """Imprimer le devis"""
        self.ensure_one()
        return self.env.ref('hotel_management_custom.action_report_proforma_invoice').report_action(self)

    def _cron_check_expired_proformas(self):
        """Tâche planifiée : Marquer les devis expirés"""
        today = fields.Date.today()
        
        expired_proformas = self.search([
            ('state', 'in', ['draft', 'sent']),
            ('validity_date', '<', today),
        ])
        
        for proforma in expired_proformas:
            proforma.state = 'expired'
            proforma.message_post(body=_('Devis expiré automatiquement'))
