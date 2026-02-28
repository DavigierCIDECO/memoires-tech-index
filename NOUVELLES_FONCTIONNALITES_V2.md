# Nouvelles Fonctionnalités - Version 2.0

## 🎉 Vue d'ensemble

Trois nouvelles fonctionnalités majeures ont été ajoutées au système d'indexation :

1. **Pondération temporelle** : Les MTs récents sont favorisés dans les résultats
2. **Enrichissement manuel intelligent** : Corrigez l'indexation en langage naturel
3. **Apprentissage automatique** : Le système s'améliore avec vos enrichissements

---

## 1️⃣ Pondération Temporelle

### Fonctionnement

Les documents sont maintenant scorés avec un bonus basé sur leur date d'indexation :

- **< 3 mois** : +15% de bonus sur le score
- **3-6 mois** : +10% de bonus
- **6-12 mois** : +5% de bonus
- **> 12 mois** : Pas de bonus

### Configuration

Modifiez les paramètres dans `config.py` :

```python
TEMPORAL_WEIGHTING_ENABLED = True  # Activer/désactiver
TEMPORAL_BONUS_RECENT = 0.15       # Bonus pour < 3 mois
TEMPORAL_BONUS_MEDIUM = 0.10       # Bonus pour 3-6 mois
TEMPORAL_BONUS_OLD = 0.05          # Bonus pour 6-12 mois
```

### Visualisation

Le bonus temporel apparaît dans les résultats de recherche :

```
Score de similarité: 42.5
Detail du score:
   - Mots-clés: 15.0
   - Thèmes: 9.0
   - Caractéristiques: 12.0
   - Bonus temporel (récent): +6.5  ⬅️ NOUVEAU
```

---

## 2️⃣ Enrichissement Manuel Intelligent

### Principe

Au lieu d'éditer des champs un par un, vous décrivez vos modifications en **langage naturel** et l'IA interprète, propose les changements, et vous validez.

### Utilisation

#### Étape 1 : Accédez à l'onglet "Enrichissement manuel"

```bash
streamlit run app.py
```

Cliquez sur l'onglet **"✏️ Enrichissement manuel"**

#### Étape 2 : Sélectionnez un document

Choisissez le document à enrichir dans la liste. Les documents déjà enrichis sont marqués d'un ✅.

#### Étape 3 : Décrivez vos modifications

Exemples d'instructions en langage naturel :

```
Ajoute 'béton précontraint' dans les matériaux et retire 'acier'
```

```
Change le résumé pour mettre en avant l'aspect diagnostic patrimonial
```

```
Ajoute 'modélisation 3D' et 'calcul éléments finis' dans la méthodologie
```

```
Retire 'Jean Dupont' de l'équipe et ajoute 'Marie Martin' et 'Paul Durand'
```

#### Étape 4 : Interprétez et validez

1. Cliquez sur **"🔍 Interpréter"**
2. L'IA affiche les modifications proposées :
   - ➕ AJOUTER
   - ➖ RETIRER
   - ✏️ MODIFIER
   - 🆕 CRÉER
3. Vérifiez les modifications
4. Cliquez sur **"✅ Valider et appliquer"** ou **"❌ Annuler"**

### Champs enrichissables

Tous les champs peuvent être enrichis :

- Résumé, mots-clés, thèmes
- Matériaux, domaines, méthodologie
- Équipements, membres d'équipe, rôles
- Références projets, projets cibles
- Sections spéciales
- Illustrations

### Historique

Chaque enrichissement est sauvegardé dans :
- `data/enrichments_history.json` : Historique complet pour apprentissage
- Dans le document lui-même : Champ `manual_enrichments`

---

## 3️⃣ Apprentissage Automatique

### Principe

Le système analyse vos enrichissements pour détecter des **patterns d'erreurs récurrentes** et propose des **améliorations aux prompts d'indexation**.

### Fonctionnement

**Après chaque enrichissement validé**, le système :

1. **Analyse** l'historique complet des enrichissements
2. **Détecte** des patterns :
   - Champs fréquemment modifiés
   - Valeurs souvent ajoutées (non détectées par l'IA)
   - Valeurs souvent retirées (faux positifs)
3. **Génère** des suggestions d'amélioration des prompts
4. **Affiche** les améliorations dans l'interface

### Visualisation des améliorations

Dans l'onglet "Enrichissement manuel", en bas de page :

```
🎓 Améliorations suggérées par l'IA
-----------------------------------
📊 Résumé : Le système détecte 3 patterns d'erreurs récurrents...

Basé sur : 15 enrichissements
Généré le : 2026-01-11 15:30

🔴 [HAUTE] Les équipements spécifiques ne sont pas détectés
   Champ concerné: equipment
   Suggestion: Ajouter des exemples concrets d'équipements...
   Exemple de modification du prompt:
   "Pour les équipements, soyez très précis et incluez
   le matériel distinctif comme : géoradar, corrosimètre,
   ferroscan, carotteuse, nacelle, etc."

🟡 [MOYENNE] Les matériaux composites sont mal identifiés
   ...
```

### Lancer l'analyse manuellement

Si vous voulez forcer une analyse (sans faire d'enrichissement) :

```bash
python learning.py
```

Ou via l'interface web, cliquez sur **"🔄 Lancer l'analyse maintenant"**

### Fichiers générés

- `data/learning_insights.json` : Patterns détectés
- `data/prompt_improvements.json` : Améliorations proposées

---

## 📊 Statistiques

### Dashboard (dans l'interface)

L'onglet "Enrichissement manuel" affiche :

- **Total enrichissements** : Nombre total d'enrichissements effectués
- **Documents enrichis** : Nombre de documents uniques enrichis
- **Dernier enrichissement** : Date du dernier enrichissement

### Métriques de la page d'accueil

Nouvelles métriques ajoutées :

- **⚡ Documents enrichis (v2.0)** : Documents avec la nouvelle analyse enrichie
- **🖼️ Avec illustrations** : Documents contenant des illustrations exceptionnelles

---

## 🔄 Workflow Complet

### Indexation hebdomadaire (TOUT dans l'interface web !)

```bash
# 1. Lancer l'interface web
streamlit run app.py

# 2. Indexer les nouveaux MTs
#    - Onglet "📥 Indexation"
#    - Choisir: Dossier / Fichier(s) / Chemin par défaut
#    - Spécifier le chemin
#    - Cliquer sur "Lancer l'indexation"
#    - Suivre la progression en temps réel

# 3. Vérifier les nouveaux documents
#    - Onglet "💬 Description texte" pour tester la recherche
#    - Les MTs récents auront un bonus dans les résultats

# 4. Enrichir si nécessaire
#    - Onglet "✏️ Enrichissement manuel"
#    - Sélectionner un document
#    - Décrire les modifications en langage naturel
#    - Valider

# 5. Consulter les améliorations suggérées
#    - Section "Améliorations suggérées" en bas de l'onglet
#    - Prendre note des suggestions pour amélioration future
```

### Alternative CLI (si vous préférez)

```bash
# Indexer via ligne de commande
python indexer.py "C:\chemin\vers\nouveaux\MTs"

# Puis lancer l'interface
streamlit run app.py
```

### Cycle d'amélioration continue

```
1. Indexer nouveaux MTs
   ↓
2. Utiliser le système (recherche)
   ↓
3. Détecter erreurs/oublis
   ↓
4. Enrichir manuellement (langage naturel)
   ↓
5. Système apprend automatiquement
   ↓
6. Améliorations proposées
   ↓
7. [Futur] Prompts améliorés appliqués
   ↓
Retour à l'étape 1 (avec moins d'erreurs)
```

---

## 🎯 Objectif Final

**Réduire progressivement le besoin d'enrichissements manuels** en améliorant continuellement les prompts d'indexation grâce à vos corrections.

**Résultat attendu** : Après quelques semaines/mois d'enrichissements, le système devrait :
- Détecter 90%+ des équipements spécifiques
- Identifier correctement les matériaux composites
- Capturer les sections techniques distinctives
- Réduire les faux positifs

---

## 🛠️ Commandes Utiles

```bash
# Indexer de nouveaux documents
python indexer.py /chemin/vers/nouveaux/mts

# Forcer réindexation complète
python indexer.py --force

# Lancer interface web
streamlit run app.py

# Recherche CLI (avec bonus temporel)
python find_similar.py "votre requête"

# Lancer cycle d'apprentissage manuel
python learning.py
```

---

## 📝 Notes Techniques

### Fichiers ajoutés

- `enrichment.py` : Gestionnaire d'enrichissement
- `learning.py` : Système d'apprentissage
- `data/enrichments_history.json` : Historique des enrichissements
- `data/learning_insights.json` : Insights détectés
- `data/prompt_improvements.json` : Améliorations proposées

### Modifications existantes

- `config.py` : Paramètres de pondération temporelle
- `find_similar.py` : Ajout du bonus temporel dans le scoring
- `app.py` : Nouvel onglet "Enrichissement manuel" + visualisation améliorations
- `index.json` : Nouveaux champs (`manual_enrichments`, `manually_enriched`, `last_manual_enrichment`)

### API Claude

Les nouvelles fonctionnalités utilisent l'API Claude :
- **Enrichissement** : ~1 call par enrichissement (interprétation)
- **Apprentissage** : ~1 call par cycle (génération améliorations)

Coût estimé : ~0.01$ par enrichissement + apprentissage

---

## 🆘 Support

En cas de problème :

1. Vérifiez les logs dans la console
2. Consultez les fichiers JSON dans `data/` pour débugger
3. Le système continue de fonctionner même si l'apprentissage échoue
4. Enrichissements sauvegardés dans l'historique même en cas d'erreur

---

## 🚀 Prochaines Étapes (Suggestions)

1. **Application automatique des améliorations** : Modifier `indexer.py` pour intégrer les prompts améliorés
2. **Interface de validation des améliorations** : Permettre de valider/rejeter les suggestions avant application
3. **Métriques d'amélioration** : Tracker l'évolution de la qualité (% enrichissements, types d'erreurs)
4. **Export des enrichissements** : Générer un rapport des corrections effectuées
