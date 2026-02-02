"""
Migrations possibles pour les données existantes
Fichier de recommandations et scripts d'assistance
"""

# MIGRATION DES EMPLOYÉS EXISTANTS
# ================================

# Si vous avez des données anciennes dans employee_name (texte libre),
# vous pouvez les migrer vers le nouveau modèle lagunes.employee

# Approche manuelle (petite quantité):
# 1. Lister toutes les commandes : Cantine → Toutes les commandes
# 2. Noter les noms d'employés uniques
# 3. Pour chaque nom : Cantine → Employés → Créer
# 4. Éditer les commandes pour lier au nouvel employé

# Approche script (pour gros volume):
# Contacter l'administrateur Odoo pour exécuter :

"""
from odoo import api, models

@api.model
def migrate_employee_names():
    # Récupérer toutes les commandes avec employee_name
    commandes = self.env['lagunes.commande'].search([])
    
    for commande in commandes:
        if commande.employee_name and not commande.employee_id:
            # Chercher l'employé existant ou en créer un
            employee = self.env['lagunes.employee'].search([
                ('name', '=', commande.employee_name),
                ('entreprise_id', '=', commande.entreprise_id.id)
            ])
            
            if not employee:
                # Créer un nouvel employé
                employee = self.env['lagunes.employee'].create({
                    'name': commande.employee_name,
                    'entreprise_id': commande.entreprise_id.id
                })
            
            # Lier à la commande
            commande.employee_id = employee.id
    
    return True
"""

# DONNÉES INITIALES À CRÉER
# =========================

# 1. OPTIONS PRÉDÉFINIES (déjà créées dans plat_option_data.xml):
"""
- Sans sel (gratuit, global)
- Piment à part (gratuit, global)
- Sauce à côté (gratuit, spécifique)
- Portion supplémentaire (2500 FCFA, spécifique)
- Légumes supplémentaires (1000 FCFA, global)
- Sans huile/Allégé (gratuit, global)
"""

# 2. LIER LES OPTIONS AUX PLATS:
# Pour chaque plat, aller dans "Options disponibles" et sélectionner :
"""
Riz sauce arachide :
  - Sans sel
  - Piment à part
  - Sauce à côté
  - Portion supplémentaire
  - Légumes supplémentaires
  - Sans huile

Riz gras :
  - Sans sel
  - Piment à part
  - Légumes supplémentaires
  - Sans huile

Poulet :
  - Sans sel
  - Piment à part
  - Portion supplémentaire
  - Légumes supplémentaires
  - Sans huile

etc...
"""

# 3. CRÉER LES EMPLOYÉS:
# Menu : Cantine → Employés → Créer
"""
Pour chaque entreprise cliente :

Nom : [Prénom Nom]
Entreprise : [Entreprise]
Fonction : [Rôle - optionnel]
Email : [Email pro - optionnel]
Téléphone : [Téléphone - optionnel]
Date d'embauche : [Date actuelle ou contrat]
Actif : ✓ Coché
"""

# BACKWARD COMPATIBILITY
# ======================

# Les anciens champs sont conservés :
# - lagunes.commande.option_sans_sel (booléen)
# - lagunes.commande.option_piment_apart (booléen)

# Ces champs peuvent coexister avec le nouveau système:
# - Si option_sans_sel = True, cela signifie "Sans sel" activé
# - Les deux systèmes fonctionnent en parallèle

# RECOMMANDATION : Progressivement, remplacer les vieux booléens 
# par le système many2many option_ids (futur upgrade)

# TABLEAUX DE CONVERSION
# ======================

"""
ANCIEN SYSTÈME           ->  NOUVEAU SYSTÈME
option_sans_sel=True     ->  Sans sel option liée
option_piment_apart=True ->  Piment à part option liée
(aucune option)          ->  (aucune option liée)
"""

# CHECKLIST DE MIGRATION
# ======================

print("""
CHECKLIST DE MIGRATION - lagunes_cantine v18.0.1.1.0

[  ] 1. Lire MISE_A_JOUR_FEVRIER_2026.md
[  ] 2. Lire GUIDE_UTILISATION_EMPLOYES_OPTIONS.md
[  ] 3. Arrêter Odoo
[  ] 4. Mettre à jour le module (python -m odoo ... -i lagunes_cantine --update-all)
[  ] 5. Redémarrer Odoo
[  ] 6. Vérifier les nouveaux menus (Restaurant Lagunes → Cantine)
[  ] 7. Vérifier les 6 options prédéfinies créées
[  ] 8. Créer les employés de chaque entreprise
[  ] 9. Lier les options aux plats appropriés
[  ] 10. Tester une nouvelle commande (employee_id doit fonctionner)
[  ] 11. Vérifier l'historique commandes par employé
[  ] 12. Former le personnel

MIGRATION DES DONNÉES EXISTANTES (si données anciennes):
[  ] 13. Lister les noms d'employés existants
[  ] 14. Créer enregistrements lagunes.employee correspondants
[  ] 15. Lier les anciennes commandes (ou laisser en legacy)
[  ] 16. Archiver les employés partis (toggle Actif)

TESTS FINAUX:
[  ] 17. Test créer employé
[  ] 18. Test créer option
[  ] 19. Test passer commande avec nouvel employé
[  ] 20. Test filtrage employés par entreprise
[  ] 21. Test voir commandes de l'employé
[  ] 22. Test désactiver/activer option
[  ] 23. Test kanban vue avec badges options
[  ] 24. Production GO!
""")

# CONTACT SUPPORT
# ===============
print("""
EN CAS DE PROBLÈME:

1. Options ne s'affichent pas ?
   → Vérifier que l'option est "Actif"
   → Vérifier que le plat est sélectionné (si option non-globale)
   → Recharger la page

2. Employé ne s'affiche pas en commande ?
   → Vérifier que l'employé est "Actif"
   → Vérifier qu'il appartient à la bonne "Entreprise"
   → Sélectionner d'abord l'entreprise
   → Recharger

3. Impossible de supprimer employé ?
   → C'est normal ! Click "Activer/Désactiver" pour archiver
   → Cela préserve l'historique des commandes

4. Anciennes commandes sans employee_id ?
   → Normal, elles sont en legacy
   → Vous pouvez les éditer manuellement si nécessaire
   → Ou les laisser comme sont (compatible)

5. Script de migration ne fonctionne pas ?
   → Contacter administrateur Odoo
   → Il exécutera depuis le terminal Odoo
""")

# SCRIPTS DE VERIFICATION
# =======================

"""
Script SQL pour vérifier les données (accès base de données):

-- Vérifier les employés créés
SELECT COUNT(*) FROM lagunes_employee;
SELECT name, entreprise_id, active FROM lagunes_employee LIMIT 10;

-- Vérifier les options créées
SELECT COUNT(*) FROM lagunes_plat_option;
SELECT name, prix_supplementaire, is_global, active FROM lagunes_plat_option;

-- Vérifier les liens plat-option
SELECT COUNT(*) FROM lagunes_plat_option_rel;
SELECT plat_id, option_id FROM lagunes_plat_option_rel LIMIT 10;

-- Vérifier les commandes avec employee
SELECT COUNT(*) FROM lagunes_commande WHERE employee_id IS NOT NULL;
SELECT reference, employee_id, employee_name FROM lagunes_commande LIMIT 10;
"""

# DATES IMPORTANTES
# =================

print("""
TIMELINE D'IMPLÉMENTATION:

Juin 2025 : Conception du système
Août 2025 : Développement modèles
Janvier 2026 : Tests finaux
2 février 2026 : Livraison v18.0.1.1.0
""")

# CONTACTS DÉVELOPPEUR
# ====================

print("""
Restaurant des Lagunes
Module de cantine d'entreprise

Développeur : Équipe Lagunes
Date : 2 février 2026
Version : 18.0.1.1.0

Support technique : À définir
Email support : À définir
Hotline : À définir
""")

# FIN DU FICHIER DE MIGRATION
