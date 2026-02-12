# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from datetime import date, timedelta
import json


class LagunesCantineController(http.Controller):
    
    @http.route('/', type='http', auth='public', website=True)
    def home_redirect(self, **kwargs):
        """Rediriger la racine vers la cantine"""
        return request.redirect('/cantine')
    
    @http.route('/cantine', type='http', auth='public', website=True)
    def cantine_home(self, **kwargs):
        """Page d'accueil de la cantine - Formulaire d'accès par code"""
        # Si déjà connecté, rediriger vers le menu
        if request.session.get('cantine_entreprise_id'):
            entreprise_id = request.session.get('cantine_entreprise_id')
            return request.redirect(f'/cantine/menu/{entreprise_id}')
            
        return request.render('lagunes_cantine.cantine_home')
    
    @http.route('/cantine/verify_access', type='json', auth='public', website=True)
    def verify_access(self, access_code=None):
        """Vérifier l'accès avec le code entreprise (AJAX)"""
        result = request.env['res.partner'].sudo().verify_cantine_access(
            access_code=access_code
        )
        
        if result.get('success'):
            # Stocker les infos dans la session
            request.session['cantine_entreprise_id'] = result['entreprise_id']
            request.session['cantine_access_code'] = access_code
            request.session['cantine_access_time'] = str(date.today())
        
        return result
    
    @http.route('/cantine/menu/<int:entreprise_id>', type='http', auth='public', website=True)
    def cantine_menu(self, entreprise_id, **kwargs):
        """Afficher le menu d'une entreprise (Aujourd'hui uniquement)"""
        # Vérifier l'accès via la session
        if not self._check_session_access(entreprise_id):
            return request.redirect('/cantine')
        
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        
        # Toujours forcer la date à aujourd'hui
        target_date = date.today()
        
        # Récupérer le menu actif
        menu = request.env['lagunes.menu'].sudo().get_menu_for_entreprise(
            entreprise_id=entreprise_id,
            target_date=target_date
        )
        
        # Vérifier si la limite de commandes est atteinte
        max_orders = entreprise.max_orders_per_day
        orders_today = 0
        limit_reached = False
        
        if max_orders > 0:
            orders_today = request.env['lagunes.commande'].sudo().search_count([
                ('entreprise_id', '=', entreprise_id),
                ('date', '=', target_date),
                ('state', '!=', 'cancelled')
            ])
            limit_reached = (orders_today >= max_orders)
        
        # Formater la date en français
        days_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        months_fr = [
            'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
        ]
        
        date_fr = f"{days_fr[target_date.weekday()]} {target_date.day} {months_fr[target_date.month - 1]} {target_date.year}"
        
        return request.render('lagunes_cantine.cantine_menu', {
            'entreprise': entreprise,
            'menu': menu,
            'target_date': target_date,
            'date_fr': date_fr,
            'has_menu': bool(menu),
            'limit_reached': limit_reached,
            'orders_today': orders_today,
            'max_orders': max_orders,
        })
    
    @http.route('/cantine/commander', type='json', auth='public', website=True, csrf=False)
    def commander_plat(self, entreprise_id, menu_id, plat_id, quantity=1, 
                       option_ids=None, notes='', employee_name=None):
        """Créer une commande (AJAX)"""
        # Vérifier l'accès
        if not self._check_session_access(entreprise_id):
            return {
                'success': False,
                'message': 'Session expirée. Veuillez vous reconnecter.'
            }
        
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        
        # Force quantité à 1
        quantity = 1
        
        # Vérifier si la personne a déjà commandé dans cette session
        session_key = f'cantine_commanded_{entreprise_id}'
        if request.session.get(session_key):
            return {
                'success': False,
                'message': 'Vous avez déjà passé une commande dans cette session. Une seule commande est autorisée par session.'
            }
        
        # Vérifier limite de commandes
        if entreprise.max_orders_per_day > 0:
            count = request.env['lagunes.commande'].sudo().search_count([
                ('entreprise_id', '=', entreprise_id),
                ('date', '=', date.today()),
                ('state', '!=', 'cancelled')
            ])
            
            if count >= entreprise.max_orders_per_day:
                return {
                    'success': False,
                    'message': f'Limite de {entreprise.max_orders_per_day} commande(s) par jour atteinte.'
                }
        
        try:
            # Créer la commande
            vals = {
                'entreprise_id': entreprise_id,
                'menu_id': menu_id,
                'plat_id': plat_id,
                'quantity': quantity,
                'notes': notes,
                'date': date.today(),
                'state': 'confirmed',
                'facturation_state': 'not_invoiced',
                'employee_name': (employee_name or '').strip(),
            }
            
            if option_ids:
                vals['option_ids'] = [(6, 0, [int(oid) for oid in option_ids])]
                
            commande = request.env['lagunes.commande'].sudo().create(vals)
            
            # Marquer la session comme ayant commandé
            session_key = f'cantine_commanded_{entreprise_id}'
            request.session[session_key] = True
            
            return {
                'success': True,
                'message': f'Commande confirmée ! Référence: {commande.reference}',
                'commande_id': commande.id,
                'reference': commande.reference,
                'employee_name': commande.employee_name,
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
        """Voir l'historique des commandes de l'entreprise"""
        entreprise_id = request.session.get('cantine_entreprise_id')
        
        if not entreprise_id:
            return request.redirect('/cantine')
        
        entreprise = request.env['res.partner'].sudo().browse(entreprise_id)
        
        # Récupérer les commandes de cette entreprise
        commandes = request.env['lagunes.commande'].sudo().search([
            ('entreprise_id', '=', entreprise_id),
        ], order='date desc, create_date desc', limit=100)
        
        return request.render('lagunes_cantine.mes_commandes', {
            'commandes': commandes,
            'entreprise': entreprise,
        })
    
    @http.route('/cantine/logout', type='http', auth='public', website=True)
    def cantine_logout(self, **kwargs):
        """Déconnexion de la session cantine"""
        entreprise_id = request.session.get('cantine_entreprise_id')
        
        # Nettoyer toutes les clés de session
        request.session.pop('cantine_entreprise_id', None)
        request.session.pop('cantine_access_code', None)
        request.session.pop('cantine_access_time', None)
        
        # Nettoyer aussi la clé de commande si elle existe
        if entreprise_id:
            session_key = f'cantine_commanded_{entreprise_id}'
            request.session.pop(session_key, None)
        
        return request.redirect('/cantine')
    
    def _check_session_access(self, entreprise_id):
        """Vérifier que la session est valide pour cette entreprise"""
        session_entreprise = request.session.get('cantine_entreprise_id')
        access_code = request.session.get('cantine_access_code')
        access_time = request.session.get('cantine_access_time')
        
        if not session_entreprise or not access_code or not access_time:
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