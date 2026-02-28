# Guide Interface Web - Tout en un seul endroit 🚀

## Lancement

```bash
streamlit run app.py
```

Votre navigateur s'ouvre automatiquement sur `http://localhost:8501`

---

## 📊 Dashboard (Haut de page)

Statistiques en temps réel :
- **📚 Documents indexés** : Total de MTs dans l'index
- **🕐 Dernière mise à jour** : Date de dernière indexation
- **⚡ Documents enrichis (v2.0)** : Documents avec analyse avancée
- **🖼️ Avec illustrations** : Documents contenant des illustrations exceptionnelles

---

## Les 4 Onglets Principaux

### 1️⃣ 💬 Description texte - RECHERCHER

**Usage** : Trouver des MTs similaires à votre nouveau projet

**Comment** :
1. Décrivez votre projet dans la zone de texte
2. Cliquez sur "🔍 Rechercher"
3. Consultez les résultats triés par score de similarité

**Exemple** :
```
Diagnostic de pont en béton armé avec instrumentation
vibratoire et géoradar, équipe avec alpiniste cordiste
```

**Résultats affichés** :
- Score de similarité (avec bonus temporel pour MTs récents)
- Mots-clés et thèmes communs
- Aperçu des 3 illustrations les plus pertinentes
- Détails complets (expander) : résumé, caractéristiques, distinctions

---

### 2️⃣ 📁 Recherche par fichier

**Status** : Fonctionnalité à venir

---

### 3️⃣ ✏️ Enrichissement manuel - CORRIGER

**Usage** : Corriger/améliorer l'indexation automatique

**Comment** :

#### Étape 1 : Sélectionner le document
- Choisir dans la liste déroulante
- ✅ = document déjà enrichi manuellement
- Cliquer sur "📋 État actuel" pour voir l'indexation actuelle

#### Étape 2 : Décrire vos modifications en langage naturel
Exemples :
```
Ajoute 'béton précontraint' dans les matériaux et retire 'acier'
```
```
Change le résumé pour mettre en avant l'aspect diagnostic patrimonial
```
```
Ajoute 'modélisation 3D' dans la méthodologie
```
```
Retire 'Jean Dupont' de l'équipe et ajoute 'Marie Martin'
```

#### Étape 3 : Interpréter
- Cliquez sur "🔍 Interpréter"
- L'IA affiche les modifications structurées :
  - ➕ AJOUTER
  - ➖ RETIRER
  - ✏️ MODIFIER
  - 🆕 CRÉER

#### Étape 4 : Valider ou annuler
- "✅ Valider et appliquer" : applique les modifications
- "❌ Annuler" : abandonne les modifications

**Après validation** :
- ✅ Modifications appliquées
- 🎓 Le système apprend automatiquement
- 🎉 Ballons de célébration !

#### Section "🎓 Améliorations suggérées" (bas de page)

Le système affiche :
- 📊 Résumé des patterns détectés
- 🔴 [HAUTE] Problèmes prioritaires
- 🟡 [MOYENNE] Problèmes importants
- 🟢 [BASSE] Améliorations mineures

Pour chaque amélioration :
- Champ concerné
- Suggestion concrète
- Exemple de modification du prompt

---

### 4️⃣ 📥 Indexation - AJOUTER

**Usage** : Indexer de nouveaux MTs ou réindexer des documents modifiés

**3 modes disponibles** :

#### Mode 1 : 📁 Dossier complet
1. Sélectionner "📁 Dossier complet"
2. **NOUVEAU** : Cliquer sur "📂 Parcourir..." pour ouvrir l'explorateur Windows
   - OU entrer manuellement le chemin : `C:\Users\David\Documents\MTs\Janvier_2026`
3. Voir le nombre de fichiers détectés
4. Cliquer sur "🚀 Lancer l'indexation"

#### Mode 2 : 📄 Fichier(s) individuel(s)
1. Sélectionner "📄 Fichier(s) individuel(s)"
2. **NOUVEAU** : Cliquer sur "📂 Parcourir..." pour ouvrir l'explorateur Windows
   - Sélectionner un ou plusieurs fichiers (Ctrl+clic pour sélection multiple)
   - OU entrer manuellement les chemins (un par ligne)
3. Voir la validation des fichiers
4. Cliquer sur "🚀 Lancer l'indexation"

#### Mode 3 : 🔄 Utiliser le chemin par défaut (.env)
1. Sélectionner "🔄 Utiliser le chemin par défaut"
2. Voir le chemin configuré dans `.env`
3. Cliquer sur "🚀 Lancer l'indexation"

**Option "Forcer la réindexation"** :
- ☑️ Cocher pour réindexer les fichiers déjà indexés
- Utile si vous avez modifié un document

**Pendant l'indexation** :
- 📊 Barre de progression en temps réel
- 📄 Logs d'indexation (fichier par fichier)
- ⏱️ Statut actuel

**Résumé final** :
- 📥 Indexés : Nouveaux documents ajoutés
- ⏭️ Ignorés : Documents déjà indexés
- ❌ Erreurs : Échecs d'indexation
- ✅ Total dans l'index

**Bonus** : 🎈 Ballons de célébration à la fin !

---

## 🎯 Workflow Hebdomadaire Complet

```
1. Lancer l'interface web
   ↓
2. Onglet "Indexation" → Indexer nouveaux MTs
   ↓
3. Onglet "Description texte" → Tester la recherche
   ↓
4. Si erreurs détectées → Onglet "Enrichissement manuel"
   ↓
5. Consulter "Améliorations suggérées"
   ↓
6. Répéter chaque semaine
```

**Résultat** : Système qui s'améliore automatiquement avec vos corrections !

---

## 💡 Astuces

### Explorateur Windows natif
- **Mode Dossier** : Le bouton "📂 Parcourir..." ouvre l'explorateur Windows natif
  - Naviguez visuellement dans vos dossiers
  - Cliquez sur "Sélectionner le dossier" pour valider
- **Mode Fichiers** : Sélection multiple disponible
  - `Ctrl + clic` : Sélectionner plusieurs fichiers un par un
  - `Shift + clic` : Sélectionner une plage de fichiers
  - Filtrage automatique par type (.docx, .pdf, etc.)

### Raccourcis clavier
- `Ctrl + R` : Rafraîchir la page
- `Esc` : Fermer les expanders

### Performance
- Les MTs récents (< 3 mois) ont un bonus +15% dans les recherches
- L'indexation est sauvegardée tous les 10 documents
- Les fichiers déjà indexés sont automatiquement ignorés

### Coûts API
- ~0.25$ pour 100 documents indexés
- ~0.01$ par enrichissement manuel + apprentissage

### Formats supportés
- `.docx` (Word)
- `.pdf` (PDF)
- `.doc` (Word ancien)
- `.docm` (Word avec macros)

---

## ❓ FAQ

**Q : L'interface est lente ?**
R : L'indexation et l'enrichissement utilisent l'API Claude, cela peut prendre quelques secondes. La recherche est instantanée.

**Q : Puis-je indexer pendant que l'interface est ouverte ?**
R : Oui ! Utilisez l'onglet "Indexation". Vous pouvez aussi indexer via CLI en parallèle.

**Q : Les enrichissements modifient-ils l'index immédiatement ?**
R : Oui, dès validation, l'index est mis à jour. Cliquez sur "🔄 Rafraîchir" pour voir les changements.

**Q : Comment voir l'historique de mes enrichissements ?**
R : Consultez `data/enrichments_history.json` ou les statistiques en haut de l'onglet "Enrichissement".

**Q : Le système apprend vraiment tout seul ?**
R : Oui ! Après chaque enrichissement, il analyse les patterns et propose des améliorations des prompts d'indexation.

---

## 🆘 Support

En cas de problème :
1. Vérifiez la console (terminal où vous avez lancé `streamlit run app.py`)
2. Consultez les logs dans les fichiers `.log`
3. Relancez l'interface : `Ctrl+C` puis `streamlit run app.py`

---

**Tout est maintenant dans l'interface web !** 🎉

Plus besoin de ligne de commande pour l'usage quotidien.
