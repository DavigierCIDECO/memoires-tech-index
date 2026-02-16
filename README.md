# Système d'Indexation de Mémoires Techniques

Système intelligent pour indexer, rechercher et trouver des mémoires techniques similaires.

## 🎯 Objectif

Accélérer la création de nouveaux mémoires techniques en :
- Indexant automatiquement tous vos documents (Word .docx et PDF)
- Trouvant rapidement quel mémoire contient quelle information
- Identifiant le document le plus proche de votre nouveau projet
- Suggérant des sections pertinentes à réutiliser

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- Une clé API Anthropic (Claude)

### Étapes

1. **Installer Python** (si pas déjà fait)
   - Téléchargez depuis https://www.python.org/downloads/
   - Cochez "Add Python to PATH" lors de l'installation

2. **Installer les dépendances**
   ```bash
   cd memoires-tech-index
   pip install -r requirements.txt
   ```

3. **Configurer l'environnement**

   Créez un fichier `.env` à la racine du projet :
   ```bash
   copy .env.example .env
   ```

   Éditez `.env` et ajoutez :
   ```
   ANTHROPIC_API_KEY=votre_cle_api_ici
   LOCAL_DOCS_PATH=C:\chemin\vers\vos\documents
   ```

   Pour obtenir une clé API Claude :
   - Allez sur https://console.anthropic.com/
   - Créez un compte ou connectez-vous
   - Allez dans "API Keys"
   - Créez une nouvelle clé

## 📖 Utilisation

### 1. Indexer vos documents

**Première indexation :**
```bash
python indexer.py
```
Cela scanne le dossier configuré dans `LOCAL_DOCS_PATH` et indexe tous les fichiers .docx et .pdf.

**Indexer un dossier spécifique :**
```bash
python indexer.py C:\chemin\vers\dossier
```

**Réindexer tous les fichiers (forcer) :**
```bash
python indexer.py --force
```

**Ce qui se passe :**
- Scan de tous les fichiers .docx et .pdf
- Extraction du texte
- Génération automatique de résumés via Claude
- Extraction des mots-clés et thèmes
- Sauvegarde dans `data/index.json`

### 2. Rechercher dans vos documents

**Recherche simple :**
```bash
python search.py analyse de risque cybersécurité
```

**Limiter le nombre de résultats :**
```bash
python search.py "gestion de projet" --max 5
```

**Voir les statistiques de l'index :**
```bash
python search.py --stats
```

**Résultat :**
- Liste des documents pertinents triés par score
- Résumé, mots-clés et thèmes de chaque document
- Aperçu du contenu
- Chemin complet du fichier

### 3. Trouver des documents similaires

**À partir d'une description de projet :**
```bash
python find_similar.py "Je dois répondre à un appel d'offres pour un projet de migration cloud avec Azure"
```

**À partir d'un fichier existant :**
```bash
python find_similar.py "C:\nouveau_projet.docx" --file
```

**Résultat :**
- Document le plus proche recommandé comme base
- Autres documents pertinents pour sections spécifiques
- Mots-clés et thèmes en commun
- Scores de similarité

## 📁 Structure du Projet

```
memoires-tech-index/
│
├── data/                    # Données générées
│   └── index.json          # Index des documents
│
├── config.py               # Configuration
├── extractor.py            # Extraction de texte (docx/pdf)
├── indexer.py              # Indexation des documents
├── search.py               # Recherche dans l'index
├── find_similar.py         # Trouve documents similaires
│
├── requirements.txt        # Dépendances Python
├── .env.example           # Exemple de configuration
└── README.md              # Ce fichier
```

## 💡 Exemples d'Utilisation

### Scénario 1 : Démarrer un nouveau mémoire technique

```bash
# 1. Décrire votre projet
python find_similar.py "Projet de mise en place d'un système de monitoring avec Grafana et Prometheus"

# 2. Ouvrir le document recommandé comme base
# 3. Rechercher des sections spécifiques dans d'autres documents
python search.py grafana prometheus alerting
```

### Scénario 2 : Retrouver où vous avez parlé de quelque chose

```bash
# Chercher tous les documents qui parlent de Kubernetes
python search.py kubernetes orchestration conteneurs

# Voir les statistiques pour identifier les thèmes récurrents
python search.py --stats
```

### Scénario 3 : Mise à jour de l'index

```bash
# Après avoir ajouté de nouveaux documents
python indexer.py

# Seuls les nouveaux fichiers seront indexés
# Les fichiers déjà indexés sont automatiquement ignorés
```

## 🔧 Personnalisation

### Modifier les paramètres de résumé

Dans `config.py` :
```python
SUMMARY_MAX_TOKENS = 500  # Longueur des résumés
SUMMARY_MODEL = "claude-3-5-haiku-20241022"  # Modèle Claude à utiliser
```

### Ajouter d'autres formats de fichiers

Dans `config.py`, modifiez :
```python
SUPPORTED_EXTENSIONS = [".docx", ".pdf", ".txt"]
```

Puis ajoutez la logique d'extraction dans `extractor.py`.

## 🚧 Évolutions Futures (Phase 2 et 3)

### Phase 2 : Intégration Google Drive
- Synchronisation automatique avec Google Drive
- Indexation des documents partagés
- Mise à jour incrémentale

### Phase 3 : Serveur MCP pour Claude Code
- Interrogation en langage naturel depuis Claude Code
- Commandes du type : `> trouve-moi les mémoires sur la sécurité API`
- Intégration transparente dans votre workflow

### Phase 4 : Interface Web pour l'équipe
- Interface web simple pour recherche
- Partage avec collègues
- Recherche sémantique avancée (embeddings)

## ❓ Dépannage

### Erreur : "ANTHROPIC_API_KEY non définie"
→ Vérifiez que votre fichier `.env` existe et contient la clé API

### Erreur : "Module 'docx' not found"
→ Réinstallez les dépendances : `pip install -r requirements.txt`

### L'indexation est lente
→ Normal pour la première fois (génération des résumés)
→ Les indexations suivantes ne traitent que les nouveaux fichiers

### Aucun résultat de recherche
→ Vérifiez que l'index existe : `python search.py --stats`
→ Si vide, réindexez : `python indexer.py`

## 📊 Coûts API Claude

- Modèle utilisé : Claude 3.5 Haiku (rapide et économique)
- Coût approximatif : ~0.25$ pour 100 documents
- Seuls les nouveaux fichiers consomment de l'API

## 🤝 Support

Pour toute question ou suggestion :
1. Vérifiez ce README
2. Consultez les logs d'erreur
3. Testez avec un seul fichier d'abord

## 📝 Licence

Usage interne - Projet personnel
