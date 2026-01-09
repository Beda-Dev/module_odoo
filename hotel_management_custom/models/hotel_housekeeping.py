# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError , ValidationError


class HotelHousekeeping(models.Model):
    _name = 'hotel.housekeeping'
    _description = 'Nettoyage de Chambre'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))

    # Chambre
    room_id = fields.Many2one('hotel.room', string='Chambre', required=True, tracking=True)
    room_status = fields.Selection(related='room_id.status', string='Statut Chambre', readonly=True)

    # Type de nettoyage
    cleaning_type = fields.Selection([
        ('daily', 'Nettoyage Quotidien'),
        ('checkout', 'Nettoyage Après Départ'),
        ('deep', 'Grand Nettoyage'),
        ('turndown', 'Service du Soir'),
    ], string='Type de Nettoyage', required=True, default='daily', tracking=True)

    # Dates
    date = fields.Date(string='Date', required=True, default=fields.Date.today, tracking=True)
    start_time = fields.Datetime(string='Heure de Début')
    end_time = fields.Datetime(string='Heure de Fin')
    duration = fields.Float(string='Durée (heures)', compute='_compute_duration', store=True)

    # Employé assigné
    employee_id = fields.Many2one('hr.employee', string='Employé', tracking=True)

    # État
    state = fields.Selection([
        ('pending', 'En Attente'),
        ('in_progress', 'En Cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='pending', required=True, tracking=True)

    # Inspection
    inspection_required = fields.Boolean(string='Inspection Requise', default=True)
    inspected = fields.Boolean(string='Inspecté', readonly=True)
    inspected_by = fields.Many2one('res.users', string='Inspecté par', readonly=True)
    inspection_date = fields.Datetime(string='Date d\'Inspection', readonly=True)
    inspection_notes = fields.Text(string='Notes d\'Inspection')

    # Qualité
    quality_rating = fields.Selection([
        ('1', 'Mauvais'),
        ('2', 'Passable'),
        ('3', 'Bien'),
        ('4', 'Très Bien'),
        ('5', 'Excellent'),
    ], string='Note de Qualité')

    # Produits utilisés
    product_line_ids = fields.One2many('hotel.housekeeping.product', 'housekeeping_id',
                                       string='Produits Utilisés')

    # Observations
    notes = fields.Text(string='Notes')
    issues_found = fields.Text(string='Problèmes Constatés')

    # Photos (optionnel)
    image_before = fields.Binary(string='Photo Avant')
    image_after = fields.Binary(string='Photo Après')

    company_id = fields.Many2one('res.company', string='Société',
                                 default=lambda self: self.env.company)

    color = fields.Integer(string='Couleur Kanban')

    @api.constrains('room_id')
    def _check_room_not_occupied(self):
        """Vérifier que la chambre n'est pas occupée"""
        for record in self:
            if record.room_id.status == 'occupied':
                raise ValidationError(_(
                    'Impossible de créer un nettoyage pour la chambre %s car elle est actuellement occupée. '
                    'Veuillez d\'abord effectuer le check-out du client.'
                ) % record.room_id.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.housekeeping') or _('Nouveau')
        return super(HotelHousekeeping, self).create(vals_list)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.duration = delta.total_seconds() / 3600.0
            else:
                record.duration = 0.0

    def action_start(self):
        """Commencer le nettoyage"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Seules les tâches en attente peuvent être démarrées.'))

            # Vérifier que la chambre n'est pas occupée
            if record.room_id.status == 'occupied':
                raise UserError(_(
                    'Impossible de démarrer le nettoyage de la chambre %s car elle est actuellement occupée. '
                    'Veuillez d\'abord effectuer le check-out du client.'
                ) % record.room_id.name)    

            record.write({
                'state': 'in_progress',
                'start_time': fields.Datetime.now(),
            })

            record.room_id.write({'status': 'cleaning'})
            record.message_post(body=_('Nettoyage démarré par %s') % (record.employee_id.name or 'N/A'))

        return True

    def action_complete(self):
        """Terminer le nettoyage"""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Seules les tâches en cours peuvent être terminées.'))

            record.write({
                'state': 'completed',
                'end_time': fields.Datetime.now(),
            })

            # Si inspection non requise, marquer la chambre comme disponible
            if not record.inspection_required:
                record.room_id.write({'status': 'available'})
                record.message_post(body=_('Nettoyage terminé. Chambre disponible.'))
            else:
                record.message_post(body=_('Nettoyage terminé. En attente d\'inspection.'))

        return True

    def action_inspect(self):
        """Inspecter la chambre nettoyée"""
        for record in self:
            if record.state != 'completed':
                raise UserError(_('Seules les tâches terminées peuvent être inspectées.'))

            record.write({
                'inspected': True,
                'inspected_by': self.env.user.id,
                'inspection_date': fields.Datetime.now(),
            })

            # Marquer la chambre comme disponible après inspection
            record.room_id.write({'status': 'available'})
            record.message_post(body=_('Inspection effectuée par %s. Chambre disponible.') % self.env.user.name)

        return True

    def action_cancel(self):
        """Annuler la tâche de nettoyage"""
        for record in self:
            if record.state == 'completed':
                raise UserError(_('Impossible d\'annuler une tâche terminée.'))

            record.write({'state': 'cancelled'})
            record.message_post(body=_('Tâche de nettoyage annulée'))

        return True

    def action_add_product(self):
        """Ajouter un produit utilisé"""
        self.ensure_one()
        return {
            'name': _('Ajouter un Produit'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.housekeeping.product',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_housekeeping_id': self.id},
        }


class HotelHousekeepingProduct(models.Model):
    _name = 'hotel.housekeeping.product'
    _description = 'Produit de Nettoyage Utilisé'

    housekeeping_id = fields.Many2one('hotel.housekeeping', string='Nettoyage',
                                      required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Produit',
                                 required=True, domain=[('type', '=', 'consu')]) # type = consu ou service ou combo
    quantity = fields.Float(string='Quantité', required=True, default=1.0)
    uom_id = fields.Many2one(related='product_id.uom_id', string='Unité')

    # Mouvement de stock
    stock_move_id = fields.Many2one('stock.move', string='Mouvement de Stock', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        product_lines = super(HotelHousekeepingProduct, self).create(vals_list)
        for product_line in product_lines:
            product_line._create_stock_move()
        return product_lines

    def _create_stock_move(self):
        """Créer un mouvement de stock pour le produit utilisé"""
        self.ensure_one()

        # Trouver les emplacements
        # Utiliser une recherche directe au lieu de ref pour éviter les dépendances manquantes
        location_src = self.env['stock.location'].search([
            ('name', 'ilike', 'stock'),
            ('usage', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not location_src:
            # Fallback : chercher un emplacement interne
            location_src = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
            ], limit=1)

        location_dest = self.env['stock.location'].search([
            ('name', 'ilike', 'customers'),
            ('usage', '=', 'customer'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not location_dest:
            # Fallback : chercher un emplacement client
            location_dest = self.env['stock.location'].search([
                ('usage', '=', 'customer'),
                ('usage', '=', 'customer')
            ], limit=1)

        if not location_src or not location_dest:
            return

        move = self.env['stock.move'].create({
            'name': _('Nettoyage: %s') % self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': self.housekeeping_id.name,
        })

        move._action_confirm()
        move._action_assign()
        move._action_done()

        self.stock_move_id = move