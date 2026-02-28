# Guide d'Utilisation - Système d'Indexation de Mémoires Techniques

## 📖 PARTIE 1 : Utilisation complète du système

### A) Comment indexer de nouveaux mémoires techniques

#### Scénario 1 : Vous ajoutez des documents dans le dossier existant

```bash
# Ouvrez un terminal Windows (PowerShell ou cmd)
cd C:\Users\David\Documents\ClaudeCodeSandbox\memoires-tech-index

# Lancez l'indexation
python indexer.py
```

**Ce qui se passe :**
- Le système scanne le dossier configuré dans `.env` : `C:\Users\David\Documents\0K- Mémoires techniques OA`
- Il calcule un hash MD5 de chaque fichier
- Si le fichier existe déjà dans l'index (même hash) → **ignoré** ✅ (pas de coût API)
- Si le fichier est nouveau ou modifié → **indexé** avec résumé généré par Claude
- Durée : ~6 secondes par nouveau document

**Résultat :**
```
=== Résumé de l'indexation ===
Indexés: 3
Ignorés (déjà indexés): 22
Erreurs: 0
Total dans l'index: 25
```

#### Scénario 2 : Indexer un autre dossier

```bash
python indexer.py "C:\Autre\Dossier\Memoires"
```

Cela indexe un dossier différent de celui configuré dans `.env`.

#### Scénario 3 : Forcer la réindexation complète

```bash
python indexer.py --force
```

Réindexe TOUS les fichiers, même ceux déjà indexés. Utile si :
- Vous avez modifié le contenu d'un fichier
- Vous voulez régénérer tous les résumés

---

### B) Comment requêter dans l'index

#### 🔍 1. Recherche par mots-clés

**Recherche simple :**
```bash
python search.py précontrainte diagnostic pont
```

**Recherche avec termes entre guillemets :**
```bash
python search.py "diagnostic de pont" précontrainte
```

**Limiter le nombre de résultats :**
```bash
python search.py précontrainte --max 3
```

**Voir les statistiques de l'index :**
```bash
python search.py --stats
```

**Résultat d'une recherche :**
```
================================================================================
Résultats pour : précontrainte diagnostic pont
================================================================================

1. Pont de Cantepau.docx
   Score de pertinence: 55.5
   Chemin: C:\Users\David\Documents\0K- Mémoires techniques OA\Pont de Cantepau.docx
   Taille: 19258.3 KB
   Modifié: 2023-09-03

   Résumé:
   Ce mémoire technique présente le projet de diagnostic du pont de Cantepau...

   Mots-clés: précontrainte, diagnostic, ouvrages d'art, auscultation
   Thèmes: Diagnostic d'infrastructure, Techniques d'investigation

   Aperçu:
   Direction des routes du Sud-Ouest RN88 – Pont de Cantepau...
```

---

#### 🎯 2. Trouver le document de base pour un nouveau projet

**À partir d'une description de projet :**
```bash
python find_similar.py "Je dois faire un diagnostic de viaduc autoroutier avec investigations précontrainte"
```

**À partir d'un fichier existant :**
```bash
python find_similar.py "C:\MonNouveauProjet.docx" --file
```

**Limiter les résultats :**
```bash
python find_similar.py "diagnostic pont" --max 3
```

**Résultat :**
```
================================================================================
DOCUMENTS SIMILAIRES TROUVÉS
================================================================================

Votre projet :
  Résumé: Réalisation d'un diagnostic approfondi sur un viaduc ancien...
  Mots-clés: viaduc, précontrainte, diagnostic, béton, infrastructure
  Thèmes: Expertise structurelle, Infrastructure de transport

--------------------------------------------------------------------------------

1. Pont de Cantepau.docx
   Score de similarité: 26.0
   Chemin: C:\Users\David\Documents\0K- Mémoires techniques OA\Pont de Cantepau.docx
   Mots-clés communs: précontrainte, diagnostic, ingénierie
   Thèmes communs: génie civil, maintenance des ouvrages

   Résumé du document:
   Ce mémoire technique présente le projet de diagnostic du pont de Cantepau...

--------------------------------------------------------------------------------

RECOMMANDATION:

>> Utilisez 'Pont de Cantepau.docx' comme base
   (Score: 26.0)

>> Considerez aussi ces documents pour des sections specifiques :
   - Allier - Note Méthodologique.docx (Score: 24.5)
   - Haute Savoie.docx (Score: 24.5)
```

---

#### 🔄 3. Workflow complet (exemple réel)

**Situation :** Vous devez créer un nouveau mémoire technique pour un diagnostic de pont métallique avec problèmes de corrosion.

```bash
# ÉTAPE 1 : Trouvez le document de base
cd C:\Users\David\Documents\ClaudeCodeSandbox\memoires-tech-index
python find_similar.py "diagnostic pont métallique corrosion fatigue acier"

# Résultat : Le système recommande "Pont XYZ.docx" comme base

# ÉTAPE 2 : Ouvrez "Pont XYZ.docx" dans Word
# → Utilisez-le comme structure de départ

# ÉTAPE 3 : Cherchez des sections spécifiques pour enrichir votre document
python search.py "méthodologie inspection métallique"
python search.py "analyse corrosion acier"
python search.py "essais non destructifs"

# ÉTAPE 4 : Ouvrez les documents trouvés et copiez-collez les sections pertinentes

# ÉTAPE 5 : Adaptez et personnalisez pour votre projet
```

**Temps gagné :** Au lieu de partir de zéro ou de fouiller manuellement dans 25+ documents, vous avez immédiatement :
- Le meilleur document de base (30 secondes)
- Les sections pertinentes des autres documents (2 minutes)

---

## 💻 PARTIE 2 : Claude Code et la gestion des sessions

### Que se passe-t-il si vous fermez le terminal ?

#### ✅ SAUVEGARDÉ (permanent) :

1. **Tous les fichiers du projet**
   - `memoires-tech-index/` (dossier complet)
   - Scripts Python (`indexer.py`, `search.py`, `find_similar.py`, etc.)
   - Configuration (`.env`)
   - Index des documents (`data/index.json`)

2. **Votre index**
   - Les 25 documents indexés restent dans `data/index.json`
   - Tous les résumés, mots-clés et thèmes générés

3. **Configuration**
   - Clé API Claude
   - Chemin vers vos documents

**→ Vous pouvez utiliser le système même après avoir fermé le terminal !**

#### ❌ PERDU (temporaire) :

1. **L'historique de la conversation avec Claude Code**
   - Claude ne se "souviendra" pas de ce qu'on a discuté
   - Les explications données pendant la session

2. **Le contexte de la session**
   - Claude devra "réapprendre" votre projet si vous le relancez

**→ C'est normal, chaque session Claude Code est indépendante**

---

### Comment reprendre ?

#### 🎯 Option 1 : Utiliser le système SANS Claude Code (recommandé au quotidien)

**Vous N'AVEZ PAS BESOIN de Claude Code pour utiliser le système !**

Les scripts Python fonctionnent de manière autonome :

```bash
# Ouvrez un terminal Windows (PowerShell, cmd, ou Terminal)
cd C:\Users\David\Documents\ClaudeCodeSandbox\memoires-tech-index

# Utilisez directement les commandes Python
python search.py diagnostic
python find_similar.py "votre nouveau projet"
python indexer.py  # Pour ajouter de nouveaux documents
```

**Cas d'usage quotidien :**
- Vous cherchez un document → `python search.py`
- Vous démarrez un nouveau projet → `python find_similar.py`
- Vous avez ajouté des documents → `python indexer.py`

**Pas besoin de Claude Code !**

---

#### 🤖 Option 2 : Nouvelle session Claude Code

```bash
# Ouvrez un terminal n'importe où
claude

# Claude démarre une NOUVELLE conversation
# Il ne se souviendra pas de la session précédente
```

**Quand utiliser Claude Code ?**
- Vous voulez ajouter de nouvelles fonctionnalités au système
- Vous rencontrez un bug à corriger
- Vous voulez développer la Phase 2 (Google Drive)
- Vous avez besoin d'aide pour personnaliser quelque chose

---

#### 🔄 Option 3 : Continuer une conversation précédente

```bash
# Reprendre la dernière conversation
claude -c

# Choisir une conversation antérieure
claude -r
```

**⚠️ Note importante :** Même en reprenant une conversation, c'est une nouvelle session. Claude a accès à l'historique, mais ne "continue" pas exactement où vous en étiez.

---

## 📋 Aide-mémoire rapide

### Commandes essentielles

```bash
# ALLER DANS LE DOSSIER DU PROJET
cd C:\Users\David\Documents\ClaudeCodeSandbox\memoires-tech-index

# INDEXER DE NOUVEAUX DOCUMENTS
python indexer.py                           # Index le dossier configuré
python indexer.py "C:\Autre\Dossier"       # Index un dossier spécifique
python indexer.py --force                   # Réindexe tout

# RECHERCHER
python search.py diagnostic pont            # Recherche simple
python search.py "mot composé" autre        # Avec termes entre guillemets
python search.py diagnostic --max 5         # Limite à 5 résultats
python search.py --stats                    # Voir les statistiques

# TROUVER DOCUMENT SIMILAIRE
python find_similar.py "description projet" # Description textuelle
python find_similar.py "fichier.docx" --file # À partir d'un fichier
python find_similar.py "projet" --max 3     # Limite à 3 résultats

# TESTER L'INSTALLATION
python test_installation.py                 # Vérifier que tout fonctionne
```

---

## 🚀 Workflow recommandé au quotidien

### 1️⃣ Quand vous démarrez un nouveau mémoire technique

```bash
cd memoires-tech-index
python find_similar.py "description de votre nouveau projet"

# → Ouvrez le document recommandé dans Word
# → Utilisez-le comme base
```

### 2️⃣ Pendant la rédaction

```bash
# Cherchez des sections spécifiques
python search.py "méthodologie diagnostic"
python search.py "analyse structurelle"
python search.py "conclusions recommandations"

# → Ouvrez les documents trouvés
# → Copiez-collez les sections pertinentes
```

### 3️⃣ Quand vous ajoutez de nouveaux mémoires

```bash
# Ajoutez vos fichiers dans : C:\Users\David\Documents\0K- Mémoires techniques OA
# Puis :
python indexer.py

# Seuls les nouveaux fichiers seront indexés
```

### 4️⃣ Maintenance

```bash
# Vérifier l'état de l'index
python search.py --stats

# Réindexer si vous avez modifié des fichiers
python indexer.py --force
```

---

## 💡 Questions fréquentes

### Q : Dois-je lancer Claude Code à chaque fois ?
**R :** Non ! Le système fonctionne avec Python seul. Claude Code n'est utile que pour développer/modifier le système.

### Q : L'indexation coûte-t-elle cher ?
**R :** Environ 0.25$ pour 100 documents. Les fichiers déjà indexés sont gratuits (ignorés automatiquement).

### Q : Puis-je indexer plusieurs dossiers ?
**R :** Oui ! Lancez `python indexer.py "chemin"` pour chaque dossier. Tous seront dans le même index.

### Q : Comment supprimer un document de l'index ?
**R :** Supprimez le fichier du dossier, puis réindexez avec `python indexer.py --force`.

### Q : Puis-je utiliser le système sans connexion internet ?
**R :** Non, la recherche fonctionne hors ligne, mais l'indexation nécessite l'API Claude (internet).

### Q : Et pour les Google Drives ?
**R :** C'est prévu dans la Phase 2 ! Pour l'instant, téléchargez les fichiers localement pour les indexer.

---

## 📞 Besoin d'aide ?

1. **Problème technique :** Relancez `python test_installation.py`
2. **Question sur l'utilisation :** Relisez ce guide
3. **Développement Phase 2 :** Lancez `claude` et demandez de l'aide
4. **Documentation complète :** Consultez `README.md`

---

## 🎯 En résumé

**Le système est maintenant autonome et utilisable sans Claude Code !**

- ✅ 25 documents indexés
- ✅ Recherche par mots-clés opérationnelle
- ✅ Détection de documents similaires fonctionnelle
- ✅ Scripts Python autonomes

**Pour l'utilisation quotidienne :**
```bash
cd memoires-tech-index
python search.py <recherche>
python find_similar.py "<projet>"
python indexer.py  # quand nouveaux documents
```

**Claude Code n'est nécessaire que pour améliorer/développer le système, pas pour l'utiliser !**

---

*Guide créé le 2025-12-11 - Version 1.0*
