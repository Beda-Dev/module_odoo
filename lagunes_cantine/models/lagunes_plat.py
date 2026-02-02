# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LagunesPlat(models.Model):
    _name = 'lagunes.plat'
    _description = 'Plat de la cantine'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nom du plat',
        required=True,
        translate=True
    )
    
    sequence = fields.Integer(
        string='Séquence',
        default=10
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Produit associé',
        required=True,
        domain=[('type', '=', 'consu')],
        ondelete='restrict'
    )
    
    description = fields.Text(
        string='Description',
        translate=True
    )
    
    image_1920 = fields.Image(
        string='Image',
        related='product_id.image_1920',
        readonly=False
    )
    
    image_128 = fields.Image(
        string='Image (128x128)',
        related='product_id.image_128'
    )
    
    category_id = fields.Many2one(
        'product.category',
        string='Catégorie',
        related='product_id.categ_id',
        readonly=False
    )
    
    active = fields.Boolean(
        string='Actif',
        default=True
    )
    
    option_ids = fields.Many2many(
        'lagunes.plat.option',
        'lagunes_plat_option_rel',
        'plat_id',
        'option_id',
        string='Options disponibles',
        help='Options que les clients peuvent choisir pour ce plat'
    )
    
    option_sans_sel = fields.Boolean(
        string='Option "Sans sel" disponible',
        default=True,
        help='Permet au client de commander ce plat sans sel'
    )
    
    option_piment_apart = fields.Boolean(
        string='Option "Piment à part" disponible',
        default=True,
        help='Permet au client de demander le piment à part'
    )
    
    menu_ids = fields.Many2many(
        'lagunes.menu',
        'lagunes_menu_plat_rel',
        'plat_id',
        'menu_id',
        string='Menus'
    )
    
    prix_unitaire = fields.Float(
        string='Prix unitaire',
        related='product_id.list_price',
        readonly=False,
        help='Prix du plat (sans TVA - régime micro-entreprise)'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Créer automatiquement un produit si non fourni"""
        for vals in vals_list:
            if not vals.get('product_id'):
                # Créer un produit consommable
                product = self.env['product.product'].create({
                    'name': vals.get('name', 'Nouveau plat'),
                    'type': 'consu',
                    'sale_ok': True,
                    'purchase_ok': False,
                    'invoice_policy': 'order',
                    'taxes_id': [(5, 0, 0)],  # Pas de TVA
                })
                vals['product_id'] = product.id
        
        return super(LagunesPlat, self).create(vals_list)
    
    def write(self, vals):
        """Synchroniser le nom avec le produit"""
        res = super(LagunesPlat, self).write(vals)
        
        if 'name' in vals:
            for plat in self:
                if plat.product_id:
                    plat.product_id.name = vals['name']
        
        return res
