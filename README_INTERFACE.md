# 🔍 Interface Web de Recherche - Guide Utilisateur

Interface Streamlit pour rechercher des mémoires techniques similaires.

---

## 🚀 Lancement Local (sur votre PC)

### Prérequis

1. **Python 3.8+** installé
2. **Dépendances** installées :
```bash
pip install -r requirements.txt
```

3. **Index créé** : Vous devez avoir au moins indexé quelques documents
```bash
python indexer.py "C:\chemin\vers\vos\memoires"
```

### Lancer l'Interface

```bash
streamlit run app.py
```

L'interface s'ouvrira automatiquement dans votre navigateur à l'adresse :
```
http://localhost:8501
```

**Si le navigateur ne s'ouvre pas automatiquement**, copiez l'URL affichée dans le terminal.

---

## 🌐 Déploiement pour vos Collègues (Streamlit Cloud)

Pour que vos collègues puissent accéder à l'interface sans installation, déployez sur **Streamlit Cloud** (gratuit).

### Étape 1 : Préparer le Dépôt Git

1. **Créer un dépôt GitHub** (privé ou public) :
   - Allez sur https://github.com
   - Cliquez "New repository"
   - Nom : `memoires-tech-search`
   - ✅ Privé (recommandé)
   - Créer

2. **Pousser le code** :
```bash
cd "C:\Users\David\Documents\ClaudeCodeSandbox\memoires-tech-index"

# Initialiser git si pas déjà fait
git init

# Créer .gitignore
echo ".env" > .gitignore
echo "data/index.json.backup" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore

# Ajouter et committer
git add .
git commit -m "Interface Streamlit de recherche"

# Lier au dépôt GitHub
git remote add origin https://github.com/VOTRE_USERNAME/memoires-tech-search.git
git branch -M main
git push -u origin main
```

### Étape 2 : Créer Fichier de Configuration Cloud

Créez un fichier `.streamlit/secrets.toml` pour les secrets (clés API) :

```bash
mkdir .streamlit
```

Créez `.streamlit/secrets.toml` :
```toml
ANTHROPIC_API_KEY = "votre-clé-api-anthropic"
```

⚠️ **Important** : Ajoutez `.streamlit/secrets.toml` au `.gitignore` :
```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

### Étape 3 : Déployer sur Streamlit Cloud

1. **Créer un compte** : https://share.streamlit.io
   - Connectez-vous avec votre compte GitHub

2. **Nouveau déploiement** :
   - Cliquez "New app"
   - Sélectionnez votre dépôt GitHub
   - Branch : `main`
   - Main file : `app.py`
   - Cliquez "Deploy"

3. **Ajouter les secrets** :
   - Dans les paramètres de l'app (⚙️)
   - Section "Secrets"
   - Copiez le contenu de `.streamlit/secrets.toml`
   - Sauvegardez

4. **Partager l'URL** avec vos collègues :
   ```
   https://votre-app-unique.streamlit.app
   ```

### Étape 4 : Mettre à Jour l'Index

**Option A : Index dans le dépôt Git** (Simple mais limitée)
- L'index `data/index.json` est dans le dépôt
- **Mise à jour** :
  1. Vous indexez localement : `python indexer.py`
  2. Vous poussez sur Git : `git add data/index.json && git commit -m "Update index" && git push`
  3. Streamlit Cloud redémarre automatiquement

**Option B : Index sur Google Drive** (Recommandée pour évolutions futures)
- Mettez `data/index.json` sur un Drive partagé en lecture
- Modifiez `config.py` pour charger depuis une URL partagée
- Vos collègues voient toujours l'index à jour

---

## 📊 Utilisation de l'Interface

### Recherche par Description

1. Ouvrez l'interface
2. Onglet **"💬 Description texte"**
3. Tapez votre requête :
   ```
   Diagnostic de pont en béton armé avec géoradar et corrosimètre
   ```
4. Cliquez **🔍 Rechercher**
5. Résultats affichés avec scores de similarité
6. Cliquez **"📋 Voir détails complets"** pour plus d'infos

### Exemples de Requêtes

**Par type de projet** :
```
Diagnostic d'ouvrage d'art en maçonnerie
```

**Par équipement** :
```
Projet avec géoradar et ferroscan
```

**Par équipe** :
```
Mission avec Lionel et alpiniste cordiste
```

**Par référence** :
```
Projet similaire au Pont d'Orbeil
```

**Combiné** :
```
Pont béton armé avec analyse vibratoire et accéléromètres, équipe Houssem
```

---

## 🔄 Workflow Complet

### Vous (David - Admin)

**Indexation** (sur votre PC) :
```bash
# Indexer nouveaux documents
python indexer.py "C:\path\to\new\memoires"

# Ou forcer réindexation complète
python indexer.py "C:\path\to\all\memoires" --force

# Pousser l'index mis à jour (si Option A)
git add data/index.json
git commit -m "Update index with new documents"
git push
```

### Vos Collègues

**Recherche** (via navigateur) :
1. Ouvrent `https://votre-app.streamlit.app`
2. Décrivent leur projet
3. Trouvent le mémoire le plus similaire
4. Utilisent comme base pour leur nouveau mémoire

---

## 🎨 Fonctionnalités de l'Interface

### Page d'Accueil

- **📚 Statistiques** : Nombre de documents indexés
- **🕐 Dernière mise à jour** : Date de la dernière indexation
- **⚡ Documents enrichis** : Nombre de documents avec analyse v2.0

### Résultats de Recherche

Pour chaque document trouvé :
- **Score de similarité** : Pertinence du document
- **Éléments communs** : Mots-clés et thèmes en commun
- **Détails complets** (expandable) :
  - Résumé
  - Caractéristiques (matériaux, équipements, équipe, etc.)
  - Aspects uniques (ce qui le distingue)
  - Différenciateurs
  - Métadonnées

---

## 🛠️ Maintenance

### Mettre à Jour les Dépendances

```bash
pip install --upgrade -r requirements.txt
```

### Redémarrer l'Interface Locale

Appuyez sur `Ctrl+C` dans le terminal, puis :
```bash
streamlit run app.py
```

### Redémarrer l'Interface Cloud

Option 1 : Automatique après `git push`

Option 2 : Manuel dans les paramètres Streamlit Cloud :
- ⚙️ Paramètres → "Reboot app"

---

## ❓ Dépannage

### "Index introuvable"

**Problème** : L'index n'existe pas.

**Solution** :
```bash
python indexer.py "C:\path\to\memoires"
```

### "ANTHROPIC_API_KEY non définie"

**Problème** : Clé API manquante.

**Solution locale** : Créez `.env` :
```
ANTHROPIC_API_KEY=votre-clé-ici
```

**Solution cloud** : Ajoutez dans Secrets (Streamlit Cloud).

### Interface ne se lance pas

**Vérifiez** :
```bash
# Python version
python --version  # Doit être 3.8+

# Streamlit installé
streamlit --version

# Réinstaller si besoin
pip install --force-reinstall streamlit
```

### Résultats vides

**Causes possibles** :
- Index vide (pas de documents indexés)
- Requête trop spécifique
- Aucun document ne correspond

**Solutions** :
- Vérifiez `data/index.json` (doit contenir des documents)
- Simplifiez la requête
- Indexez plus de documents

---

## 📈 Prochaines Améliorations Possibles

- [ ] Upload de fichier pour recherche par document
- [ ] Filtres avancés (par année, matériau, équipe)
- [ ] Export des résultats en PDF/Excel
- [ ] Liens directs vers fichiers sur Google Drive
- [ ] Recherche par similarité d'image (captures d'écran)
- [ ] Authentification utilisateur
- [ ] Historique des recherches

---

## 🆘 Support

Pour toute question ou problème, contactez **David Vigier**.

---

**Version** : 1.0
**Date** : Décembre 2024
