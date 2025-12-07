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
    """Extension réservation avec gestion des acomptes et paiements anticipés"""
    _inherit = 'hotel.reservation'
    
    # Gestion de l'acompte
    deposit_amount = fields.Float(
        string='Montant Acompte Demandé',
        compute='_compute_deposit_amount',
        store=True,
        readonly=False,
        help='Montant de l\'acompte que le client doit payer'
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
    deposit_percentage = fields.Float(
        string='Pourcentage Acompte (%)',
        compute='_compute_deposit_percentage',
        store=True,
        readonly=False,
        help='Pourcentage du montant total à demander en acompte'
    )
    
    # Paiements anticipés (incluant acomptes)
    advance_payment_ids = fields.One2many(
        'account.payment',
        'reservation_id',
        string='Paiements Anticipés',
        readonly=True,
        domain=[('is_advance_payment', '=', True)]
    )
    
    # Écritures comptables liées
    accounting_move_ids = fields.Many2many(
        'account.move',
        'reservation_accounting_move_rel',
        'reservation_id',
        'move_id',
        string='Écritures Comptables',
        readonly=True
    )
    
    # Statut paiement anticipé
    advance_payment_status = fields.Selection([
        ('none', 'Aucun Paiement'),
        ('partial', 'Paiement Partiel'),
        ('deposit_paid', 'Acompte Payé'),
        ('full_paid', 'Totalement Payé'),
    ], string='Statut Paiement Anticipé', compute='_compute_advance_payment_status', store=True)

    @api.depends('total_amount', 'state')
    def _compute_deposit_percentage(self):
        """Calculer le pourcentage d'acompte par défaut depuis la configuration"""
        deposit_percentage = float(self.env['ir.config_parameter'].sudo().get_param(
            'hotel.deposit_percentage', default='0'
        ))
        for reservation in self:
            if not reservation.deposit_percentage and reservation.state == 'draft':
                reservation.deposit_percentage = deposit_percentage

    @api.depends('total_amount', 'deposit_percentage')
    def _compute_deposit_amount(self):
        """Calculer l'acompte basé sur le pourcentage"""
        for reservation in self:
            if reservation.deposit_percentage > 0:
                reservation.deposit_amount = (reservation.total_amount * reservation.deposit_percentage) / 100
            elif not reservation.deposit_amount:
                reservation.deposit_amount = 0.0

    @api.depends('advance_payment_ids.amount', 'advance_payment_ids.state')
    def _compute_deposit_paid(self):
        """Calculer l'acompte déjà payé"""
        for reservation in self:
            paid_amount = 0
            for payment in reservation.advance_payment_ids:
                if hasattr(payment, 'state') and payment.state == 'paid':
                    paid_amount += payment.amount
            reservation.deposit_paid = paid_amount

    @api.depends('deposit_paid', 'deposit_amount', 'total_amount')
    def _compute_advance_payment_status(self):
        """Calculer le statut des paiements anticipés"""
        for reservation in self:
            if reservation.deposit_paid <= 0:
                reservation.advance_payment_status = 'none'
            elif reservation.deposit_paid >= reservation.total_amount:
                reservation.advance_payment_status = 'full_paid'
            elif reservation.deposit_paid >= reservation.deposit_amount and reservation.deposit_amount > 0:
                reservation.advance_payment_status = 'deposit_paid'
            else:
                reservation.advance_payment_status = 'partial'

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
                'default_amount': self.total_amount - self.deposit_paid,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_is_advance_payment': True,
            },
        }

    def action_confirm(self):
        """Confirmer la réservation avec vérification de l'acompte si requis"""
        for reservation in self:
            # Vérifier si l'acompte est obligatoire
            deposit_required = self.env['ir.config_parameter'].sudo().get_param(
                'hotel.deposit_required', default='False'
            ) == 'True'
            
            if deposit_required and reservation.deposit_amount > 0:
                if reservation.deposit_paid < reservation.deposit_amount:
                    raise UserError(_(
                        'Un acompte de %s est requis avant de confirmer la réservation. '
                        'Montant déjà payé : %s'
                    ) % (reservation.deposit_amount, reservation.deposit_paid))
        
        return super(HotelReservation, self).action_confirm()


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
        string='Acompte Utilisé',
        default=False,
        help='Les paiements anticipés ont été appliqués au folio'
    )

    accounting_move_ids = fields.Many2many(
        'account.move',
        'folio_accounting_move_rel',
        'folio_id',
        'move_id',
        string='Écritures Comptables',
        readonly=True,
        help='Écritures comptables liées à ce folio'
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

        # CORRECTION: Obtenir le compte de revenu par défaut sans filtrer par company_id
        default_income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
        ], limit=1)
        
        if not default_income_account:
            raise UserError(_(
                'Aucun compte de revenu trouvé. Veuillez configurer un compte de type "Revenu" '
                'dans votre plan comptable.'
            ))

        invoice_lines = []

        # Ligne hébergement
        if self.room_total > 0:
            product = self.env['product.product'].search([
                ('name', 'ilike', 'hébergement'),
                ('type', '=', 'service')
            ], limit=1)
            
            if not product:
                product = self.env['product.product'].search([
                    ('type', '=', 'service')
                ], limit=1)
            
            # Déterminer le compte à utiliser
            account_id = False
            if product and product.property_account_income_id:
                account_id = product.property_account_income_id.id
            else:
                account_id = default_income_account.id
            
            invoice_lines.append((0, 0, {
                'name': _('Hébergement - Chambre %s (%d nuits)') % (
                    self.room_id.name,
                    self.reservation_id.duration_days
                ),
                'quantity': self.reservation_id.duration_days,
                'price_unit': self.room_total / self.reservation_id.duration_days 
                    if self.reservation_id.duration_days else self.room_total,
                'product_id': product.id if product else False,
                'account_id': account_id,
            }))

        # Lignes services
        for service_line in self.service_line_ids:
            # Déterminer le compte à utiliser
            account_id = False
            if service_line.service_id.product_id and service_line.service_id.product_id.property_account_income_id:
                account_id = service_line.service_id.product_id.property_account_income_id.id
            else:
                account_id = default_income_account.id
            
            invoice_lines.append((0, 0, {
                'name': service_line.service_id.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,
                'product_id': service_line.service_id.product_id.id if service_line.service_id.product_id else False,
                'account_id': account_id,
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

        # Marquer les acomptes comme crédités
        if self.reservation_id.advance_payment_ids and not self.deposit_credited:
            self.deposit_credited = True

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
            'view_mode': 'list,form',
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
        string='Paiement Anticipé',
        default=False,
        help='Indique si c\'est un paiement anticipé sur réservation (acompte ou paiement total)'
    )

    @api.onchange('hotel_payment_method_id')
    def _onchange_hotel_payment_method_id(self):
        """Auto-remplir le journal quand on change le mode de paiement"""
        if self.hotel_payment_method_id and self.hotel_payment_method_id.journal_id:
            self.journal_id = self.hotel_payment_method_id.journal_id

    def action_post(self):
        """Poster le paiement avec validation et mise à jour"""
        result = super().action_post()

        for payment in self:
            # Mettre à jour le folio
            if payment.folio_id:
                payment.folio_id._compute_amounts()
                # Créer automatiquement la facture si totalement payé
                if payment.folio_id.amount_due <= 0 and not payment.folio_id.invoice_ids.filtered(lambda i: i.state == 'posted'):
                    payment.folio_id.action_create_invoice()

            # Marquer date acompte si c'est un paiement d'avance
            if payment.reservation_id and payment.is_advance_payment:
                if not payment.reservation_id.deposit_date:
                    payment.reservation_id.deposit_date = fields.Date.today()
                payment.reservation_id._compute_deposit_paid()

        return result

    def action_print_receipt(self):
        """Imprimer le reçu de paiement"""
        self.ensure_one()
        return self.env.ref('hotel_management_custom.action_report_payment_receipt').report_action(self)


class ResConfigSettings(models.TransientModel):
    """Configuration des paramètres hôtel"""
    _inherit = 'res.config.settings'

    # Configuration acomptes
    hotel_deposit_required = fields.Boolean(
        string='Acompte Obligatoire',
        config_parameter='hotel.deposit_required',
        help='Si activé, un acompte sera obligatoire avant de confirmer une réservation'
    )
    hotel_deposit_percentage = fields.Float(
        string='Pourcentage Acompte (%)',
        config_parameter='hotel.deposit_percentage',
        help='Pourcentage du montant total à demander en acompte par défaut'
    )
    hotel_allow_full_prepayment = fields.Boolean(
        string='Autoriser Paiement Total Anticipé',
        default=True,
        config_parameter='hotel.allow_full_prepayment',
        help='Permet aux clients de payer la totalité avant leur arrivée'
    )


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
    advance_paid = fields.Float(string='Paiements Anticipés', readonly=True)
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
                    COALESCE(SUM(CASE WHEN ap.state IN ('posted', 'reconciled') THEN ap.amount ELSE 0 END), 0) as amount_paid,
                    COALESCE(SUM(CASE WHEN ap.state IN ('posted', 'reconciled') AND ap.is_advance_payment = true THEN ap.amount ELSE 0 END), 0) as advance_paid,
                    COALESCE(r.total_amount, 0) - COALESCE(SUM(CASE WHEN ap.state IN ('posted', 'reconciled') THEN ap.amount ELSE 0 END), 0) as amount_due,
                    COALESCE(COUNT(DISTINCT inv.id), 0) as invoice_count,
                    COALESCE(COUNT(DISTINCT CASE WHEN ap.state IN ('posted', 'reconciled') THEN ap.id END), 0) as payment_count,
                    f.state
                FROM hotel_folio f
                LEFT JOIN hotel_reservation r ON f.reservation_id = r.id
                LEFT JOIN hotel_service_line sl ON f.id = sl.folio_id
                LEFT JOIN account_payment ap ON (f.id = ap.folio_id OR r.id = ap.reservation_id)
                LEFT JOIN folio_invoice_rel fir ON f.id = fir.folio_id
                LEFT JOIN account_move inv ON fir.invoice_id = inv.id
                GROUP BY f.id, r.id, f.partner_id, r.room_id, r.checkin_date, r.checkout_date, r.total_amount, f.state
            )
        """ % self._table

        self.env.cr.execute(query)