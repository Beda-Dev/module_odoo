# -*- coding: utf-8 -*-
# Fichier: hotel_management_custom/models/hotel_accounting.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class HotelPaymentMethod(models.Model):
    """Extension du modèle mode de paiement avec comptes comptables"""
    _inherit = 'hotel.payment.method'

    # Comptes comptables liés
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


class HotelReservation(models.Model):
    """Extension réservation avec gestion des acomptes"""
    _inherit = 'hotel.reservation'

    # Gestion de l'acompte
    deposit_amount = fields.Float(
        string='Montant Acompte Demandé',
        default=0.0,
        help='Montant de l\'acompte que le client doit payer avant le séjour'
    )
    deposit_paid = fields.Float(
        string='Acompte Déjà Payé',
        compute='_compute_deposit_paid',
        store=True,
        help='Montant de l\'acompte déjà reçu'
    )
    deposit_date = fields.Date(
        string='Date Paiement Acompte',
        readonly=True
    )
    
    # Paiements d'avance liés
    advance_payment_ids = fields.One2many(
        'account.payment',
        'reservation_id',
        string='Paiements d\'Avance',
        readonly=True,
        domain=[('is_advance_payment', '=', True)]
    )

    # Écritures comptables
    accounting_move_ids = fields.Many2many(
        'account.move',
        'reservation_accounting_move_rel',
        'reservation_id',
        'move_id',
        string='Écritures Comptables',
        readonly=True
    )

    @api.depends('advance_payment_ids.amount', 'advance_payment_ids.state')
    def _compute_deposit_paid(self):
        """Calculer l'acompte déjà payé"""
        for reservation in self:
            reservation.deposit_paid = sum(
                reservation.advance_payment_ids.filtered(
                    lambda p: p.state == 'paid'
                ).mapped('amount')
            )

    def action_request_deposit(self):
        """Action pour demander un acompte"""
        self.ensure_one()

        if self.state not in ['draft', 'confirmed']:
            raise UserError(
                _('Vous pouvez demander un acompte que sur une réservation brouillon ou confirmée.')
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
                'default_amount': self.deposit_amount,
                'default_payment_type': 'inbound',
                'default_is_advance_payment': True,
            },
        }

    def action_confirm(self):
        """Confirmer la réservation avec création du folio et écritures comptables"""
        result = super().action_confirm()

        for reservation in self:
            if reservation.folio_id and reservation.hotel_payment_method_id:
                reservation._create_reservation_accounting_entry()

        return result

    def _create_reservation_accounting_entry(self):
        """Créer les écritures comptables de réservation"""
        self.ensure_one()

        if not self.hotel_payment_method_id.journal_id:
            return

        try:
            journal = self.hotel_payment_method_id.journal_id
            lines = []

            # Compte client (débit)
            client_account = self.partner_id.property_account_receivable_id
            lines.append((0, 0, {
                'account_id': client_account.id,
                'debit': self.total_amount,
                'credit': 0.0,
                'name': _('Réservation - Client %s') % self.partner_id.name,
            }))

            # Compte revenue (crédit)
            revenue_account_id = int(
                self.env['ir.config_parameter'].sudo().get_param(
                    'hotel.account_revenue_id', '0'
                )
            )
            if not revenue_account_id:
                # Utiliser le compte de revenu par défaut du système
                revenue_account = self.env['account.account'].search([
                    ('account_type', '=', 'income'),
                    ('company_ids', 'in', [self.env.company.id]),
                    ('deprecated', '=', False)
                ], limit=1)
                revenue_account_id = revenue_account.id if revenue_account else 0

            lines.append((0, 0, {
                'account_id': revenue_account_id,
                'debit': 0.0,
                'credit': self.total_amount,
                'name': _('Revenue - Réservation %s') % self.name,
            }))

            # Créer l'écriture
            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': _('RES-%s') % self.name,
                'line_ids': lines,
            })

            self.accounting_move_ids = [(4, move.id)]
            move.action_post()

        except Exception as e:
            self.message_post(
                body=_('Erreur lors de la création de l\'écriture comptable: %s') % str(e),
                message_type='notification'
            )


class HotelFolio(models.Model):
    """Extension folio avec facturation et comptabilité"""
    _inherit = 'hotel.folio'

    # Statut de facturation
    invoice_status = fields.Selection([
        ('not_invoiced', 'Non Facturé'),
        ('partial', 'Partiellement Facturé'),
        ('invoiced', 'Facturé'),
    ], string='Statut Facturation', compute='_compute_invoice_status', store=True)

    # Gestion du dépôt
    deposit_credited = fields.Boolean(
        string='Dépôt Utilisé pour Régler',
        default=False,
        help='Le dépôt a été crédité contre le montant dû'
    )

    # Écritures comptables du folio
    accounting_move_ids = fields.Many2many(
        'account.move',
        'folio_accounting_move_rel',
        'folio_id',
        'move_id',
        string='Écritures Comptables',
        readonly=True
    )

    @api.depends('invoice_ids.state')
    def _compute_invoice_status(self):
        """Calculer le statut de facturation"""
        for folio in self:
            if not folio.invoice_ids:
                folio.invoice_status = 'not_invoiced'
            else:
                posted_count = len(folio.invoice_ids.filtered(lambda i: i.state == 'posted'))
                total_count = len(folio.invoice_ids)
                
                if posted_count == total_count:
                    folio.invoice_status = 'invoiced'
                elif posted_count > 0:
                    folio.invoice_status = 'partial'
                else:
                    folio.invoice_status = 'not_invoiced'

    def action_create_invoice(self):
        """Créer une facture client avec comptabilisation"""
        self.ensure_one()

        # Vérifier s'il existe une facture en brouillon
        existing_draft = self.invoice_ids.filtered(lambda i: i.state == 'draft')
        if existing_draft:
            return {
                'name': _('Facture'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': existing_draft[0].id,
            }

        invoice_lines = []

        # Ligne hébergement
        if self.room_total > 0:
            invoice_lines.append((0, 0, {
                'name': _('Hébergement - Chambre %s (%d nuits)') % (
                    self.room_id.name,
                    self.reservation_id.duration_days
                ),
                'quantity': self.reservation_id.duration_days,
                'price_unit': self.room_total / self.reservation_id.duration_days 
                    if self.reservation_id.duration_days else self.room_total,
            }))

        # Lignes services
        for service_line in self.service_line_ids:
            invoice_lines.append((0, 0, {
                'name': service_line.service_id.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,
            }))

        # Créer la facture
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'ref': self.name,
            'narration': _('Folio: %s\nChambre: %s\nDu %s au %s') % (
                self.name,
                self.room_id.name,
                self.checkin_date,
                self.checkout_date,
            ),
        })

        self.invoice_ids = [(4, invoice.id)]
        self.accounting_move_ids = [(4, invoice.id)]

        return {
            'name': _('Facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def action_close_folio(self):
        """Fermer le folio avec validation comptable"""
        self.ensure_one()

        # Vérifier solde
        if self.amount_due > 0.01:  # Tolérance de 0.01
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Attention'),
                    'message': _('Il reste un solde dû de %s. Veuillez effectuer le paiement.') % self.amount_due,
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Vérifier facture
        if not self.invoice_ids.filtered(lambda i: i.state == 'posted'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur'),
                    'message': _('Veuillez valider la facture avant de fermer.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }

        self.write({'state': 'closed'})
        self.message_post(body=_('Folio fermé et comptabilisé'))

        return True

    def action_open_accounting_entries(self):
        """Afficher les écritures comptables liées"""
        self.ensure_one()
        return {
            'name': _('Écritures Comptables'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.accounting_move_ids.ids)],
        }


class AccountPayment(models.Model):
    """Extension des paiements pour l'hôtel"""
    _inherit = 'account.payment'

    # Relations hôtel
    folio_id = fields.Many2one('hotel.folio', string='Folio', ondelete='set null')
    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', ondelete='set null')
    hotel_payment_method_id = fields.Many2one('hotel.payment.method', string='Mode de Paiement Hôtel')

    # Infos mobiles money
    mobile_phone = fields.Char(string='Numéro de Téléphone')
    mobile_reference = fields.Char(string='Référence Transaction')

    # Infos chèque
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')

    # Type de paiement
    is_advance_payment = fields.Boolean(
        string='Paiement d\'Avance',
        default=False,
        help='Indique si c\'est un paiement d\'avance sur réservation'
    )

    @api.onchange('hotel_payment_method_id')
    def _onchange_hotel_payment_method_id(self):
        """Auto-remplir le journal quand on change le mode de paiement"""
        if self.hotel_payment_method_id and self.hotel_payment_method_id.journal_id:
            self.journal_id = self.hotel_payment_method_id.journal_id

    def action_post(self):
        """Poster le paiement et mettre à jour les montants"""
        result = super().action_post()

        for payment in self:
            # Mettre à jour folio
            if payment.folio_id:
                payment.folio_id._compute_amounts()

            # Marquer date acompte si c'est un paiement d'avance
            if payment.reservation_id and payment.is_advance_payment:
                payment.reservation_id.deposit_date = fields.Date.today()
                payment.reservation_id._compute_deposit_paid()

        return result


class HotelAccountingReport(models.Model):
    """Rapport comptable hôtel"""
    _name = 'hotel.accounting.report'
    _description = 'Rapport Comptable Hôtel'
    _auto = False
    _rec_name = 'folio_id'

    folio_id = fields.Many2one('hotel.folio', string='Folio', readonly=True)
    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Client', readonly=True)
    room_id = fields.Many2one('hotel.room', string='Chambre', readonly=True)

    checkin_date = fields.Date(string='Check-in', readonly=True)
    checkout_date = fields.Date(string='Check-out', readonly=True)

    room_total = fields.Float(string='Total Chambres', readonly=True)
    service_total = fields.Float(string='Total Services', readonly=True)
    amount_total = fields.Float(string='Montant Total', readonly=True)
    amount_paid = fields.Float(string='Montant Payé', readonly=True)
    amount_due = fields.Float(string='Solde Dû', readonly=True)

    invoice_count = fields.Integer(string='Factures', readonly=True)
    payment_count = fields.Integer(string='Paiements', readonly=True)

    state = fields.Selection([
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
    ], string='État', readonly=True)

    def init(self):
        """Créer la vue SQL"""
        from odoo import tools
        tools.drop_view_if_exists(self.env.cr, self._table)

        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    f.id,
                    f.id as folio_id,
                    r.id as reservation_id,
                    f.partner_id,
                    r.room_id,
                    r.checkin_date,
                    r.checkout_date,
                    COALESCE(r.total_amount, 0) - COALESCE(SUM(CASE WHEN sl.id IS NOT NULL THEN sl.price_subtotal ELSE 0 END), 0) as room_total,
                    COALESCE(SUM(CASE WHEN sl.id IS NOT NULL THEN sl.price_subtotal ELSE 0 END), 0) as service_total,
                    COALESCE(r.total_amount, 0) as amount_total,
                    COALESCE(SUM(CASE WHEN ap.state = 'paid' THEN ap.amount ELSE 0 END), 0) as amount_paid,
                    COALESCE(r.total_amount, 0) - COALESCE(SUM(CASE WHEN ap.state = 'paid' THEN ap.amount ELSE 0 END), 0) as amount_due,
                    COALESCE(COUNT(DISTINCT inv.id), 0) as invoice_count,
                    COALESCE(COUNT(DISTINCT CASE WHEN ap.state = 'paid' THEN ap.id END), 0) as payment_count,
                    f.state
                FROM hotel_folio f
                LEFT JOIN hotel_reservation r ON f.reservation_id = r.id
                LEFT JOIN hotel_service_line sl ON f.id = sl.folio_id
                LEFT JOIN account_payment ap ON f.id = ap.folio_id
                LEFT JOIN folio_invoice_rel fir ON f.id = fir.folio_id
                LEFT JOIN account_move inv ON fir.invoice_id = inv.id
                GROUP BY f.id, r.id, f.partner_id, r.room_id, r.checkin_date, r.checkout_date, r.total_amount, f.state
            )
        """ % self._table

        self.env.cr.execute(query)