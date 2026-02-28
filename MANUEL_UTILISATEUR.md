# Manuel Utilisateur - Recherche de Mémoires Techniques

## Accès

**URL :** https://memoires-tech-index.streamlit.app/

Au lancement, choisissez votre nom dans le sélecteur "Qui êtes-vous ?" puis validez. Votre nom apparaît dans la barre latérale gauche avec un bouton "Se déconnecter".

---

## Onglet Recherche

C'est l'onglet principal. Il permet de trouver les mémoires techniques les plus proches d'un projet donné.

**Comment faire :**
1. Décrivez votre projet dans la zone de texte (mots-clés, type d'ouvrage, techniques, matériaux...)
2. Cliquez sur **Rechercher**
3. Les résultats s'affichent par ordre de pertinence (score de similarité)

**Pour chaque résultat :**
- Le nom du document et son score de similarité
- Les mots-clés et thèmes en commun avec votre recherche
- Un lien vers le document sur le Drive (cliquable)
- Un aperçu des illustrations (jusqu'à 3 miniatures)
- Un bouton **"Voir détails complets"** pour afficher le résumé intégral, les caractéristiques (matériaux, méthodologie, équipements...), les points distinctifs et toutes les illustrations

---

## Onglet Tableau de bord

Vue d'ensemble de l'état de la base documentaire.

**Métriques affichées :**
- Nombre total de documents indexés
- Nombre de documents non validés / validés / enrichis

**Activité récente :**
- Les 10 derniers documents indexés, avec le nom de l'utilisateur qui les a indexés et la date

**Verrous :**
- Indique si quelqu'un est en train d'indexer (pour éviter les conflits)

---

## Onglet Enrichissement

Permet d'améliorer manuellement la fiche d'un document déjà indexé.

### Etape 1 : Sélectionner un document
- Utilisez le champ de recherche pour filtrer par nom
- Sélectionnez le document dans la liste déroulante

### Etape 2 : Renommer (optionnel)
- Modifiez le nom du fichier si nécessaire (le fichier est aussi renommé sur le Drive)

### Etat actuel
- Dépliez "Etat actuel de l'indexation" pour voir le résumé, les mots-clés, thèmes, caractéristiques et illustrations actuels

### Etape 3 : Modifier

Trois sous-onglets sont disponibles :

**Enrichissement général :**
- Décrivez vos modifications en langage naturel
- Exemple : *"Ajoute 'béton précontraint' dans les matériaux et retire 'acier'"*

**Illustrations (Visuel) :**
- Visualisez les illustrations existantes (avec possibilité de supprimer)
- Ajoutez une nouvelle illustration en collant depuis le presse-papiers ou en uploadant un fichier
- Renseignez la catégorie, le type, une description et des mots-clés techniques

**Illustrations (Langage naturel) :**
- Décrivez une illustration à ajouter en texte libre
- Exemple : *"Ajoute une illustration : schéma de carottage vertical, catégorie Investigation"*

### Etape 4 : Interpréter et appliquer
- Cliquez sur **Interpréter** pour voir les modifications détectées
- Vérifiez chaque modification proposée (ajout, retrait, modification)
- Cliquez sur **Valider et appliquer** pour enregistrer, ou **Annuler**

---

## Onglet Indexation

Permet d'ajouter de nouveaux documents à la base depuis le Drive partagé.

**Fonctionnement :**
1. L'onglet liste automatiquement les documents présents dans le dossier Drive qui ne sont pas encore indexés
2. Cochez les documents à indexer (ou "Tout sélectionner")
3. Cliquez sur **Indexer N document(s)**
4. Pour chaque document, l'application :
   - Télécharge le fichier depuis le Drive
   - Extrait le texte
   - Génère automatiquement un résumé, des mots-clés et des thèmes via l'IA
5. Le résultat de l'indexation s'affiche immédiatement (résumé, mots-clés, thèmes)

**Option :** Cochez "Forcer la réindexation" pour réindexer des documents déjà présents dans la base.

**Note :** Si quelqu'un est déjà en train d'indexer, un message de verrouillage s'affiche.

---

## Onglet Admin (David uniquement)

Protégé par mot de passe. Contient 4 sous-sections :

### Validation des documents
- Liste les documents indexés mais pas encore validés
- Pour chaque document : résumé, mots-clés, thèmes, lien vers le fichier
- Actions disponibles :
  - **Valider** : marque le document comme vérifié
  - **Valider et enrichir** : valide puis redirige vers l'enrichissement
  - **Ré-indexer** : relance l'indexation si le résultat est insatisfaisant
- **Tout valider** : bouton de validation en masse

### Cycle d'apprentissage
- Lance une analyse des enrichissements manuels effectués par les utilisateurs
- L'IA détecte des patterns récurrents (ex : "les utilisateurs ajoutent systématiquement le type de marché")
- Génère des propositions d'amélioration du prompt d'indexation

### Améliorations IA
- Affiche les améliorations proposées par le cycle d'apprentissage
- Pour chaque amélioration : priorité, champ concerné, suggestion, exemple de prompt
- Actions : **Valider** ou **Rejeter** chaque proposition
- **Appliquer** : intègre les améliorations validées dans le système

### Règles apprises
- Liste les règles qui ont été validées et intégrées
- Ces règles sont automatiquement utilisées lors des futures indexations pour améliorer la qualité des résumés générés

---

## Cycle de vie d'un document

```
Nouveau document sur le Drive
        |
        v
   [Indexation]  -->  statut : "indexé non validé"
        |
        v
   [Validation]  -->  statut : "validé"  (Admin)
        |
        v
  [Enrichissement] --> statut : "enrichi"
```

Les documents sont consultables par la recherche quel que soit leur statut.
