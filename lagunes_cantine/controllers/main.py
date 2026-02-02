# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import date, timedelta
import json


class LagunesCantineController(http.Controller):
    
    @http.route('/cantine', type='http', auth='public', website=True)
    def cantine_home(self, **kwargs):
        """Page d'accueil de la cantine"""
        entreprises = request.env['res.partner'].sudo().search([
            ('is_cantine_client', '=', True),
            ('active', '=', True)
        ])
        
        return request.render('lagunes_cantine.cantine_home', {
            'entreprises': entreprises,
        })
    
    @http.route('/cantine/access/<int:entreprise_id>', type='http', auth='public', website=True)
    def cantine_access(self, entreprise_id, **kwargs):
        """Page d'accès pour une entreprise"""
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        
        if not entreprise.exists() or not entreprise.is_cantine_client:
            return request.render('lagunes_cantine.error_page', {
                'error_message': 'Entreprise non trouvée'
            })
        
        return request.render('lagunes_cantine.cantine_access', {
            'entreprise': entreprise,
        })
    
    @http.route('/cantine/verify_access', type='json', auth='public', website=True)
    def verify_access(self, entreprise_id, employee_name, access_code=None):
        """Vérifier l'accès d'un employé (AJAX)"""
        result = request.env['res.partner'].sudo().verify_cantine_access(
            entreprise_id=entreprise_id,
            employee_name=employee_name,
            access_code=access_code
        )
        
        if result['success']:
            # Stocker les infos dans la session
            request.session['cantine_entreprise_id'] = entreprise_id
            request.session['cantine_employee_name'] = employee_name
            request.session['cantine_access_time'] = str(date.today())
        
        return result
    
    @http.route('/cantine/menu/<int:entreprise_id>', type='http', auth='public', website=True)
    def cantine_menu(self, entreprise_id, menu_date=None, **kwargs):
        """Afficher le menu d'une entreprise"""
        # Vérifier l'accès via la session
        if not self._check_session_access(entreprise_id):
            return request.redirect(f'/cantine/access/{entreprise_id}')
        
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        employee_name = request.session.get('cantine_employee_name', 'Employé')
        
        # Date du menu
        if menu_date:
            try:
                target_date = date.fromisoformat(menu_date)
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()
        
        # Récupérer le menu
        menu = request.env['lagunes.menu'].sudo().get_menu_for_entreprise(
            entreprise_id=entreprise_id,
            target_date=target_date
        )
        
        # Dates pour navigation
        previous_date = target_date - timedelta(days=1)
        next_date = target_date + timedelta(days=1)
        
        return request.render('lagunes_cantine.cantine_menu', {
            'entreprise': entreprise,
            'employee_name': employee_name,
            'menu': menu,
            'target_date': target_date,
            'previous_date': previous_date,
            'next_date': next_date,
            'has_menu': bool(menu),
        })
    
    @http.route('/cantine/commander', type='json', auth='public', website=True, csrf=False)
    def commander_plat(self, entreprise_id, menu_id, plat_id, quantity=1, 
                       option_sans_sel=False, option_piment_apart=False, notes=''):
        """Créer une commande (AJAX)"""
        # Vérifier l'accès
        if not self._check_session_access(entreprise_id):
            return {
                'success': False,
                'message': 'Session expirée. Veuillez vous reconnecter.'
            }
        
        employee_name = request.session.get('cantine_employee_name')
        
        try:
            # Créer la commande
            commande = request.env['lagunes.commande'].sudo().create({
                'entreprise_id': entreprise_id,
                'employee_name': employee_name,
                'menu_id': menu_id,
                'plat_id': plat_id,
                'quantity': int(quantity),
                'option_sans_sel': bool(option_sans_sel),
                'option_piment_apart': bool(option_piment_apart),
                'notes': notes,
                'date': date.today(),
                'state': 'confirmed',
                'facturation_state': 'not_invoiced',
            })
            
            return {
                'success': True,
                'message': f'Commande confirmée ! Référence: {commande.reference}',
                'commande_id': commande.id,
                'reference': commande.reference,
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erreur lors de la commande: {str(e)}'
            }
    
    @http.route('/cantine/confirmation/<int:commande_id>', type='http', auth='public', website=True)
    def commande_confirmation(self, commande_id, **kwargs):
        """Page de confirmation de commande"""
        commande = request.env['lagunes.commande'].sudo().browse(commande_id)
        
        if not commande.exists():
            return request.render('lagunes_cantine.error_page', {
                'error_message': 'Commande non trouvée'
            })
        
        return request.render('lagunes_cantine.commande_confirmation', {
            'commande': commande,
        })
    
    @http.route('/cantine/mes_commandes', type='http', auth='public', website=True)
    def mes_commandes(self, **kwargs):
        """Voir l'historique des commandes de l'employé"""
        entreprise_id = request.session.get('cantine_entreprise_id')
        employee_name = request.session.get('cantine_employee_name')
        
        if not entreprise_id or not employee_name:
            return request.redirect('/cantine')
        
        # Récupérer les commandes de cet employé
        commandes = request.env['lagunes.commande'].sudo().search([
            ('entreprise_id', '=', entreprise_id),
            ('employee_name', '=', employee_name),
        ], order='date desc, create_date desc', limit=50)
        
        return request.render('lagunes_cantine.mes_commandes', {
            'commandes': commandes,
            'employee_name': employee_name,
        })
    
    @http.route('/cantine/logout', type='http', auth='public', website=True)
    def cantine_logout(self, **kwargs):
        """Déconnexion de la session cantine"""
        request.session.pop('cantine_entreprise_id', None)
        request.session.pop('cantine_employee_name', None)
        request.session.pop('cantine_access_time', None)
        
        return request.redirect('/cantine')
    
    def _check_session_access(self, entreprise_id):
        """Vérifier que la session est valide pour cette entreprise"""
        session_entreprise = request.session.get('cantine_entreprise_id')
        access_time = request.session.get('cantine_access_time')
        
        if not session_entreprise or not access_time:
            return False
        
        if session_entreprise != entreprise_id:
            return False
        
        # Vérifier que l'accès date d'aujourd'hui
        try:
            access_date = date.fromisoformat(access_time)
            if access_date != date.today():
                return False
        except ValueError:
            return False
        
        return True
