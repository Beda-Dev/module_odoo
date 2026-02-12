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
        default=lambda self: _('Nouveau'),
        index=True
    )
    
    entreprise_id = fields.Many2one(
        'res.partner',
        string='Entreprise',
        required=True,
        domain=[('is_cantine_client', '=', True)],
        ondelete='restrict',
        index=True
    )
    
    date = fields.Date(
        string='Date de la commande',
        required=True,
        default=fields.Date.today,
        index=True
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
    
    option_ids = fields.Many2many(
        'lagunes.plat.option',
        'lagunes_commande_option_rel',
        'commande_id',
        'option_id',
        string='Options'
    )
    
    notes = fields.Text(
        string='Notes / Instructions spéciales'
    )
    
    employee_name = fields.Char(
        string='Nom de l\'employé',
        help='Nom de l\'employé qui a passé la commande'
    )
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prêt'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', required=True, index=True)
    
    facturation_state = fields.Selection([
        ('not_invoiced', 'Non facturée'),
        ('to_invoice', 'À facturer'),
        ('invoiced', 'Facturée'),
    ], string='État facturation', default='not_invoiced', required=True)
    
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
    
    @api.depends('quantity', 'prix_unitaire', 'option_ids')
    def _compute_prix_total(self):
        """Calcul du prix total incluant les options"""
        for commande in self:
            prix_base = commande.quantity * commande.prix_unitaire
            prix_options = sum(commande.option_ids.mapped('prix_supplementaire'))
            commande.prix_total = prix_base + (prix_options * commande.quantity)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Générer une référence unique à la création"""
        for vals in vals_list:
            if vals.get('reference', _('Nouveau')) == _('Nouveau'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('lagunes.commande') or _('Nouveau')
        
        return super(LagunesCommande, self).create(vals_list)
    
    @api.constrains('quantity')
    def _check_quantity(self):
        """Vérifier que la quantité est exactement 1"""
        for commande in self:
            if commande.quantity != 1:
                raise ValidationError("La quantité par commande est limitée à 1 portion.")
    
    @api.constrains('entreprise_id', 'date')
    def _check_max_orders_per_day(self):
        """
        Vérifier que l'entreprise n'a pas dépassé sa limite de commandes par jour
        """
        for record in self:
            if not record.entreprise_id or not record.date:
                continue
            
            max_orders = record.entreprise_id.max_orders_per_day
            
            # Si max_orders = 0, pas de limite
            if max_orders <= 0:
                continue
            
            # Compter les commandes non annulées pour cette entreprise ce jour
            count = self.search_count([
                ('id', '!=', record.id),  # Exclure la commande actuelle
                ('entreprise_id', '=', record.entreprise_id.id),
                ('date', '=', record.date),
                ('state', '!=', 'cancelled')
            ])
            
            if count >= max_orders:
                raise ValidationError(
                    f"Limite de {max_orders} commande(s) par jour atteinte pour "
                    f"{record.entreprise_id.name}.\n\n"
                    f"{count} commande(s) déjà passée(s) aujourd'hui."
                )
    
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
                'price_unit': self.prix_total,  # Prix total incluant options
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
        description = f"{self.plat_id.name}"
        
        options = self.option_ids.mapped('name')
        if options:
            description += f" ({', '.join(options)})"
        
        if self.notes:
            description += f"\nNotes: {self.notes}"
        
        return description
    
    def get_options_display(self):
        """Retourner les options pour affichage"""
        self.ensure_one()
        options = self.option_ids.mapped('name')
        return ', '.join(options) if options else 'Aucune'