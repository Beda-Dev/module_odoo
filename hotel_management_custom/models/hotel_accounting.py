# -*- coding: utf-8 -*-
# Fichier: hotel_management_custom/models/hotel_accounting.py

import logging
from odoo import models, fields, api, _
import traceback

_logger = logging.getLogger(__name__)
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
    
    # Paiements effectués au check-out
    checkout_payment_ids = fields.One2many(
        'account.payment',
        'folio_id',
        string='Paiements Check-out',
        readonly=True,
        domain=[('payment_category', '=', 'checkout')]
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
        """Créer et valider une facture avec gestion des paiements"""
        self.ensure_one()
        _logger.info("[HOTEL_ACCOUNTING] DÉBUT CRÉATION FACTURE - Folio: %s, Client: %s", self.name, self.partner_id.name)

        # Vérifier s'il existe une facture en brouillon
        existing_draft = self.invoice_ids.filtered(lambda i: i.state == 'draft')
        if existing_draft:
            invoice = existing_draft[0]
            _logger.info("[HOTEL_ACCOUNTING] Facture brouillon trouvée: %s", invoice.name)
        else:
            # Créer la facture
            invoice = self._create_invoice()
            _logger.info("[HOTEL_ACCOUNTING] Nouvelle facture créée: %s", invoice.name)
        
        # Valider la facture
        self._validate_invoice(invoice)
        
        # Gérer les paiements existants
        _logger.info("[HOTEL_ACCOUNTING] TRAITEMENT DES PAIEMENTS EXISTANTS - Acomptes: %d, Paiements check-out: %d", 
                    len(self.reservation_id.advance_payment_ids), len(self.checkout_payment_ids))
        self._process_existing_payments(invoice)
        
        # Mettre à jour les relations
        if invoice.id not in self.invoice_ids.ids:
            self.invoice_ids = [(4, invoice.id)]
        if invoice.id not in self.accounting_move_ids.ids:
            self.accounting_move_ids = [(4, invoice.id)]
        
        _logger.info("[HOTEL_ACCOUNTING] FIN CRÉATION FACTURE - Facture: %s, État: %s", invoice.name, invoice.state)
        return {
            'name': _('Facture'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def _create_invoice(self):
        """Création de la facture avec les lignes appropriées"""
        # Obtenir le compte de revenu par défaut
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
            account_id = product.property_account_income_id.id if (product and product.property_account_income_id) else default_income_account.id
            
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
            account_id = default_income_account.id
            if service_line.service_id.product_id and service_line.service_id.product_id.property_account_income_id:
                account_id = service_line.service_id.product_id.property_account_income_id.id
            
            invoice_lines.append((0, 0, {
                'name': service_line.service_id.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,
                'product_id': service_line.service_id.product_id.id if service_line.service_id.product_id else False,
                'account_id': account_id,
                'tax_ids': [(6, 0, service_line.service_id.tax_ids.ids)],
            }))

        # Créer la facture
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'ref': self.name,
            'narration': _('Folio: %s\nChambre: %s\nDu %s au %s') % (
                self.name, self.room_id.name, self.checkin_date, self.checkout_date,
            ),
        })

    def _validate_invoice(self, invoice):
        """Validation de la facture avec gestion des erreurs"""
        if invoice.state == 'posted':
            return True
            
        try:
            invoice.with_context(
                check_move_validity=False,
                force_company=self.company_id.id
            ).action_post()
            self.message_post(body=_('Facture validée: %s') % invoice.name)
            return True
        except Exception as e:
            _logger.error("Erreur validation facture %s: %s", invoice.name, str(e))
            self.message_post(
                body=_('Erreur de validation: %s') % str(e),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            raise UserError(_("Impossible de valider la facture: %s") % str(e))

    def _process_existing_payments(self, invoice):
        """Traite les paiements existants (acomptes et paiements au check-out)"""
        _logger.info("[HOTEL_ACCOUNTING] DÉBUT TRAITEMENT PAIEMENTS - Facture: %s", invoice.name)
        
        # Rapprocher les acomptes
        if self.reservation_id.advance_payment_ids:
            _logger.info("[HOTEL_ACCOUNTING] Traitement de %d acomptes pour la réservation %s", 
                        len(self.reservation_id.advance_payment_ids), self.reservation_id.name)
            self._reconcile_advance_payments(invoice)
        else:
            _logger.info("[HOTEL_ACCOUNTING] Aucun acompte à traiter pour la réservation %s", self.reservation_id.name)
        
        # Rapprocher les paiements au check-out
        if hasattr(self, 'checkout_payment_ids') and self.checkout_payment_ids:
            _logger.info("[HOTEL_ACCOUNTING] Traitement de %d paiements check-out pour le folio %s", 
                        len(self.checkout_payment_ids), self.name)
            self._reconcile_checkout_payments(invoice)
        else:
            _logger.info("[HOTEL_ACCOUNTING] Aucun paiement check-out à traiter pour le folio %s", self.name)
        
        _logger.info("[HOTEL_ACCOUNTING] FIN TRAITEMENT PAIEMENTS - Facture: %s", invoice.name)

    def _reconcile_advance_payments(self, invoice):
        """Rapproche les paiements anticipés avec la facture"""
        _logger.info("[HOTEL_ACCOUNTING] DÉBUT LETTRAGE ACOMPTES - Facture: %s", invoice.name)
        
        for payment in self.reservation_id.advance_payment_ids:
            _logger.info("[HOTEL_ACCOUNTING] Tentative lettrage acompte: %s (État: %s, Montant: %s)", 
                        payment.name, payment.state, payment.amount)
            self._reconcile_single_payment(payment, invoice, _('Acompte'))
            
        _logger.info("[HOTEL_ACCOUNTING] FIN LETTRAGE ACOMPTES - Facture: %s", invoice.name)

    def _reconcile_checkout_payments(self, invoice):
        """Rapproche les paiements effectués au check-out avec la facture"""
        _logger.info("[HOTEL_ACCOUNTING] DÉBUT LETTRAGE PAIEMENTS CHECK-OUT - Facture: %s", invoice.name)
        
        for payment in self.checkout_payment_ids:
            _logger.info("[HOTEL_ACCOUNTING] Tentative lettrage paiement check-out: %s (État: %s, Montant: %s)", 
                        payment.name, payment.state, payment.amount)
            self._reconcile_single_payment(payment, invoice, _('Paiement check-out'))
            
        _logger.info("[HOTEL_ACCOUNTING] FIN LETTRAGE PAIEMENTS CHECK-OUT - Facture: %s", invoice.name)

    def _reconcile_single_payment(self, payment, invoice, payment_type):
        """Rapproche un paiement unique avec la facture"""
        _logger.info("[HOTEL_ACCOUNTING] DÉBUT LETTRAGE INDIVIDUEL - Type: %s, Paiement: %s, Facture: %s", 
                    payment_type, payment.name, invoice.name)
        
        # Vérifications initiales
        if payment.state not in ['draft', 'paid']:
            _logger.warning("[HOTEL_ACCOUNTING] ÉCHEC LETTRAGE - Le paiement %s n'est pas dans un état valide (état actuel: %s)", 
                           payment.name, payment.state)
            return False
        
        # Si le paiement est en draft, le valider d'abord
        if payment.state == 'draft':
            _logger.info("[HOTEL_ACCOUNTING] Validation du paiement %s (état: draft)", payment.name)
            try:
                payment.action_post()
                _logger.info("[HOTEL_ACCOUNTING] Paiement %s validé avec succès", payment.name)
            except Exception as e:
                _logger.error("[HOTEL_ACCOUNTING] Impossible de valider le paiement %s: %s", payment.name, str(e))
                return False
        
        # Vérifier si le paiement est déjà rapproché
        if payment.is_reconciled:
            _logger.warning("[HOTEL_ACCOUNTING] ÉCHEC LETTRAGE - Le paiement %s est déjà rapproché", 
                           payment.name)
            return False
        
        _logger.info("[HOTEL_ACCOUNTING] Vérifications initiales OK pour le paiement %s", payment.name)
        
        try:
            # Récupération des lignes à rapprocher
            invoice_lines = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            payment_lines = payment.line_ids.filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            )
            
            _logger.info("[HOTEL_ACCOUNTING] Lignes de facture à rapprocher: %s", 
                        [(l.id, l.account_id.code, l.account_id.name, l.balance) for l in invoice_lines])
            _logger.info("[HOTEL_ACCOUNTING] Lignes de paiement à rapprocher: %s", 
                        [(l.id, l.account_id.code, l.account_id.name, l.balance) for l in payment_lines])
            
            if not invoice_lines or not payment_lines:
                _logger.error("[HOTEL_ACCOUNTING] ÉCHEC LETTRAGE - Impossible de trouver des lignes à rapprocher (facture: %s lignes, paiement: %s lignes)", 
                             len(invoice_lines), len(payment_lines))
                return False
            
            # Rapprochement
            _logger.info("[HOTEL_ACCOUNTING] Lancement du rapprochement pour %s lignes au total", 
                        len(invoice_lines + payment_lines))
            (invoice_lines + payment_lines).reconcile()
            
            _logger.info("[HOTEL_ACCOUNTING] LETTRAGE RÉUSSI - Type: %s, Paiement: %s, Facture: %s", 
                        payment_type, payment.name, invoice.name)
            
            self.message_post(
                body=_('%s rapproché: %s') % (payment_type, payment.name)
            )
            return True
            
        except Exception as e:
            _logger.error("""
[HOTEL_ACCOUNTING] ERREUR CRITIQUE LORS DU RAPPROCHEMENT:
- Type: %s
- Paiement: %s (ID: %s)
- Facture: %s (ID: %s)
- Erreur: %s
- Traceback: %s
            """, 
            payment_type, 
            payment.name, 
            payment.id,
            invoice.name, 
            invoice.id,
            str(e), 
            traceback.format_exc())
            
            self.message_post(
                body=_('Erreur de rapprochement %s %s: %s') % (payment_type, payment.name, str(e)),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            return False
        
        finally:
            _logger.info("[HOTEL_ACCOUNTING] FIN LETTRAGE INDIVIDUEL - Type: %s, Paiement: %s", 
                        payment_type, payment.name)

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

    # ============================================================================
    # ✅ CHAMPS RELATIONS HÔTEL
    # ============================================================================
    
    folio_id = fields.Many2one(
        'hotel.folio', 
        string='Folio', 
        ondelete='set null',
        index=True
    )
    reservation_id = fields.Many2one(
        'hotel.reservation', 
        string='Réservation', 
        ondelete='set null',
        index=True
    )
    hotel_payment_method_id = fields.Many2one(
        'hotel.payment.method', 
        string='Mode de Paiement Hôtel',
        index=True
    )

    # ✅ INFORMATIONS MOBILE MONEY
    mobile_phone = fields.Char(string='Numéro de Téléphone')
    mobile_reference = fields.Char(string='Référence Transaction')

    # ✅ INFORMATIONS CHÈQUE
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')

    # ✅ TYPE DE PAIEMENT HÔTELIER
    is_advance_payment = fields.Boolean(
        string='Paiement Anticipé',
        default=False,
        help='Indique si c\'est un paiement anticipé sur réservation (acompte ou paiement total)',
        index=True
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

    # ============================================================================
    # ✅ ONCHANGE - AUTOMATISATIONS
    # ============================================================================
    
    @api.onchange('hotel_payment_method_id')
    def _onchange_hotel_payment_method_id(self):
        """Auto-remplir le journal et la méthode quand on change le mode de paiement hôtel"""
        if self.hotel_payment_method_id:
            if self.hotel_payment_method_id.journal_id:
                self.journal_id = self.hotel_payment_method_id.journal_id
            
            if self.hotel_payment_method_id.default_payment_method_line_id:
                self.payment_method_line_id = self.hotel_payment_method_id.default_payment_method_line_id

    # ============================================================================
    # ✅ SURCHARGE action_post - MISE À JOUR AUTOMATIQUE
    # ============================================================================
    
    def action_post(self):
        """
        ✅ Poster le paiement avec mise à jour automatique du folio et de la réservation
        """
        result = super(AccountPayment, self).action_post()

        for payment in self:
            # ✅ METTRE À JOUR LE FOLIO
            if payment.folio_id:
                payment.folio_id._compute_amounts()
                
                # Message sur le folio
                payment.folio_id.message_post(
                    body=_('💰 Paiement de %.2f enregistré via %s') % (
                        payment.amount,
                        payment.hotel_payment_method_id.name if payment.hotel_payment_method_id else 'N/A'
                    ),
                    subject='Paiement Reçu'
                )

            # ✅ METTRE À JOUR LA RÉSERVATION (paiements anticipés)
            if payment.reservation_id and payment.is_advance_payment:
                # Marquer la date d'acompte si c'est le premier
                if not payment.reservation_id.deposit_date:
                    payment.reservation_id.deposit_date = fields.Date.today()
                
                # Recalculer les montants
                payment.reservation_id._compute_deposit_paid()
                payment.reservation_id._compute_amount_paid()
                
                # Message sur la réservation
                payment.reservation_id.message_post(
                    body=_('💰 Paiement anticipé de %.2f reçu') % payment.amount,
                    subject='Paiement Anticipé'
                )

        return result

    # ============================================================================
    # ✅ ACTIONS INTERFACE
    # ============================================================================
    
    def action_print_receipt(self):
        """Imprimer le reçu de paiement"""
        self.ensure_one()
        # Vous pouvez créer un rapport spécifique pour le reçu
        return self.env.ref('hotel_management_custom.action_report_payment_receipt').report_action(self)
    
    def action_view_related_folio(self):
        """Voir le folio lié"""
        self.ensure_one()
        if not self.folio_id:
            raise UserError(_('Ce paiement n\'est pas lié à un folio.'))
        
        return {
            'name': _('Folio'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.folio',
            'res_id': self.folio_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_related_reservation(self):
        """Voir la réservation liée"""
        self.ensure_one()
        if not self.reservation_id:
            raise UserError(_('Ce paiement n\'est pas lié à une réservation.'))
        
        return {
            'name': _('Réservation'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'res_id': self.reservation_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

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
                    COALESCE(SUM(CASE WHEN ap.state = 'paid' THEN ap.amount ELSE 0 END), 0) as amount_paid,
                    COALESCE(SUM(CASE WHEN ap.state = 'paid' AND ap.is_advance_payment = true THEN ap.amount ELSE 0 END), 0) as advance_paid,
                    COALESCE(r.total_amount, 0) - COALESCE(SUM(CASE WHEN ap.state = 'paid' THEN ap.amount ELSE 0 END), 0) as amount_due,
                    COALESCE(COUNT(DISTINCT inv.id), 0) as invoice_count,
                    COALESCE(COUNT(DISTINCT CASE WHEN ap.state = 'paid' THEN ap.id END), 0) as payment_count,
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