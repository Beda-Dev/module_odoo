# -*- coding: utf-8 -*-

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Désactiver automatiquement la TVA pour les produits de cantine
        (régime micro-entreprise)
        """
        res = super(ProductTemplate, self).create(vals_list)
        
        # Vérifier si c'est un produit créé via lagunes.plat
        for product in res:
            # Retirer toutes les taxes
            if product.categ_id and 'Cantine' in product.categ_id.complete_name:
                product.taxes_id = [(5, 0, 0)]
                product.supplier_taxes_id = [(5, 0, 0)]
        
        return res
