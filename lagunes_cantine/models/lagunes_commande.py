# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class LagunesCommande(models.Model):
    _name = 'lagunes.commande'
    _description = 'Commande cantine'
    _order = 'date desc, create_date desc'
    _rec_name = 'reference'

    reference = fields.Char(
        string='Référence',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Nouveau')
    )
    
    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='restrict'
    )
    
    employee_id = fields.Many2one(
        'lagunes.employee',
        string='Employé',
        required=True,
        ondelete='restrict',
        help='Employé qui passe la commande'
    )
    
    employee_name = fields.Char(
        string='Nom de l\'employé (mémorisation)',
        related='employee_id.name',
        store=True,
        readonly=True
    )
    
    date = fields.Date(
        string='Date de la commande',
        required=True,
        default=fields.Date.today
    )
    
    menu_id = fields.Many2one(
        'lagunes.menu',
        string='Menu',
        required=True,
        ondelete='restrict'
    )
    
    plat_id = fields.Many2one(
        'lagunes.plat',
        string='Plat commandé',
        required=True,
        ondelete='restrict'
    )
    
    quantity = fields.Integer(
        string='Quantité',
        default=1,
        required=True
    )
    
    option_sans_sel = fields.Boolean(
        string='Sans sel',
        default=False
    )
    
    option_piment_apart = fields.Boolean(
        string='Piment à part',
        default=False
    )
    
    notes = fields.Text(
        string='Notes / Instructions spéciales'
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prêt'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', required=True, tracking=True)
    
    facturation_state = fields.Selection([
        ('not_invoiced', 'Non facturée'),
        ('to_invoice', 'À facturer'),
        ('invoiced', 'Facturée'),
    ], string='État facturation', default='not_invoiced', required=True, tracking=True)
    
    prix_unitaire = fields.Float(
        string='Prix unitaire',
        related='plat_id.prix_unitaire',
        store=True
    )
    
    prix_total = fields.Float(
        string='Prix total',
        compute='_compute_prix_total',
        store=True
    )
    
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande de vente',
        readonly=True,
        copy=False
    )
    
    create_date = fields.Datetime(
        string='Date de création',
        readonly=True
    )
    
    create_uid = fields.Many2one(
        'res.users',
        string='Créé par',
        readonly=True
    )
    
    @api.depends('quantity', 'prix_unitaire')
    def _compute_prix_total(self):
        """Calcul du prix total"""
        for commande in self:
            commande.prix_total = commande.quantity * commande.prix_unitaire
    
    @api.model_create_multi
    def create(self, vals_list):
        """Générer une référence unique à la création"""
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('lagunes.commande') or _('Nouveau')
        
        return super(LagunesCommande, self).create(vals_list)
    
    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifier que la quantité est positive"""
        for commande in self:
            if commande.quantity <= 0:
                raise ValidationError("La quantité doit être supérieure à 0")
    
    @api.onchange('menu_id')
    def _onchange_menu_id(self):
        """Filtrer les plats selon le menu sélectionné"""
        if self.menu_id:
            return {'domain': {'plat_id': [('id', 'in', self.menu_id.plat_ids.ids)]}}
        return {'domain': {'plat_id': []}}
    
    def action_confirm(self):
        """Confirmer la commande"""
        for commande in self:
            commande.state = 'confirmed'
    
    def action_prepare(self):
        """Marquer comme en préparation"""
        for commande in self:
            commande.state = 'preparing'
    
    def action_ready(self):
        """Marquer comme prêt"""
        for commande in self:
            commande.state = 'ready'
    
    def action_deliver(self):
        """Marquer comme livré"""
        for commande in self:
            commande.state = 'delivered'
    
    def action_cancel(self):
        """Annuler la commande"""
        for commande in self:
            commande.state = 'cancelled'
    
    def create_sale_order(self):
        """
        Créer une commande de vente (pour facturation future)
        Cette fonction sera utilisée lors de la facturation mensuelle
        """
        self.ensure_one()
        
        if self.sale_order_id:
            raise ValidationError("Une commande de vente existe déjà pour cette commande")
        
        # Créer la commande de vente
        sale_order = self.env['sale.order'].create({
            'partner_id': self.entreprise_id.id,
            'date_order': datetime.now(),
            'order_line': [(0, 0, {
                'product_id': self.plat_id.product_id.id,
                'name': self._get_order_line_description(),
                'product_uom_qty': self.quantity,
                'price_unit': self.prix_unitaire,
                'tax_id': [(5, 0, 0)],  # Pas de TVA
            })]
        })
        
        self.sale_order_id = sale_order.id
        self.facturation_state = 'to_invoice'
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commande de vente',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _get_order_line_description(self):
        """Générer la description de la ligne de commande"""
        description = f"{self.plat_id.name} - {self.employee_name}"
        
        options = []
        if self.option_sans_sel:
            options.append("Sans sel")
        if self.option_piment_apart:
            options.append("Piment à part")
        
        if options:
            description += f" ({', '.join(options)})"
        
        if self.notes:
            description += f"\nNotes: {self.notes}"
        
        return description
    
    def get_options_display(self):
        """Retourner les options pour affichage"""
        self.ensure_one()
        options = []
        if self.option_sans_sel:
            options.append('Sans sel')
        if self.option_piment_apart:
            options.append('Piment à part')
        return ', '.join(options) if options else 'Aucune'


class LagunesCommandeLine(models.Model):
    """
    Modèle optionnel pour gérer plusieurs plats par commande
    (extension future si nécessaire)
    """
    _name = 'lagunes.commande.line'
    _description = 'Ligne de commande cantine'

    commande_id = fields.Many2one(
        'lagunes.commande',
        string='Commande',
        required=True,
        ondelete='cascade'
    )
    
    plat_id = fields.Many2one(
        'lagunes.plat',
        string='Plat',
        required=True,
        ondelete='restrict'
    )
    
    quantity = fields.Integer(
        string='Quantité',
        default=1,
        required=True
    )
    
    option_sans_sel = fields.Boolean(
        string='Sans sel',
        default=False
    )
    
    option_piment_apart = fields.Boolean(
        string='Piment à part',
        default=False
    )
    
    prix_unitaire = fields.Float(
        string='Prix unitaire',
        related='plat_id.prix_unitaire'
    )
    
    prix_total = fields.Float(
        string='Prix total',
        compute='_compute_prix_total',
        store=True
    )
    
    @api.depends('quantity', 'prix_unitaire')
    def _compute_prix_total(self):
        for line in self:
            line.prix_total = line.quantity * line.prix_unitaire
