# Mise à jour du module lagunes_cantine - Février 2026

## Résumé des améliorations

Le module **lagunes_cantine** a été considérablement enrichi avec de nouvelles fonctionnalités pour mieux gérer les opérations de cantine. Voici ce qui a été ajouté :

## 1. ✅ Gestion des Employés (Nouveau modèle)

### Avant :
- Les employés n'étaient représentés que par une simple chaîne de caractères (`employee_name`) dans les commandes
- Pas de gestion structurée des employés

### Après :
- **Nouveau modèle** : `lagunes.employee`
- Chaque employé est maintenant un enregistrement complet avec :
  - 👤 **Nom** de l'employé
  - 🏢 **Entreprise** (lien vers res.partner)
  - 📧 **Email** professionnel
  - 📱 **Téléphone**
  - 👔 **Fonction/Poste**
  - 📅 **Date d'embauche**
  - ✔️ **État** (Actif/Inactif pour archivage sans suppression)
  - 📋 **Notes** supplémentaires
  - 📊 **Compteur de commandes** (lié aux commandes passées)

### Accès :
- Menu : **Cantine → Employés**
- Actions : Ajouter, modifier, désactiver, voir les commandes d'un employé
- Gestion complète avec recherche, filtrage et groupage

---

## 2. ✅ Gestion des Options de Plats Paramétrables (Nouveau modèle)

### Avant :
- Options limitées et codées en dur (seulement "Sans sel" et "Piment à part")
- Impossible d'ajouter d'autres options personnalisées

### Après :
- **Nouveau modèle** : `lagunes.plat.option`
- Options complètement paramétrables avec :
  - 📝 **Nom** de l'option (ex: "Sans sel", "Piment à part", "Sauce à côté", etc.)
  - 🔄 **Ordre d'affichage** (Séquence)
  - 💬 **Description** détaillée
  - 💰 **Prix supplémentaire** (gratuit ou payant)
  - 🌍 **Portée** : Option globale (tous les plats) ou spécifique à certains plats
  - ✔️ **État** (Actif/Inactif)
  - 📋 **Notes**

### Fonctionnalités :
- ➕ **Ajouter** : Créer des options nouvelles illimitées
- ✏️ **Modifier** : Changer les paramètres d'une option existante
- 🔇 **Désactiver** : Archiver une option sans la supprimer (mode inactif)
- 🗑️ **Supprimer** : Suppression complète si nécessaire
- 🔗 **Liées aux plats** : Chaque option peut s'appliquer à certains plats ou tous

### Accès :
- Menu : **Cantine → Options de plats**
- Vue Liste avec ordonnancement
- Vue Formulaire pour édition
- Filtres : Actives/Inactives, globales, payantes

---

## 3. ✅ Mise à jour des Commandes

### Améliorations :
- Les commandes utilisent maintenant `employee_id` (lien vers `lagunes.employee`) au lieu d'une simple chaîne
- Le champ `employee_name` est devenu un champ calculé mémorisé depuis l'employé
- Filtrage automatique des employés par entreprise sélectionnée
- Meilleure traçabilité des commandes par employé

### Vue améliorée :
- Affichage propre de l'employé comme un lien
- Historique complet des commandes par employé

---

## 4. ✅ Amélioration de la structure des Plats

### Nouvelle relation :
- Les plats sont maintenant directement liés aux options via `option_ids`
- Relation Many2many : un plat peut avoir plusieurs options, une option s'applique à plusieurs plats
- Table de liaison : `lagunes_plat_option_rel`

### Vues mises à jour :
- Onglet "Options disponibles" dans le formulaire des plats
- Sélection facile des options avec widget `many2many_tags`

---

## 5. 🔐 Sécurité mise à jour

### Accès contrôlé pour les nouveaux modèles :
- ✅ `lagunes_employee` : Lecture/Écriture/Création pour managers
- ✅ `lagunes_plat_option` : Lecture/Écriture/Création pour managers

### Groupes d'accès :
- 👤 **group_lagunes_user** : Accès en lecture seule
- 👨‍💼 **group_lagunes_manager** : Accès complet (CRUD)
- 👨‍🍳 **group_lagunes_cuisine** : Accès limité (consultation et modification de l'état)

---

## 6. 📁 Structure des menus mise à jour

Les menus principales ont été réorganisés :

```
Restaurant Lagunes
├── Cantine
│   ├── Entreprises
│   ├── Menus
│   ├── Plats
│   ├── Options de plats ⭐ NOUVEAU
│   ├── Employés ⭐ NOUVEAU
│   └── Toutes les commandes
└── Cuisine
    └── Commandes du jour
```

---

## 7. 📊 Statistiques et suivi

### Nouvelles fonctionnalités de suivi :
- 📈 Compteur de commandes par employé
- 📍 Localisation rapide des commandes d'un employé via bouton d'action
- 🔍 Historique complet traçable

---

## 8. 🎯 Cas d'utilisation

### Gestion des employés :
```
Direction → Ajouter employé "Jean Dupont" → Entreprise "ACME Corp"
Jean Dupont passe commande via le site → Commande liée à son profil
Suivi des habitudes de commande par employé
```

### Gestion des options :
```
Direction crée option "Sauce piquante" → Applicable aux plats "Riz"
Option coûte 500 FCFA supplémentaires
Client choisit l'option lors de la commande
Facturation correcte avec surcoût
```

---

## 9. 🚀 Installation / Mise à jour

### Étapes pour mettre à jour le module :

1. **Arrêter Odoo**
2. **Mettre à jour la base de données** :
   ```bash
   python -m odoo -d restaurent_des_lagunes -i lagunes_cantine --update-all
   ```
3. **Redémarrer Odoo**
4. **Vérifier les menus** : Restaurant Lagunes → Cantine

### Données existantes :
- ✅ Migrations automatiques si nécessaire
- ✅ Les commandes existantes restent intactes
- ✅ Possibilité de lier les anciennes commandes aux employés

---

## 10. 📝 Fichiers modifiés/créés

### Modèles (models) :
- ✅ **lagunes_employee.py** (NOUVEAU)
- ✅ **lagunes_plat_option.py** (NOUVEAU)
- ✅ **lagunes_commande.py** (MODIFIÉ - employee_id)
- ✅ **lagunes_plat.py** (MODIFIÉ - option_ids)
- ✅ **__init__.py** (MODIFIÉ - imports)

### Vues (views) :
- ✅ **lagunes_employee_views.xml** (NOUVEAU)
- ✅ **lagunes_plat_option_views.xml** (NOUVEAU)
- ✅ **lagunes_menus.xml** (MODIFIÉ - nouveaux menus)
- ✅ **lagunes_commande_views.xml** (MODIFIÉ - employee_id)

### Sécurité (security) :
- ✅ **ir.model.access.csv** (MODIFIÉ - nouveaux modèles)

---

## 11. ⚠️ Notes importantes

### Points d'attention :
1. **Migration des employés** : Les données `employee_name` doivent être migrées vers le modèle `lagunes_employee`
2. **Options par plat** : À configurer manuellement dans chaque plat via l'onglet "Options"
3. **Backward compatibility** : Les anciens champs `option_sans_sel` et `option_piment_apart` restent pour compatibilité

### Recommandations :
- 📋 Créer d'abord les employés dans chaque entreprise
- ⚙️ Configurer les options de plats disponibles
- 🔗 Lier les options aux plats appropriés
- ✔️ Tester une commande complète

---

## 12. 🔮 Évolutions futures possibles

- 📊 Dashboard avec statistiques d'utilisation
- 🔔 Notifications pour les employés
- 📈 Rapports d'utilisation par employé/entreprise
- 🎁 Système de loyalité/réductions
- 🌐 Amélioration du portail web

---

**Module mis à jour le :** 2 février 2026  
**Version :** 18.0.1.1.0  
**Auteur :** Restaurant des Lagunes

