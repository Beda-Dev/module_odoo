# Guide de déploiement Odoo SH - Restaurant des Lagunes

## 🚀 Déploiement sur Odoo.sh

### Étape 1 : Préparation du repository Git

```bash
# Créer un repository Git
cd lagunes_cantine
git init
git add .
git commit -m "Initial commit: Module Lagunes Cantine v1.0.0"

# Créer un repository sur GitHub/GitLab
git remote add origin https://github.com/votre-organisation/lagunes_cantine.git
git push -u origin main
```

### Étape 2 : Configuration Odoo.sh

1. **Connexion à Odoo.sh**
   - Se connecter sur https://www.odoo.sh
   - Créer un nouveau projet ou utiliser un projet existant

2. **Lier le repository**
   - Dans Odoo.sh, aller dans **Settings**
   - Ajouter le repository Git
   - Configurer la branche principale (main/master)

3. **Structure du projet**
   ```
   votre-projet-odoo/
   ├── lagunes_cantine/          # Notre module
   │   ├── __init__.py
   │   ├── __manifest__.py
   │   ├── models/
   │   ├── controllers/
   │   ├── views/
   │   ├── security/
   │   ├── data/
   │   └── static/
   └── odoo.conf (optionnel)
   ```

### Étape 3 : Installation du module

1. **Dans Odoo.sh**
   - Aller dans l'environnement de production
   - Activer le mode développeur
   - Apps > Update Apps List
   - Rechercher "Restaurant des Lagunes"
   - Cliquer sur **Install**

2. **Via le shell (optionnel)**
   ```bash
   # Se connecter au shell Odoo.sh
   ./odoo-bin -d votre_base -u lagunes_cantine --stop-after-init
   ```

### Étape 4 : Configuration post-installation

#### 4.1 Créer les catégories de produits

Les catégories sont créées automatiquement lors de l'installation.

#### 4.2 Configurer les groupes d'utilisateurs

1. **Settings > Users & Companies > Users**
2. Assigner les groupes aux utilisateurs:
   - **Manager Cantine**: Pour les gestionnaires
   - **Cuisine**: Pour le personnel de cuisine
   - **Utilisateur**: Pour les employés (optionnel)

#### 4.3 Créer la première entreprise cliente

1. **Restaurant Lagunes > Cantine > Entreprises**
2. Nouveau partenaire:
   - Nom: Ex. "DIGIFAZ"
   - Cocher **Client Cantine**
   - Activer **Code requis** (optionnel)
   - Définir un **Code d'accès** unique

#### 4.4 Créer des plats

1. **Restaurant Lagunes > Cantine > Plats**
2. Créer des plats:
   - Riz sauce arachide
   - Poulet braisé
   - Poisson grillé
   - Attiéké poisson
   - etc.

#### 4.5 Créer des menus

1. **Restaurant Lagunes > Cantine > Menus**
2. Créer des menus pour chaque jour de la semaine

### Étape 5 : Configuration du site web

#### 5.1 Activer le module Website

Le module Website est déjà dans les dépendances et sera activé automatiquement.

#### 5.2 Personnaliser l'apparence (optionnel)

1. **Website > Configuration > Settings**
2. Choisir un thème
3. Personnaliser les couleurs

#### 5.3 Tester l'accès web

1. Ouvrir: `https://votre-domaine.odoo.com/cantine`
2. Sélectionner une entreprise
3. Entrer les identifiants
4. Vérifier l'affichage du menu

### Étape 6 : Tests fonctionnels

#### Test 1 : Accès entreprise

- [ ] Accès avec code correct
- [ ] Refus avec code incorrect
- [ ] Accès sans code si non requis

#### Test 2 : Affichage menu

- [ ] Menu du jour affiché
- [ ] Plats avec images
- [ ] Options disponibles
- [ ] Prix affichés

#### Test 3 : Commande

- [ ] Sélection d'un plat
- [ ] Options (sans sel, piment à part)
- [ ] Quantité
- [ ] Notes spéciales
- [ ] Validation de commande
- [ ] Page de confirmation

#### Test 4 : Cuisine

- [ ] Commandes visibles en kanban
- [ ] Changement de statut
- [ ] Options visibles
- [ ] Filtres fonctionnels

### Étape 7 : Sécurité

#### 7.1 HTTPS

Odoo.sh fournit automatiquement un certificat SSL.

#### 7.2 Backup

Odoo.sh effectue des sauvegardes automatiques.

#### 7.3 Règles de sécurité

- Les entreprises ne voient que leurs données
- Les employés n'ont pas accès au backend
- Les codes d'accès sont chiffrés

### Étape 8 : Monitoring

#### 8.1 Logs

- Consulter les logs dans Odoo.sh
- Vérifier les erreurs de commande

#### 8.2 Métriques

- Nombre de commandes par jour
- Entreprises actives
- Plats les plus commandés

### Étape 9 : Maintenance

#### 9.1 Mises à jour

```bash
# Pour déployer une mise à jour
git add .
git commit -m "Description de la mise à jour"
git push origin main
```

#### 9.2 Sauvegarde manuelle

1. **Odoo.sh > Backups**
2. Créer une sauvegarde manuelle avant une mise à jour importante

## 🔧 Dépannage

### Problème : Module non visible

**Solution**: 
- Mettre à jour la liste des apps
- Vérifier que le module est bien dans le repository
- Vérifier les dépendances

### Problème : Erreur lors de l'installation

**Solution**:
- Consulter les logs Odoo.sh
- Vérifier la syntaxe des fichiers XML
- Vérifier les dépendances Python

### Problème : Site web non accessible

**Solution**:
- Vérifier que le module Website est installé
- Vérifier la configuration du domaine
- Vérifier les contrôleurs

### Problème : Commandes non créées

**Solution**:
- Vérifier les droits d'accès public
- Consulter les logs JavaScript
- Vérifier la session utilisateur

## 📞 Support

En cas de problème persistant:
- Consulter la documentation Odoo.sh
- Contacter le support Odoo
- Vérifier les forums de la communauté

## ✅ Checklist de déploiement

- [ ] Repository Git créé et pushé
- [ ] Projet Odoo.sh configuré
- [ ] Module installé
- [ ] Utilisateurs créés et groupes assignés
- [ ] Première entreprise créée
- [ ] Plats créés
- [ ] Menus créés
- [ ] Site web testé
- [ ] Commande test effectuée
- [ ] Cuisine testée
- [ ] Sauvegardes configurées
- [ ] Documentation partagée avec l'équipe

---

**Date de déploiement**: _____________
**Déployé par**: _____________
**Version**: 18.0.1.0.0
