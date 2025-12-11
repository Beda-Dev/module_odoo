# -*- coding: utf-8 -*-
# hotel_management_custom/wizard/hotel_checkout_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelCheckoutWizard(models.TransientModel):
    _name = 'hotel.checkout.wizard'
    _description = 'Assistant Check-out'

    reservation_id = fields.Many2one('hotel.reservation', string='Réservation', 
                                     required=True, readonly=True)
    folio_id = fields.Many2one(related='reservation_id.folio_id', string='Folio', readonly=True)
    partner_id = fields.Many2one(related='reservation_id.partner_id', string='Client', readonly=True)
    room_id = fields.Many2one(related='reservation_id.room_id', string='Chambre', readonly=True)
    
    # Informations du check-out
    checkout_datetime = fields.Datetime(string='Date/Heure Check-out', 
                                        required=True, default=fields.Datetime.now)
    
    # Montants
    total_amount = fields.Float(related='folio_id.amount_total', string='Montant Total', readonly=True)
    amount_paid = fields.Float(related='folio_id.amount_paid', string='Montant Payé', readonly=True)
    amount_due = fields.Float(related='folio_id.amount_due', string='Solde Dû', readonly=True)
    
    # Paiement
    payment_required = fields.Boolean(string='Paiement Requis', 
                                     compute='_compute_payment_required')
    payment_method_id = fields.Many2one('hotel.payment.method', string='Mode de Paiement')
    payment_amount = fields.Float(string='Montant du Paiement')
    
    # Informations pour mobile money
    mobile_phone = fields.Char(string='Numéro de Téléphone')
    mobile_reference = fields.Char(string='Référence Transaction')
    
    # Informations pour chèque
    check_number = fields.Char(string='Numéro de Chèque')
    check_date = fields.Date(string='Date du Chèque')
    check_bank = fields.Char(string='Banque')
    
    # Vérifications
    room_inspection = fields.Selection([
        ('ok', 'Chambre OK'),
        ('damage', 'Dommages Constatés'),
        ('cleaning_needed', 'Nettoyage Approfondi Requis'),
    ], string='Inspection de la Chambre', default='ok')
    
    damage_description = fields.Text(string='Description des Dommages')
    damage_cost = fields.Float(string='Coût des Dommages')
    
    # Minibar et services
    minibar_check = fields.Boolean(string='Minibar Vérifié', default=False)
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Satisfaction client
    satisfaction_rating = fields.Selection([
        ('1', 'Très Insatisfait'),
        ('2', 'Insatisfait'),
        ('3', 'Neutre'),
        ('4', 'Satisfait'),
        ('5', 'Très Satisfait'),
    ], string='Satisfaction Client')
    
    @api.depends('amount_due')
    def _compute_payment_required(self):
        for wizard in self:
            wizard.payment_required = wizard.amount_due > 0
    
    @api.onchange('payment_method_id')
    def _onchange_payment_method(self):
        if self.payment_method_id:
            # Pré-remplir le montant avec le solde dû
            self.payment_amount = self.amount_due
    
    @api.onchange('damage_cost')
    def _onchange_damage_cost(self):
        if self.damage_cost > 0:
            # Ajouter le coût des dommages au montant du paiement
            self.payment_amount = self.amount_due + self.damage_cost

    # ============================================================================
    # ✅ MÉTHODE PRINCIPALE CORRIGÉE
    # ============================================================================
    def action_confirm_checkout(self):
        """
        ✅ Check-out avec création automatique : 
        Facture validée → Paiement lettré → Écritures comptables
        """
        self.ensure_one()
        
        total_to_pay = self.amount_due + self.damage_cost
        
        # Vérifier qu'un mode de paiement est sélectionné si montant dû
        if total_to_pay > 0 and not self.payment_method_id:
            raise UserError(_(
                'Il reste un solde de %s à payer. Veuillez sélectionner un mode de paiement.'
            ) % total_to_pay)
        
        # 1️⃣ AJOUTER LES DOMMAGES AVANT LA FACTURE
        if self.damage_cost > 0:
            self._add_damage_charge()
        
        # 2️⃣ CRÉER ET VALIDER LA FACTURE IMMÉDIATEMENT
        invoice = self._create_and_post_invoice()
        
        # 3️⃣ CRÉER LE PAIEMENT ET LE LETTRER AVEC LA FACTURE
        payment = None
        if self.payment_method_id and self.payment_amount > 0:
            payment = self._create_and_reconcile_payment(invoice)
        
        # 4️⃣ FINALISER LE CHECK-OUT
        self._finalize_checkout()
        
        # 5️⃣ RETOURNER LA FACTURE (pas le folio)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facture Client'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'form_view_initial_mode': 'readonly',
            }
        }

    # ============================================================================
    # ✅ CRÉATION ET VALIDATION DE LA FACTURE
    # ============================================================================
    def _create_and_post_invoice(self):
        """
        Crée la facture client et la valide immédiatement
        Retourne: account.move (facture validée)
        """
        self.ensure_one()
        
        # Vérifier si une facture en brouillon existe déjà
        existing_invoice = self.folio_id.invoice_ids.filtered(lambda i: i.state == 'draft')
        if existing_invoice:
            invoice = existing_invoice[0]
        else:
            invoice = self._build_invoice()
        
        # ✅ VALIDER LA FACTURE IMMÉDIATEMENT
        if invoice.state == 'draft':
            invoice.action_post()
            
            self.folio_id.message_post(
                body=_('📄 Facture %s créée et validée automatiquement au check-out.') % invoice.name,
                subject='Facture Validée'
            )
        
        return invoice

    def _build_invoice(self):
        """Construit la facture avec toutes les lignes"""
        self.ensure_one()
        
        # Récupérer le compte de revenu par défaut
        income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            # Pas de filtre company_id nécessaire
        ], limit=1)
        
        if not income_account:
            raise UserError(_(
                'Aucun compte de revenu configuré.\n'
                'Veuillez créer un compte de type "Revenu" dans votre plan comptable.\n'
                'Comptabilité > Configuration > Plan Comptable'
            ))
        
        invoice_lines = []
        
        # ✅ LIGNE HÉBERGEMENT
        if self.folio_id.room_total > 0:
            price_per_night = (self.folio_id.room_total / self.reservation_id.duration_days 
                              if self.reservation_id.duration_days else self.folio_id.room_total)
            
            invoice_lines.append((0, 0, {
                'name': _('Hébergement - Chambre %s (%d nuit(s))') % (
                    self.room_id.name,
                    self.reservation_id.duration_days
                ),
                'quantity': self.reservation_id.duration_days,
                'price_unit': price_per_night,
                'account_id': income_account.id,
            }))
        
        # ✅ LIGNES SERVICES
        for service_line in self.folio_id.service_line_ids:
            account_id = income_account.id
            
            # Utiliser le compte du produit si disponible
            if service_line.service_id.product_id and \
               service_line.service_id.product_id.property_account_income_id:
                account_id = service_line.service_id.product_id.property_account_income_id.id
            
            invoice_lines.append((0, 0, {
                'name': service_line.service_id.name,
                'quantity': service_line.quantity,
                'price_unit': service_line.price_unit,
                'product_id': service_line.service_id.product_id.id if service_line.service_id.product_id else False,
                'account_id': account_id,
            }))
        
        # ✅ CRÉER LA FACTURE
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'ref': self.folio_id.name,
            'narration': _('Folio: %s\nChambre: %s\nDu %s au %s') % (
                self.folio_id.name,
                self.room_id.name,
                self.reservation_id.checkin_date,
                self.reservation_id.checkout_date,
            ),
        })
        
        # Lier la facture au folio
        self.folio_id.invoice_ids = [(4, invoice.id)]
        self.folio_id.accounting_move_ids = [(4, invoice.id)]
        
        return invoice

    # ============================================================================
    # ✅ CRÉATION DU PAIEMENT ET LETTRAGE
    # ============================================================================
    def _create_and_reconcile_payment(self, invoice):
        """
        Crée le paiement, le valide et le lettre avec la facture
        Retourne: account.payment (paiement validé et lettré)
        """
        self.ensure_one()
        
        # Vérifications préalables
        if not self.payment_method_id.journal_id:
            raise UserError(_(
                'Le mode de paiement "%s" n\'a pas de journal configuré.\n'
                'Veuillez configurer un journal dans:\n'
                'Hôtel > Configuration > Modes de Paiement'
            ) % self.payment_method_id.name)
        
        if not self.payment_method_id.default_payment_method_line_id:
            raise UserError(_(
                'Le mode de paiement "%s" n\'a pas de méthode de paiement par défaut.\n'
                'Veuillez la configurer dans:\n'
                'Hôtel > Configuration > Modes de Paiement'
            ) % self.payment_method_id.name)
        
        # Préparer les valeurs du paiement
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.payment_amount,
            'date': fields.Date.today(),
            'journal_id': self.payment_method_id.journal_id.id,
            'payment_method_line_id': self.payment_method_id.default_payment_method_line_id.id,
            'payment_reference': f"Check-out {self.folio_id.name}",
            'hotel_payment_method_id': self.payment_method_id.id,
            'folio_id': self.folio_id.id,
            'reservation_id': self.reservation_id.id,
            
            # 🔥 LIEN AVEC LA FACTURE (crucial pour le lettrage)
            'reconciled_invoice_ids': [(6, 0, [invoice.id])],
        }
        
        # Ajouter informations spécifiques selon le type de paiement
        if self.payment_method_id.payment_type == 'mobile_money':
            payment_vals.update({
                'mobile_phone': self.mobile_phone,
                'mobile_reference': self.mobile_reference,
            })
        elif self.payment_method_id.payment_type == 'check':
            payment_vals.update({
                'check_number': self.check_number,
                'check_date': self.check_date,
                'check_bank': self.check_bank,
            })
        
        # Créer le paiement
        payment = self.env['account.payment'].create(payment_vals)
        
        # ✅ VALIDER LE PAIEMENT (crée les écritures comptables)
        payment.action_post()
        
        # ✅ LETTRAGE AUTOMATIQUE
        # Odoo 18 fait le lettrage automatiquement grâce à reconciled_invoice_ids
        # Mais on force si nécessaire
        if invoice.payment_state not in ['paid', 'in_payment']:
            self._force_reconciliation(invoice, payment)
        
        # Message de confirmation
        self.folio_id.message_post(
            body=_('💰 Paiement de %s enregistré via %s\n'
                   '✅ Lettré avec la facture %s\n'
                   '📊 Écritures comptables créées dans le journal %s') % (
                self.payment_amount,
                self.payment_method_id.name,
                invoice.name,
                self.payment_method_id.journal_id.name
            ),
            subject='Paiement Comptabilisé'
        )
        
        return payment

    def _force_reconciliation(self, invoice, payment):
        """Force le lettrage entre la facture et le paiement"""
        # Récupérer les lignes comptables à lettrer
        invoice_receivable_lines = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        payment_receivable_lines = payment.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
        )
        
        # Effectuer le lettrage
        if invoice_receivable_lines and payment_receivable_lines:
            (invoice_receivable_lines + payment_receivable_lines).reconcile()

    # ============================================================================
    # ✅ FINALISER LE CHECK-OUT
    # ============================================================================
    def _finalize_checkout(self):
        """Finalise le check-out (statuts, nettoyage, messages)"""
        self.ensure_one()
        
        # Mettre à jour la réservation
        self.reservation_id.write({
            'state': 'checkout',
            'actual_checkout_date': self.checkout_datetime,
        })
        
        # Mettre à jour le statut de la chambre
        self.room_id.write({'status': 'cleaning'})
        
        # Créer une tâche de nettoyage
        self.env['hotel.housekeeping'].create({
            'room_id': self.room_id.id,
            'cleaning_type': 'checkout',
            'state': 'pending',
            'date': fields.Date.today(),
            'notes': self.damage_description if self.room_inspection == 'damage' else None,
        })
        
        # Fermer le folio
        self.folio_id.write({'state': 'closed'})
        
        # Ajouter notes et satisfaction
        notes_parts = [_('✅ Check-out effectué le %s') % self.checkout_datetime]
        
        if self.notes:
            notes_parts.append(_('📝 Notes: %s') % self.notes)
        
        if self.satisfaction_rating:
            notes_parts.append(_('⭐ Satisfaction: %s/5') % self.satisfaction_rating)
        
        if self.room_inspection == 'damage':
            notes_parts.append(_('⚠️ Dommages constatés: %s (Coût: %s)') % (
                self.damage_description, self.damage_cost
            ))
        
        self.reservation_id.message_post(
            body='\n'.join(notes_parts),
            subject='Check-out Finalisé'
        )

    # ============================================================================
    # ✅ AJOUT DES FRAIS DE DOMMAGES
    # ============================================================================
    def _add_damage_charge(self):
        """Ajoute une ligne de service pour les dommages"""
        self.ensure_one()
        
        # Récupérer ou créer le service de dommages
        damage_service = self.env.ref(
            'hotel_management_custom.service_damage',
            raise_if_not_found=False
        )
        
        if not damage_service:
            damage_service = self.env['hotel.service'].create({
                'name': 'Frais de Dommages',
                'category': 'other',
                'price': 0,
                'active': True,
            })
        
        # Créer la ligne de service
        self.env['hotel.service.line'].create({
            'folio_id': self.folio_id.id,
            'reservation_id': self.reservation_id.id,
            'service_id': damage_service.id,
            'quantity': 1,
            'price_unit': self.damage_cost,
            'notes': self.damage_description or 'Dommages constatés au check-out',
            'date': fields.Datetime.now(),
        })
        
        self.folio_id.message_post(
            body=_('⚠️ Frais de dommages ajoutés: %s') % self.damage_cost,
            subject='Dommages Facturés'
        )

    # ============================================================================
    # ✅ IMPRESSION
    # ============================================================================
    def action_print_folio(self):
        """Imprimer le folio"""
        self.ensure_one()
        return self.env.ref('hotel_management_custom.action_report_folio').report_action(self.folio_id)