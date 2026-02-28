# 📍 État d'Avancement - Système d'Indexation Mémoires Techniques

**Dernière mise à jour** : 2024-12-24

---

## ✅ Terminé

### Phase 1 : Indexation Différentielle (COMPLÉTÉ)
- ✅ Système d'indexation en 3 phases (analyse enrichie, similarité, différentielle)
- ✅ Extraction de caractéristiques enrichies :
  - Matériaux, domaines, méthodologie, types d'ouvrages
  - **Équipements** (géoradar, corrosimètre, nacelle, waders, etc.)
  - **Membres d'équipe** (Lionel, Houssem, David, Alaa)
  - **Rôles/compétences** (ingénieur structure, alpiniste cordiste)
  - **Sections spéciales** (analyse de risques, plan sécurité, etc.)
  - **Références projets** (Pont d'Orbeil, Viaduc de Rive de Gier)
  - **Exemples de rapports** (Rapport de diagnostic du Pont d'Orbeil)
- ✅ Scoring de similarité enrichi (score ≥ 20 pour analyse différentielle, max 5 docs)
- ✅ Affichage enrichi dans `find_similar.py`
- ✅ Backup de l'index : `data/index.json.backup`

### Fichiers Modifiés
- `config.py` : Ajout SIMILARITY_THRESHOLD=10.0, DIFFERENTIAL_ANALYSIS_THRESHOLD=20.0, MAX_DIFFERENTIAL_COMPARISONS=5
- `indexer.py` : Workflow 3 phases, extraction caractéristiques enrichies
- `find_similar.py` : Affichage complet des nouvelles caractéristiques

---

## 🔄 En Cours : Interface Streamlit + Google Drive

### Objectif
Créer une interface graphique web pour :
1. **Indexer** des mémoires techniques depuis Google Drive (4 drives partagés)
2. **Rechercher** avec l'outil find_similar intégré
3. **Partager** avec les collègues (multi-utilisateurs)

### Spécifications

**Drives partagés à scanner** :
- Commerce
- Affaires
- Affaires terminées
- Affaires terminées 2025

**Filtrage** : Seulement les fichiers avec "Mémoire Technique", "Mémoire" ou "MT" dans le titre

**Interface multi-onglets** :
- 📁 **Indexation** : Liste documents Drive, sélection, indexation
  - Statuts : [NOUVEAU], [ÉCARTÉ], [INDEXÉ] (grisé)
  - Année extraite des métadonnées Drive
- 🔍 **Recherche** : find_similar intégré, lien "Ouvrir sur Drive"
- 📊 **Statistiques** : Graphiques, top équipements, références
- ⚙️ **Configuration** : Gestion drives, API keys, paramètres

**Partage** : Déploiement futur sur Streamlit Cloud pour accès collègues

### Architecture Prévue
```
memoires-tech-index/
├── app.py                      # Point d'entrée Streamlit
├── pages/
│   ├── 1_📁_Indexation.py
│   ├── 2_🔍_Recherche.py
│   ├── 3_📊_Statistiques.py
│   └── 4_⚙️_Configuration.py
├── modules/
│   ├── drive_sync.py           # Scan drives + filtre MT
│   ├── tracking.py             # Gestion états (new/excluded/indexed)
│   ├── auth.py                 # Auth Google OAuth
│   └── indexer_wrapper.py      # Wrapper indexer.py
├── data/
│   ├── tracking.json           # États documents
│   └── config.json             # Config drives partagés
└── credentials/
    └── google_creds.json       # À créer (OAuth Google)
```

---

## 🔜 Prochaines Étapes

### Étape 1 : Google Cloud Setup (EN ATTENTE UTILISATEUR)
**Instructions données** :
1. Créer projet Google Cloud : `Memoires-Tech-Indexation`
2. Activer Google Drive API
3. Créer identifiants OAuth (Application de bureau)
4. Télécharger `credentials.json`

👉 **ATTENTE** : Utilisateur doit fournir le fichier `credentials.json`

### Étape 2 : Développement (PRÊT À DÉMARRER)
- [ ] Mettre à jour `requirements.txt` (ajouter streamlit, google-api-python-client, etc.)
- [ ] Créer `modules/auth.py` (authentification Google Drive)
- [ ] Créer `modules/drive_sync.py` (scan drives avec filtre "MT")
- [ ] Créer `modules/tracking.py` (gestion états documents)
- [ ] Créer `app.py` (interface principale Streamlit)
- [ ] Créer pages Streamlit (Indexation, Recherche, Stats, Config)
- [ ] Tests locaux avec `streamlit run app.py`

---

## 📝 Notes Importantes

### Système de Scoring Actuel
- Mots-clés communs : +5 points
- Thèmes communs : +3 points
- Équipements communs : +3 points
- Matériaux communs : +2 points
- Domaines communs : +2 points
- Membres communs : +1 point
- Rôles communs : +1 point

**Seuils** :
- Détection similarité : score ≥ 10.0
- Analyse différentielle : score ≥ 20.0 (max 5 documents)

### Commandes Utiles
```bash
# Indexation actuelle (version console)
python indexer.py                    # Mode incrémental
python indexer.py --force           # Forcer réindexation

# Recherche actuelle (version console)
python find_similar.py "description projet"
python find_similar.py "fichier.docx" --file

# Future commande (quand Streamlit prêt)
streamlit run app.py
```

---

## 🎯 Vision Finale

**Workflow Utilisateur Cible** :
1. Lionel ouvre `https://cideco-memoires.streamlit.app`
2. Onglet Indexation → voit 3 nouveaux MT sur Drive "Affaires"
3. Sélectionne les 2 pertinents, indexe
4. Houssem ouvre l'app → Onglet Recherche
5. Cherche "diagnostic pont béton géoradar"
6. Trouve "MT Pont d'Orbeil" (score 42.5)
7. Clique "Ouvrir sur Drive" → utilise comme base

---

## 📞 Pour Reprendre

**Dire à Claude** :
- "Lis PROGRESS.md et continue"
- "On reprend le développement de l'interface Streamlit"
- "Continue où on s'était arrêté"

**Fichiers de contexte** :
- Ce fichier : `PROGRESS.md`
- Plan détaillé : `.claude/plans/glittery-sleeping-firefly.md`
- Todo list : Commande `/tasks`
