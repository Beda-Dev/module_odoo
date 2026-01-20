# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Réservation d\'Hôtel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'checkin_date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))

    # Client
    partner_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', string='Téléphone')
    partner_email = fields.Char(related='partner_id.email', string='Email')

    # Chambre
    room_id = fields.Many2one('hotel.room', string='Chambre', required=True, tracking=True)
    room_type_id = fields.Many2one(related='room_id.room_type_id', string='Type de Chambre', store=True)

    # Dates
    checkin_date = fields.Date(string='Date d\'Arrivée', required=True, tracking=True)
    checkout_date = fields.Date(string='Date de Départ', required=True, tracking=True)
    duration_days = fields.Integer(string='Nombre de Nuits', compute='_compute_duration', store=True)

    # Dates effectives
    actual_checkin_date = fields.Datetime(string='Check-in Effectif', readonly=True)
    actual_checkout_date = fields.Datetime(string='Check-out Effectif', readonly=True)

    # Personnes
    adults = fields.Integer(string='Adultes', default=1, required=True)
    children = fields.Integer(string='Enfants', default=0)
    total_persons = fields.Integer(string='Total Personnes', compute='_compute_total_persons', store=True)

    # Tarifs
    total_amount = fields.Float(string='Montant Total', compute='_compute_total_amount',
                                store=True, tracking=True)
    amount_paid = fields.Float(string='Montant Payé', compute='_compute_amount_paid', store=True)
    amount_due = fields.Float(string='Montant Dû', compute='_compute_amount_due', store=True)

    # Mode de paiement
    hotel_payment_method_id = fields.Many2one('hotel.payment.method', string='Mode de Paiement')

    # Gestion des acomptes
    require_deposit = fields.Boolean(string='Acompte Requis', default=False)
    deposit_amount = fields.Float(string="Montant de l'acompte", tracking=True)
    deposit_percentage = fields.Float(
        string='Pourcentage Acompte (%)',
        compute='_compute_deposit_percentage',
        store=True,
        readonly=False,
        help='Pourcentage du montant total à demander en acompte'
    )
    deposit_paid = fields.Float(string='Acompte Payé', compute='_compute_deposit_paid', store=True)
    deposit_date = fields.Date(string='Date Paiement Acompte', readonly=True)
    
    allow_full_prepayment = fields.Boolean(string='Paiement Total Autorisé', default=False)
    is_fully_paid = fields.Boolean(string='Totalement Payé', compute='_compute_payment_status', store=True)
    
    # Paiements anticipés (incluant acomptes)
    advance_payment_ids = fields.One2many(
        'account.payment',
        'reservation_id',
        string='Paiements Anticipés',
        readonly=True,
        domain=[('is_advance_payment', '=', True)]
    )
    
    # Statut paiement anticipé
    advance_payment_status = fields.Selection([
        ('none', 'Aucun Paiement'),
        ('partial', 'Paiement Partiel'),
        ('deposit_paid', 'Acompte Payé'),
        ('full_paid', 'Totalement Payé'),
    ], string='Statut Paiement Anticipé', compute='_compute_advance_payment_status', store=True)
    
    # Écritures comptables liées
    accounting_move_ids = fields.Many2many(
        'account.move',
        'reservation_accounting_move_rel',
        'reservation_id',
        'move_id',
        string='Écritures Comptables',
        readonly=True
    )

    # Relations
    folio_id = fields.Many2one('hotel.folio', string='Notes de séjour client', readonly=True)
    service_line_ids = fields.One2many('hotel.service.line', 'reservation_id',
                                       string='Services Consommés')
    invoice_ids = fields.Many2many('account.move', string='Factures', readonly=True, copy=False)
    proforma_invoice_ids = fields.One2many(
        'hotel.proforma.invoice',
        'reservation_id',
        string='Devis / Pro-Forma',
        readonly=True
    )
    proforma_count = fields.Integer(
        string='Nombre de Devis',
        compute='_compute_proforma_count'
    )

    @api.depends('proforma_invoice_ids')
    def _compute_proforma_count(self):
        """Compter le nombre de devis"""
        for reservation in self:
            reservation.proforma_count = len(reservation.proforma_invoice_ids)

    def action_generate_proforma(self):
        """Générer une facture pro-forma (devis)"""
        self.ensure_one()
        
        if self.state not in ['draft', 'confirmed']:
            raise UserError(_('Vous ne pouvez générer un devis que pour une réservation en brouillon ou confirmée.'))
        
        # Créer le devis
        proforma = self.env['hotel.proforma.invoice'].create({
            'reservation_id': self.id,
            'partner_id': self.partner_id.id,
        })
        
        # Ouvrir le formulaire du devis
        return {
            'name': _('Devis / Facture Pro-Forma'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.proforma.invoice',
            'view_mode': 'form',
            'res_id': proforma.id,
            'target': 'current',
        }

    def action_view_proforma(self):
        """Voir les devis liés à la réservation"""
        self.ensure_one()
        
        action = {
            'name': _('Devis / Factures Pro-Forma'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.proforma.invoice',
            'domain': [('reservation_id', '=', self.id)],
        }
        
        if len(self.proforma_invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.proforma_invoice_ids[0].id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
            })
        
        return action

    def action_record_advance_payment(self):
        """Ouvrir le wizard de paiement anticipé"""
        self.ensure_one()
        
        return {
            'name': _('Enregistrer un Paiement'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.advance.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_payment_type': 'deposit' if self.require_deposit else 'partial',
            }
        }

    def action_view_invoices(self):
        """Ouvre la vue des factures liées à la réservation"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(self.invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.invoice_ids.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'views': [(False, 'list'), (False, 'form')],
            })
        return action

    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('checkin', 'Check-in'),
        ('checkout', 'Check-out'),
        ('cancelled', 'Annulée'),
    ], string='État', default='draft', required=True, tracking=True)

    # Informations supplémentaires
    notes = fields.Text(string='Notes')
    special_requests = fields.Text(string='Demandes Spéciales')

    # Canal de réservation
    booking_channel = fields.Selection([
        ('direct', 'Direct'),
        ('phone', 'Téléphone'),
        ('email', 'Email'),
        ('online', 'En Ligne'),
    ], string='Canal de Réservation', default='direct')

    # Statut de paiement
    payment_status = fields.Selection([
        ('unpaid', 'Non Payé'),
        ('partial', 'Partiellement Payé'),
        ('paid', 'Payé'),
    ], string='Statut Paiement', compute='_compute_payment_status', store=True)

    company_id = fields.Many2one('res.company', string='Société',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Devise')

    color = fields.Integer(string='Couleur')

    _sql_constraints = [
        ('check_dates', 'CHECK(checkout_date > checkin_date)',
         'La date de départ doit être postérieure à la date d\'arrivée.'),
        ('check_adults', 'CHECK(adults > 0)',
         'Il doit y avoir au moins un adulte.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Récupération des paramètres de configuration
        icp = self.env['ir.config_parameter'].sudo()
        # Récupération et conversion sécurisée des paramètres
        deposit_required = str(icp.get_param('hotel.deposit_required', 'False')).lower() == 'true'
        deposit_percentage = float(icp.get_param('hotel.deposit_percentage', '0') or '0')
        allow_full_prepayment = str(icp.get_param('hotel.allow_full_prepayment', 'False')).lower() == 'true'
        
        # Traitement de chaque ensemble de valeurs
        for vals in vals_list:
            # Génération du numéro de réservation
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.reservation') or _('Nouveau')
            
            # Application des paramètres
            if deposit_required:
                vals['require_deposit'] = True
                # Le deposit_amount sera calculé automatiquement via _compute_deposit_amount
            
            if allow_full_prepayment:
                vals['allow_full_prepayment'] = True
        
        # Appel à la méthode parente avec la liste complète des valeurs
        return super().create(vals_list)

    @api.depends('total_amount', 'state')
    def _compute_deposit_percentage(self):
        """Calculer le pourcentage d'acompte par défaut depuis la configuration"""
        deposit_percentage = float(self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_percentage', default='0'
        ))
        for reservation in self:
            if not reservation.deposit_percentage and reservation.require_deposit:
                reservation.deposit_percentage = deposit_percentage

    @api.depends('total_amount', 'deposit_percentage', 'require_deposit')
    def _compute_deposit_amount(self):
        """Calculer l'acompte basé sur le pourcentage si acompte requis"""
        for reservation in self:
            if reservation.require_deposit and reservation.deposit_percentage > 0:
                reservation.deposit_amount = (reservation.total_amount * reservation.deposit_percentage) / 100
            else:
                reservation.deposit_amount = 0.0

    @api.depends('advance_payment_ids.amount', 'advance_payment_ids.state')
    def _compute_deposit_paid(self):
        """Calculer l'acompte déjà payé"""
        for reservation in self:
            paid_amount = 0
            for payment in reservation.advance_payment_ids:
                if payment.state in ['in_process', 'paid']:
                    paid_amount += payment.amount
            reservation.deposit_paid = paid_amount

    @api.depends('deposit_paid', 'deposit_amount', 'total_amount', 'require_deposit')
    def _compute_advance_payment_status(self):
        """Calculer le statut des paiements anticipés"""
        for reservation in self:
            if not reservation.require_deposit:
                reservation.advance_payment_status = 'none'
            elif reservation.deposit_paid <= 0:
                reservation.advance_payment_status = 'none'
            elif reservation.deposit_paid >= reservation.total_amount:
                reservation.advance_payment_status = 'full_paid'
            elif reservation.deposit_paid >= reservation.deposit_amount and reservation.deposit_amount > 0:
                reservation.advance_payment_status = 'deposit_paid'
            else:
                reservation.advance_payment_status = 'partial'

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration(self):
        for reservation in self:
            if reservation.checkin_date and reservation.checkout_date:
                delta = reservation.checkout_date - reservation.checkin_date
                reservation.duration_days = delta.days
            else:
                reservation.duration_days = 0

    @api.depends('adults', 'children')
    def _compute_total_persons(self):
        for reservation in self:
            reservation.total_persons = reservation.adults + reservation.children

    @api.depends('room_id', 'checkin_date', 'checkout_date', 'service_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for reservation in self:
            total = 0.0

            # Calculer le montant des nuitées
            if reservation.room_id and reservation.checkin_date and reservation.checkout_date:
                current_date = reservation.checkin_date
                while current_date < reservation.checkout_date:
                    total += reservation.room_id.get_rate_for_date(current_date)
                    current_date += timedelta(days=1)

            # Ajouter les services
            total += sum(reservation.service_line_ids.mapped('price_subtotal'))

            reservation.total_amount = total

    @api.depends('folio_id.payment_ids.amount', 'folio_id.payment_ids.state', 
                 'advance_payment_ids.amount', 'advance_payment_ids.state')
    def _compute_amount_paid(self):
        """Calculer le montant total payé (folio + acomptes)"""
        for reservation in self:
            folio_payments = 0
            advance_payments = 0
            
            # Paiements sur le folio (après check-in)
            if reservation.folio_id:
                folio_payments = sum(
                    payment.amount 
                    for payment in reservation.folio_id.payment_ids 
                    if payment.state in ['in_process', 'paid']
                )
            
            # Paiements anticipés (avant check-in)
            advance_payments = sum(
                payment.amount 
                for payment in reservation.advance_payment_ids 
                if payment.state in ['in_process', 'paid']
            )
            
            reservation.amount_paid = folio_payments + advance_payments

    @api.depends('total_amount', 'amount_paid')
    def _compute_amount_due(self):
        for reservation in self:
            reservation.amount_due = reservation.total_amount - reservation.amount_paid

    @api.depends('amount_paid', 'total_amount')
    def _compute_payment_status(self):
        for reservation in self:
            if reservation.amount_paid <= 0:
                reservation.payment_status = 'unpaid'
                reservation.is_fully_paid = False
            elif reservation.amount_paid >= reservation.total_amount:
                reservation.payment_status = 'paid'
                reservation.is_fully_paid = True
            else:
                reservation.payment_status = 'partial'
                reservation.is_fully_paid = False

    @api.constrains('room_id', 'checkin_date', 'checkout_date')
    def _check_room_availability(self):
        for reservation in self:
            if reservation.state not in ['cancelled'] and reservation.room_id:
                # Vérifier les chevauchements avec d'autres réservations
                overlapping = self.search([
                    ('id', '!=', reservation.id),
                    ('room_id', '=', reservation.room_id.id),
                    ('state', 'in', ['draft', 'confirmed', 'checkin']),
                    '|',
                    '&', ('checkin_date', '<=', reservation.checkin_date),
                    ('checkout_date', '>', reservation.checkin_date),
                    '&', ('checkin_date', '<', reservation.checkout_date),
                    ('checkout_date', '>=', reservation.checkout_date),
                ])

                if overlapping:
                    raise ValidationError(_(
                        'La chambre %s n\'est pas disponible pour ces dates.\n'
                        'Réservation en conflit: %s'
                    ) % (reservation.room_id.name, overlapping[0].name))

    @api.constrains('total_persons', 'room_id')
    def _check_capacity(self):
        for reservation in self:
            if reservation.room_id and reservation.total_persons > reservation.room_id.capacity:
                raise ValidationError(_(
                    'Le nombre de personnes (%d) dépasse la capacité de la chambre (%d).'
                ) % (reservation.total_persons, reservation.room_id.capacity))

    def action_request_deposit(self):
        """Action pour demander un acompte"""
        self.ensure_one()

        if self.state not in ['draft', 'confirmed']:
            raise UserError(
                _('Vous ne pouvez demander un acompte que sur une réservation brouillon ou confirmée.')
            )

        if not self.deposit_amount or self.deposit_amount <= 0:
            raise UserError(_('Veuillez définir un montant d\'acompte valide.'))

        return {
            'name': _('Paiement d\'Acompte - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.deposit_amount - self.deposit_paid,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_is_advance_payment': True,
            },
        }

    def action_register_advance_payment(self):
        """Action pour enregistrer un paiement anticipé (partiel ou total)"""
        self.ensure_one()

        if self.state not in ['draft', 'confirmed']:
            raise UserError(
                _('Vous ne pouvez enregistrer un paiement que sur une réservation brouillon ou confirmée.')
            )

        return {
            'name': _('Paiement Anticipé - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_amount': self.total_amount - self.amount_paid,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_is_advance_payment': True,
            },
        }

    def action_confirm(self):
        """Confirmer la réservation avec vérification de l'acompte si requis"""
        for reservation in self:
            # Vérifier si l'acompte est obligatoire
            if reservation.require_deposit and reservation.deposit_amount > 0:
                deposit_required_param = self.env['ir.config_parameter'].sudo().get_param(
                    'hotel.deposit_required', default='False'
                ) == 'True'
                
                if deposit_required_param and reservation.deposit_paid < reservation.deposit_amount:
                    raise UserError(_(
                        'Un acompte de %s est requis avant de confirmer la réservation. '
                        'Montant déjà payé : %s'
                    ) % (reservation.deposit_amount, reservation.deposit_paid))
        
            if reservation.state != 'draft':
                raise UserError(_('Seules les réservations en brouillon peuvent être confirmées.'))

            reservation.write({'state': 'confirmed'})
            reservation.room_id.write({'status': 'reserved'})

            reservation.message_post(body=_('Réservation confirmée'))

        return True

    def action_checkin(self):
        """Effectuer le check-in"""
        return {
            'name': _('Check-in'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id},
        }

    def action_checkout(self):
        """Effectuer le check-out"""
        return {
            'name': _('Check-out'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.checkout.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id},
        }

    def action_cancel(self):
        """Annuler la réservation"""
        for reservation in self:
            if reservation.state == 'checkout':
                raise UserError(_('Impossible d\'annuler une réservation après le check-out.'))

            reservation.write({'state': 'cancelled'})

            if reservation.room_id.status == 'reserved' and reservation.room_id.current_reservation_id == reservation:
                reservation.room_id.write({'status': 'available'})

            reservation.message_post(body=_('Réservation annulée'))

        return True

    def action_view_folio(self):
        """Voir le folio"""
        self.ensure_one()
        return {
            'name': _('Folio'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.folio',
            'view_mode': 'form',
            'res_id': self.folio_id.id,
        }

    def _cron_checkout_reminder(self):
        """Tâche planifiée: Rappels de check-out"""
        today = fields.Date.today()
        tomorrow = today + timedelta(days=1)

        # Trouver les réservations avec check-out demain
        upcoming_checkouts = self.search([
            ('state', '=', 'checkin'),
            ('checkout_date', '=', tomorrow),
        ])

        for reservation in upcoming_checkouts:
            # Créer une activité de rappel
            reservation.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=reservation.create_uid.id,
                summary=_('Rappel: Check-out demain'),
                note=_('La réservation %s (%s) a un check-out prévu pour demain (%s).') % (
                    reservation.name,
                    reservation.partner_id.name,
                    reservation.checkout_date
                ),
            )

        # Trouver les réservations avec check-out aujourd'hui
        today_checkouts = self.search([
            ('state', '=', 'checkin'),
            ('checkout_date', '=', today),
        ])

        for reservation in today_checkouts:
            # Envoyer une notification
            reservation.message_post(
                body=_('Rappel: Check-out prévu aujourd\'hui pour %s') % reservation.partner_id.name,
                message_type='notification',
            )