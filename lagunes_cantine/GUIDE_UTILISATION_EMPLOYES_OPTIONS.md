# Guide d'utilisation - Gestion des Employés et Options de Plats

## 📋 Vue d'ensemble rapide

Le module lagunes_cantine gère maintenant complètement :
- **Employés** : Enregistrements structurés par entreprise
- **Options paramétrables** : Personnalisation complète des plats
- **Commandes améliorées** : Lien direct aux employés

---

## 👥 GESTION DES EMPLOYÉS

### Créer un nouvel employé

**Chemin** : Restaurant Lagunes → Cantine → Employés → Créer

**Formulaire :**
```
Nom de l'employé *     Jean Dupont
Entreprise *           ACME Corp
Fonction               Directeur Général
Email                  jean.dupont@acme.com
Téléphone              +225 XX XX XX XX
Date d'embauche        01/02/2026
Actif                  ✓ Coché
Notes                  (optionnel)
```

### Actions disponibles

| Action | Accès | Résultat |
|--------|-------|----------|
| **Ajouter** | Bouton "Créer" | Nouvel enregistrement |
| **Modifier** | Clic sur le nom | Édition de la fiche |
| **Activer/Désactiver** | Bouton en haut de formulaire | Archive l'employé sans le supprimer |
| **Voir commandes** | Icône "Commandes" dans le formulaire | Liste des commandes de l'employé |
| **Supprimer** | Menu d'actions | Suppression définitive |

### Filtrage et recherche

**Filtres rapides :**
- 🟢 Actifs
- ⚪ Inactifs

**Grouper par :**
- Entreprise
- Fonction

**Rechercher :**
- Par nom d'employé
- Par entreprise
- Par fonction

### Exemple complet

```
Entreprise : Restaurant ABC
├─ Jean Dupont (Directeur) - jean.dupont@restaurant-abc.com
├─ Marie Martin (Responsable Cuisine) - marie@restaurant-abc.com
└─ Paul Legrand (Employé) - paul@restaurant-abc.com

Entreprise : École Nationale
├─ Thomas Baudet (Directeur)
├─ Sylvie Rousseau (Secrétaire)
└─ Jacques Lenoir (Économe) - jacques.lenoir@ecole.com
```

---

## 🍽️ GESTION DES OPTIONS DE PLATS

### Créer une nouvelle option

**Chemin** : Restaurant Lagunes → Cantine → Options de plats → Créer

**Formulaire :**
```
Nom de l'option *           Sans sel
Séquence                    10
Prix supplémentaire         0.0 FCFA
Option globale              ✓ (s'applique à tous les plats)
Actif                       ✓

Description :
"Le plat est préparé sans ajout de sel supplémentaire"

Plats concernés :
(si pas global : sélectionner les plats spécifiques)

Notes : (optionnel)
```

### Options prédéfinies (données de base)

| Option | Prix | Global | Description |
|--------|------|--------|------------|
| Sans sel | 0 FCFA | ✓ | Préparation sans sel |
| Piment à part | 0 FCFA | ✓ | Piment servi séparément |
| Sauce à côté | 0 FCFA | ✗ | Sauce dans petit récipient |
| Portion extra | 2500 FCFA | ✗ | +50% de portion |
| Légumes extras | 1000 FCFA | ✓ | Légumes frais supplémentaires |
| Sans huile | 0 FCFA | ✓ | Préparation allégée |

### Types d'options

**1. Options GLOBALES** (Global = Oui)
- S'appliquent automatiquement à **tous les plats**
- Exemples : Sans sel, Sans huile, Légumes extras
- Configuration simple, pas besoin de sélectionner les plats

**2. Options SPÉCIFIQUES** (Global = Non)
- S'appliquent seulement aux plats sélectionnés
- Exemples : Sauce à côté (sauce arachide), Portion extra
- Il faut cocher les plats concernés

### Cycle de vie d'une option

```
┌─────────────┐
│ Créer       │  Nouvelle option en "Actif"
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ En cours d'utilisation      │  ✓ Visible aux clients
│ (Actif = Oui)               │  ✓ Applicable aux commandes
└──────┬──────────────────────┘
       │
       ▼ (besoin d'arrêter mais garde historique)
┌──────────────────────────────┐
│ Désactiver (Actif = Non)     │  ✓ Conservée pour l'historique
│                              │  ✗ Invisible aux clients
└──────┬───────────────────────┘
       │
       ▼ (si vraiment inutile)
┌──────────────────────────────┐
│ Supprimer                    │  ✗ Effacée définitivement
│                              │  ⚠️ À faire avec prudence
└──────────────────────────────┘
```

### Exemple : Création d'une option pour "Riz spécial"

```
Nom : Riz aux œufs
Prix : 1500 FCFA (surcoût)
Global : Non
Plats concernés :
  ✓ Riz sauce arachide
  ✓ Riz clair sauce tomate
  ✓ Riz gras
(pas sélectionné : Riz au gris)

Description :
"Transformez votre riz en riz aux œufs frais brouillés (supplément)"
```

---

## 📝 UTILISATION DANS LES COMMANDES

### Passer une commande

**Chemin** : Restaurant Lagunes → Cantine → Toutes les commandes → Créer

**Formulaire :**
```
Entreprise *              ACME Corp
Employé *                 Jean Dupont          ← Sélectionné dans la liste des employés
Date                      02/02/2026

Menu *                    ACME - 02/02/2026
Plat *                    Riz sauce arachide
Quantité                  1
Prix unitaire (lu)        5000 FCFA
Prix total (calculé)      5000 FCFA

OPTIONS PERSONNALISÉES :
☑ Sans sel                  (gratuit)
☐ Piment à part            (gratuit)

Notes : Instructions spéciales...
```

### Filtrage des employés

**Avant** : Tous les employés visibles
**Après** : Seuls les employés de l'entreprise sélectionnée

```
Sélectionner : ACME Corp
↓
Employés disponibles :
- Jean Dupont
- Marie Martin
- Paul Legrand

(Les employés des autres entreprises n'apparaissent pas)
```

---

## 🔍 RECHERCHE ET RAPPORTS

### Voir les commandes d'un employé

**Depuis la fiche employé :**
1. Ouvrir l'employé (ex: Jean Dupont)
2. Cliquer sur le bouton "Commandes" (en haut à droite)
3. Liste des commandes de Jean Dupont affichée

**Détails visibles :**
- Référence de commande
- Date
- Plat commandé
- Options choisies
- État (brouillon, confirmée, en préparation, etc.)
- Prix

### Analyse des options les plus utilisées

```
Menu → Cantine → Options de plats
Filtrer par : Actives
Grouper par : Aucun

Vue : Toutes les options avec nombre de plats concernés
```

---

## ⚠️ BONNES PRATIQUES

### ✅ À FAIRE

1. **Avant le déploiement :**
   - Créer d'abord les employés de chaque entreprise
   - Configurer les options de plats disponibles
   - Lier les options aux plats appropriés
   - Tester une commande complète

2. **Maintenance régulière :**
   - Ajouter les nouveaux employés rapidement
   - Désactiver (pas supprimer) les employés partis
   - Ajouter des options selon les demandes clients
   - Archiver les options obsolètes

3. **Pour les rapports :**
   - Utiliser les filtres "Actif/Inactif"
   - Grouper par employé pour analyser
   - Exporter les données si nécessaire

### ❌ À ÉVITER

1. **Ne pas supprimer :**
   - Les employés ayant des commandes passées (les désactiver à la place)
   - Les options utilisées dans l'historique (les désactiver)

2. **Ne pas modifier :**
   - Les noms d'employés après plusieurs commandes (crée de la confusion)
   - Les prix des options rétroactivement (les anciennes commandes gardent leurs prix)

3. **Attention à :**
   - L'unicité des noms d'employés par entreprise
   - Le prix des options (vérifier avant d'appliquer)
   - Les options globales vs spécifiques (impact sur la facturation)

---

## 📊 CAS D'USAGE RÉELS

### Cas 1 : Nouvel employé arrive

```
Lundi matin :
1. Direction crée : "Sophie Bertrand" → Entreprise "FrancPlast"
2. Sophie reçoit un email avec code d'accès
3. Mardi : Sophie passe sa première commande
4. Cuisine prépare en voyant le ticket
```

### Cas 2 : Client demande une nouvelle option

```
Demande : "On voudrait du poulet moins épicé"
Solution :
1. Créer option "Peu épicé" (0 FCFA)
2. Lier à tous les plats de poulet
3. Activer immédiatement
4. Clients voient l'option dès aujourd'hui
```

### Cas 3 : Gestion du départ d'un employé

```
Vendredi : "Monsieur Dupont part à la retraite"
Action :
1. Ouvrir "Jean Dupont" (employé)
2. Cliquer "Activer/Désactiver" → devient inactif
3. Ses données restent (historique conservé)
4. Pas visible dans les nouvelles commandes
5. Pouvoir le réactiver si nécessaire
```

### Cas 4 : Option de Noël temporaire

```
Novembre :
1. Créer "Sauce spéciale Noël" (option payante : 500 FCFA)
2. Lier aux plats principaux
3. Activer

Janvier :
1. Aller à "Options" → trouver "Sauce spéciale Noël"
2. Cliquer "Activer/Désactiver" → Inactif
3. Les commandes existantes gardent l'option
4. Nouvelle commande ne peut pas la sélectionner
```

---

## 🎓 FORMATION RAPIDE - 5 MINUTES

### Objectif : Créer 1 employé et 1 option

**Minute 1-2 : Créer un employé**
```
Menu → Restaurant Lagunes → Cantine → Employés → Créer
Nom : Marie Dupont
Entreprise : (votre entreprise)
Cliquer : Enregistrer
```

**Minute 3 : Créer une option**
```
Menu → Restaurant Lagunes → Cantine → Options → Créer
Nom : Très piquant
Prix : 0
Global : Oui (pour tous les plats)
Cliquer : Enregistrer
```

**Minute 4-5 : Tester une commande**
```
Menu → Restaurant Lagunes → Cantine → Toutes les commandes → Créer
Entreprise : (votre entreprise)
Employé : Marie Dupont (elle apparaît !)
Menu : (sélectionner)
Plat : (sélectionner)
Options : ✓ Très piquant (elle apparaît !)
Cliquer : Enregistrer
```

**Résultat :** ✅ Fonctionnel !

---

## 📞 SUPPORT ET DÉPANNAGE

### Problème : L'employé ne s'affiche pas

**Solutions :**
1. Vérifier que l'employé est **Actif** (checkbox coché)
2. Vérifier qu'il appartient à la bonne **Entreprise**
3. Recharger la page (F5)
4. Vérifier les droits d'accès

### Problème : L'option ne s'affiche pas

**Solutions :**
1. Vérifier que l'option est **Actif**
2. Si l'option n'est **pas Global** : vérifier que le plat est sélectionné
3. Recharger la page

### Problème : Impossible de supprimer un employé

**Raison probable :** L'employé a des commandes liées

**Solution :** 
- Cliquer sur "Activer/Désactiver" pour le désactiver au lieu de le supprimer
- Cela archive l'employé et préserve l'historique

---

**Dernière mise à jour :** 2 février 2026  
**Pour plus d'info :** Voir MISE_A_JOUR_FEVRIER_2026.md

