# Module Odoo 18 - Restaurant des Lagunes (Cantine d'entreprise)

## 📋 Description

Module de gestion de cantine d'entreprise pour Restaurant des Lagunes.

### Phase 1 - Fonctionnalités

- ✅ Gestion des entreprises clientes (type Cantine)
- ✅ Gestion des menus par entreprise et par jour
- ✅ Gestion des plats (produits Odoo)
- ✅ Commandes quotidiennes en ligne
- ✅ Site web dédié avec accès sécurisé
- ✅ Options de plat (sans sel, piment à part)
- ✅ Accès par code entreprise (optionnel)
- ✅ Sans paiement en ligne
- ✅ Sans TVA (régime micro-entreprise)

## 🚀 Installation

### Prérequis

- Odoo 18 (Odoo SH)
- Modules dépendants:
  - `base`
  - `product`
  - `sale_management`
  - `website`
  - `website_sale`

### Étapes d'installation

1. Copier le dossier `lagunes_cantine` dans le répertoire `addons` d'Odoo
2. Mettre à jour la liste des applications
3. Installer le module "Restaurant des Lagunes - Cantine"

## 📖 Guide d'utilisation

### Configuration initiale

#### 1. Créer une entreprise cliente

1. Aller dans **Restaurant Lagunes > Cantine > Entreprises**
2. Créer un nouveau partenaire
3. Cocher **Client Cantine**
4. Optionnel: Activer **Code requis** et définir un **Code d'accès**

#### 2. Créer des plats

1. Aller dans **Restaurant Lagunes > Cantine > Plats**
2. Créer un nouveau plat avec:
   - Nom du plat
   - Prix unitaire (sans TVA)
   - Image (optionnel)
   - Options disponibles (sans sel, piment à part)

#### 3. Créer des menus

1. Aller dans **Restaurant Lagunes > Cantine > Menus**
2. Créer un nouveau menu:
   - Sélectionner l'entreprise
   - Choisir la date
   - Ajouter les plats disponibles

### Utilisation côté employés

#### Accès au site web

1. L'entreprise partage le lien: `/cantine/access/[ID_ENTREPRISE]`
2. L'employé entre son nom
3. Si requis, l'employé entre le code d'accès
4. L'employé accède au menu du jour

#### Passer une commande

1. Consulter le menu du jour
2. Sélectionner un plat
3. Choisir les options (sans sel, piment à part)
4. Indiquer la quantité
5. Ajouter des notes spéciales (optionnel)
6. Cliquer sur **Commander**
7. Une confirmation s'affiche avec la référence

### Gestion côté cuisine

1. Aller dans **Restaurant Lagunes > Cuisine > Commandes du jour**
2. Vue Kanban organisée par statut:
   - Confirmée
   - En préparation
   - Prêt
   - Livré
3. Les options (sans sel, piment à part) sont visibles sur chaque carte

## 🔐 Sécurité et droits d'accès

### Groupes d'utilisateurs

- **Utilisateur**: Lecture des menus et commandes
- **Cuisine**: Lecture/écriture des commandes
- **Manager**: Accès complet

### Accès web public

- Les employés accèdent au site sans compte Odoo
- L'accès est contrôlé par:
  - Session navigateur
  - Code entreprise (optionnel)
  - Nom de l'employé

## 📊 Modèles de données

### res.partner (étendu)

- `is_cantine_client`: Client de la cantine
- `cantine_code_required`: Code d'accès requis
- `cantine_access_code`: Code d'accès unique

### lagunes.menu

- Entreprise
- Date
- Liste de plats
- Statut actif/inactif

### lagunes.plat

- Nom du plat
- Produit Odoo associé
- Prix unitaire
- Options disponibles
- Image

### lagunes.commande

- Référence unique
- Entreprise
- Nom de l'employé
- Menu et plat
- Quantité
- Options sélectionnées
- Statut (brouillon, confirmé, en préparation, prêt, livré)
- État de facturation (non facturée, à facturer, facturée)

## 🎨 Personnalisation

### CSS personnalisé

Le fichier `/static/src/css/lagunes_frontend.css` contient les styles du site web.

### JavaScript

Le fichier `/static/src/js/lagunes_commande.js` gère les interactions de commande.

## 📝 Facturation (Phase future)

La facturation mensuelle sera implémentée dans une phase ultérieure.

Chaque commande peut être convertie en commande de vente via le bouton **Créer facture**.

## ⚠️ Règles métier importantes

- **TVA**: Aucune TVA appliquée (régime micro-entreprise)
- **Paiement**: Aucun paiement en ligne dans cette phase
- **Unicité**: Un seul menu par entreprise et par jour
- **Facturation**: Les commandes sont créées en statut "Non facturée"

## 🆘 Support

Pour toute question ou problème:
- Contacter l'équipe Restaurant des Lagunes
- Vérifier les logs Odoo en cas d'erreur

## 📜 Licence

LGPL-3

## 👥 Auteur

Restaurant des Lagunes

---

**Version**: 18.0.1.0.0  
**Date**: 2025
