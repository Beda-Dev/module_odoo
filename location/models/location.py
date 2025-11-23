from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class MarqueVehicule(models.Model):
    _name = 'location.marque'
    _description = 'Marque de véhicule'
    _order = 'name asc'

    name = fields.Char('Nom de la marque', required=True, unique=True)
    code = fields.Char('Code', required=True, unique=True)
    description = fields.Text('Description')
    actif = fields.Boolean('Actif', default=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Cette marque existe déjà !'),
        ('code_unique', 'UNIQUE(code)', 'Ce code existe déjà !'),
    ]

class Vehicule(models.Model):
    _name = 'location.vehicule'
    _description = 'Véhicule disponible à la location'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Nom du véhicule', required=True, tracking=True)
    marque_id = fields.Many2one('location.marque', string='Marque', 
                                required=True, tracking=True, 
                                oldname='marque')
    modele = fields.Char('Modèle', tracking=True)
    immatriculation = fields.Char('Immatriculation', required=True, tracking=True)
    
    # Images
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    image_128 = fields.Image("Image 128", related="image_1920", max_width=128, max_height=128, store=True)
    
    # Caractéristiques techniques
    annee = fields.Integer('Année', tracking=True)
    couleur = fields.Char('Couleur', tracking=True)
    type_carburant = fields.Selection([
        ('essence', 'Essence'),
        ('diesel', 'Diesel'),
        ('electrique', 'Électrique'),
        ('hybride', 'Hybride'),
    ], string='Type de carburant', tracking=True)
    nombre_places = fields.Integer('Nombre de places', default=5, tracking=True)
    kilometrage = fields.Float('Kilométrage actuel (km)', tracking=True)
    numero_chassis = fields.Char('Numéro de châssis', tracking=True)
    
    # Tarification
    prix_journalier = fields.Float('Prix par jour', required=True, tracking=True)
    prix_hebdomadaire = fields.Float('Prix par semaine', tracking=True)
    prix_mensuel = fields.Float('Prix par mois', tracking=True)
    caution = fields.Float('Montant de la caution', default=500.0, tracking=True)
    
    # Documents
    date_mise_circulation = fields.Date('Date de mise en circulation', tracking=True)
    date_derniere_revision = fields.Date('Dernière révision', tracking=True)
    date_prochaine_revision = fields.Date('Prochaine révision', tracking=True)
    date_expiration_assurance = fields.Date('Expiration assurance', tracking=True)
    numero_police_assurance = fields.Char('N° police d\'assurance', tracking=True)
    
    statut = fields.Selection([
        ('disponible', 'Disponible'),
        ('loue', 'Loué'),
        ('maintenance', 'En maintenance'),
        ('hors_service', 'Hors service'),
    ], string='Statut', default='disponible', required=True, tracking=True)

    location_ids = fields.One2many('location.location', 'vehicule_id', string='Historique des locations')
    
    # Champs calculés
    total_locations = fields.Integer('Total locations', compute='_compute_total_locations')
    revenu_total = fields.Float('Revenu total généré', compute='_compute_revenu_total')
    
    _sql_constraints = [
        ('immatriculation_unique', 'UNIQUE(immatriculation)', 
         'Cette immatriculation existe déjà !'),
        ('check_annee', 'CHECK(annee >= 1900 AND annee <= 2100)', 
         'L\'année doit être valide !'),
    ]

    @api.depends('location_ids')
    def _compute_total_locations(self):
        for record in self:
            record.total_locations = len(record.location_ids)
    
    @api.depends('location_ids.montant_total', 'location_ids.statut')
    def _compute_revenu_total(self):
        for record in self:
            locations_terminees = record.location_ids.filtered(
                lambda l: l.statut == 'terminee'
            )
            record.revenu_total = sum(locations_terminees.mapped('montant_total'))
    
    def action_view_locations(self):
        """Affiche toutes les locations de ce véhicule"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Locations',
            'res_model': 'location.location',
            'view_mode': 'list,form',
            'domain': [('vehicule_id', '=', self.id)],
            'context': {'default_vehicule_id': self.id},
        }

class Location(models.Model):
    _name = 'location.location'
    _description = 'Contrat de location de véhicule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_debut desc, id desc'

    name = fields.Char('Numéro de contrat', required=True, copy=False, 
                       readonly=True, default='Nouveau')
    
    company_id = fields.Many2one('res.company', string='Société', 
                                  required=True, 
                                  default=lambda self: self.env.company)
    
    # Informations principales
    vehicule_id = fields.Many2one('location.vehicule', string='Véhicule', 
                                  required=True, tracking=True)
                                  
    client_id = fields.Many2one('res.partner', string='Client', 
                                required=True, tracking=True)
    
    # Dates
    date_debut = fields.Date('Date de début', required=True, 
                            default=fields.Date.today, tracking=True)
    date_fin = fields.Date('Date de fin', required=True, tracking=True)
    duree_jours = fields.Integer('Durée (jours)', compute='_compute_duree', store=True)
    
    # Informations véhicule
    kilometrage_depart = fields.Float('Kilométrage départ', tracking=True)
    kilometrage_retour = fields.Float('Kilométrage retour', tracking=True)
    kilometrage_parcouru = fields.Float('Km parcourus', compute='_compute_km_parcouru')
    niveau_carburant_depart = fields.Selection([
        ('vide', 'Vide'),
        ('1/4', '1/4'),
        ('1/2', '1/2'),
        ('3/4', '3/4'),
        ('plein', 'Plein'),
    ], string='Carburant départ', default='plein', tracking=True)
    niveau_carburant_retour = fields.Selection([
        ('vide', 'Vide'),
        ('1/4', '1/4'),
        ('1/2', '1/2'),
        ('3/4', '3/4'),
        ('plein', 'Plein'),
    ], string='Carburant retour', tracking=True)
    
    # Tarification
    prix_journalier = fields.Float(related='vehicule_id.prix_journalier', 
                                   string='Prix journalier', readonly=True)
    montant_location = fields.Float('Montant location', compute='_compute_montant', store=True)
    montant_caution = fields.Float(related='vehicule_id.caution', 
                                   string='Caution', readonly=True)
    frais_supplementaires = fields.Float('Frais supplémentaires', tracking=True)
    reduction = fields.Float('Réduction (%)', default=0.0, tracking=True)
    montant_total = fields.Float('Montant total', compute='_compute_montant', store=True)
    
    # Paiement
    mode_paiement = fields.Selection([
        ('especes', 'Espèces'),
        ('carte', 'Carte bancaire'),
        ('virement', 'Virement'),
        ('cheque', 'Chèque'),
        ('wave', 'Wave'),
        ('orange', 'Orange Money'),
        ('mtn', 'Mtn Money'),
        
    ], string='Mode de paiement', tracking=True)
    caution_payee = fields.Boolean('Caution payée', default=False, tracking=True)
    caution_restituee = fields.Boolean('Caution restituée', default=False, tracking=True)
    
    # Intégration comptable
    invoice_id = fields.Many2one('account.move', string='Facture', readonly=True)
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    
    statut = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ], string='Statut', default='brouillon', required=True, tracking=True)
    
    # Notes
    notes = fields.Text('Notes', tracking=True)
    etat_vehicule_depart = fields.Text('État du véhicule au départ', tracking=True)
    etat_vehicule_retour = fields.Text('État du véhicule au retour', tracking=True)
    
    # Conducteur additionnel
    conducteur_additionnel_ids = fields.Many2many(
        'res.partner', 
        string='Conducteurs additionnels',
        tracking=True
    )
    
    # Options
    assurance_tous_risques = fields.Boolean('Assurance tous risques', tracking=True)
    gps_inclus = fields.Boolean('GPS inclus', tracking=True)
    siege_bebe = fields.Boolean('Siège bébé', tracking=True)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('location.location') or 'Nouveau'
        return super(Location, self).create(vals_list)
    
    @api.depends('date_debut', 'date_fin')
    def _compute_duree(self):
        for record in self:
            if record.date_debut and record.date_fin:
                record.duree_jours = (record.date_fin - record.date_debut).days + 1
            else:
                record.duree_jours = 0
    
    @api.depends('kilometrage_depart', 'kilometrage_retour')
    def _compute_km_parcouru(self):
        for record in self:
            if record.kilometrage_depart and record.kilometrage_retour:
                record.kilometrage_parcouru = record.kilometrage_retour - record.kilometrage_depart
            else:
                record.kilometrage_parcouru = 0.0

    @api.depends('date_debut', 'date_fin', 'vehicule_id.prix_journalier', 
                 'frais_supplementaires', 'reduction')
    def _compute_montant(self):
        """Calcule automatiquement le montant total de la location"""
        for record in self:
            if record.date_debut and record.date_fin and record.vehicule_id:
                nb_jours = (record.date_fin - record.date_debut).days + 1
                montant_base = nb_jours * record.vehicule_id.prix_journalier
                record.montant_location = montant_base
                
                # Application de la réduction
                montant_reduction = montant_base * (record.reduction / 100)
                montant_apres_reduction = montant_base - montant_reduction
                record.montant_total = montant_apres_reduction + record.frais_supplementaires
            else:
                record.montant_location = 0.0
                record.montant_total = 0.0
    
    @api.depends('invoice_id')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 1 if record.invoice_id else 0
    
    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        """Vérifie que la date de fin est après la date de début"""
        for record in self:
            if record.date_debut and record.date_fin:
                if record.date_fin < record.date_debut:
                    raise ValidationError(
                        "La date de fin doit être postérieure à la date de début !"
                    )
    
    @api.constrains('reduction')
    def _check_reduction(self):
        for record in self:
            if record.reduction < 0 or record.reduction > 100:
                raise ValidationError("La réduction doit être entre 0 et 100%")
    
    @api.constrains('vehicule_id', 'date_debut', 'date_fin')
    def _check_disponibilite(self):
        """Vérifie qu'un véhicule n'est pas déjà loué sur la période"""
        for record in self:
            if record.vehicule_id and record.date_debut and record.date_fin:
                chevauchement = self.search([
                    ('vehicule_id', '=', record.vehicule_id.id),
                    ('id', '!=', record.id),
                    ('statut', 'in', ['confirmee', 'en_cours']),
                    '|',
                    '&', ('date_debut', '<=', record.date_debut), 
                         ('date_fin', '>=', record.date_debut),
                    '&', ('date_debut', '<=', record.date_fin), 
                         ('date_fin', '>=', record.date_fin),
                ])
                if chevauchement:
                    raise ValidationError(
                        f"Le véhicule {record.vehicule_id.name} est déjà loué du "
                        f"{chevauchement[0].date_debut} au {chevauchement[0].date_fin} !"
                    )
    
    def action_confirmer(self):
        """Confirme la location et rend le véhicule indisponible"""
        for record in self:
            record.statut = 'confirmee'
            record.vehicule_id.statut = 'loue'
            record.message_post(body="Location confirmée")
    
    def action_demarrer(self):
        """Démarre la location"""
        for record in self:
            if record.statut == 'confirmee':
                record.statut = 'en_cours'
                record.message_post(body="Location démarrée")
    
    def action_terminer(self):
        """Termine la location et libère le véhicule"""
        for record in self:
            record.statut = 'terminee'
            record.vehicule_id.statut = 'disponible'
            record.message_post(body="Location terminée")
    
    def action_annuler(self):
        """Annule la location et libère le véhicule"""
        for record in self:
            record.statut = 'annulee'
            if record.vehicule_id.statut == 'loue':
                record.vehicule_id.statut = 'disponible'
            record.message_post(body="Location annulée")
    
    def action_create_invoice(self):
        """Crée une facture pour la location"""
        self.ensure_one()
        
        if self.invoice_id:
            raise ValidationError("Une facture existe déjà pour cette location")
        
        # Création de la facture
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.client_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {
                    'name': f'Location {self.vehicule_id.name} du {self.date_debut} au {self.date_fin}',
                    'quantity': self.duree_jours,
                    'price_unit': self.prix_journalier,
                }),
            ]
        }
        
        # Ajout des frais supplémentaires si présents
        if self.frais_supplementaires > 0:
            invoice_vals['invoice_line_ids'].append(
                (0, 0, {
                    'name': 'Frais supplémentaires',
                    'quantity': 1,
                    'price_unit': self.frais_supplementaires,
                })
            )
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_invoice(self):
        """Affiche la facture associée"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Facture',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_print_contract(self):
        """Imprime le contrat de location"""
        self.ensure_one()
        return self.env.ref('location.report_location_contract').report_action(self)