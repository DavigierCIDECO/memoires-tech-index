# 🚀 Démarrage Rapide

Guide en 5 minutes pour commencer à utiliser le système.

## 1️⃣ Installation (2 minutes)

```bash
# Dans le dossier memoires-tech-index

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier de configuration
copy .env.example .env
```

Éditez `.env` avec un éditeur de texte :
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
LOCAL_DOCS_PATH=C:\Mes Documents\Memoires Techniques
```

**Obtenir une clé API Claude :**
1. Allez sur https://console.anthropic.com/
2. Créez un compte
3. Section "API Keys" → "Create Key"
4. Copiez la clé dans `.env`

## 2️⃣ Vérifier l'installation (30 secondes)

```bash
python test_installation.py
```

Si tout est ✓, passez à l'étape suivante.

## 3️⃣ Indexer vos documents (variable selon volume)

```bash
# Indexer le dossier configuré dans .env
python indexer.py

# OU indexer un dossier spécifique
python indexer.py "C:\Dossier\Memoires"
```

**Patientez** pendant l'indexation (quelques minutes pour 100 documents).

## 4️⃣ Utiliser le système

### Rechercher dans vos documents

```bash
python search.py cybersécurité azure
```

### Trouver le meilleur document de base pour un nouveau projet

```bash
python find_similar.py "projet de migration cloud vers AWS"
```

### Analyser un fichier existant

```bash
python find_similar.py "C:\nouveau_projet.docx" --file
```

## 🎯 Workflow Recommandé

### Quand vous démarrez un nouveau mémoire technique :

1. **Décrivez votre projet**
   ```bash
   python find_similar.py "appel d'offres système de ticketing avec Jira"
   ```

2. **Le système vous recommande** le document le plus proche comme base

3. **Ouvrez ce document** et utilisez-le comme point de départ

4. **Cherchez des sections spécifiques** dans d'autres documents :
   ```bash
   python search.py architecture jira intégration
   ```

5. **Copiez-collez** les sections pertinentes

## 📊 Statistiques de l'index

```bash
python search.py --stats
```

Affiche :
- Nombre de documents indexés
- Taille totale
- Mots-clés les plus fréquents
- Thèmes récurrents

## ⚡ Astuces

### Mettre à jour l'index après ajout de documents

```bash
python indexer.py
# Seuls les nouveaux fichiers sont indexés
```

### Forcer la réindexation complète

```bash
python indexer.py --force
```

### Recherche avec plusieurs termes

```bash
python search.py "gestion de projet" "méthodologie agile"
```

### Limiter les résultats

```bash
python search.py kubernetes --max 3
```

## 🆘 Problèmes Courants

### "ANTHROPIC_API_KEY non définie"
→ Vérifiez votre fichier `.env`

### "Module not found"
→ `pip install -r requirements.txt`

### Aucun résultat
→ Vérifiez que l'index existe : `python search.py --stats`

### Indexation lente
→ Normal pour la première fois (génération des résumés)

## 📞 Prochaines Étapes

Une fois familiarisé avec le système :
1. Indexez vos Google Drives (Phase 2)
2. Partagez avec vos collègues
3. Intégrez avec Claude Code (MCP)

Consultez le `README.md` complet pour plus de détails.
