# PROJECT CARD — Mémoires Techniques Index

> Dernière mise à jour : 2026-03-05

---

## 1. Description

Outil interne de recherche et d'indexation de mémoires techniques (appels d'offres BTP).
Permet d'indexer des documents Word/PDF, de les enrichir manuellement via Claude AI,
et de retrouver les mémoires les plus similaires à un nouveau projet.

---

## 2. Stack technique

| Couche | Technologie | Version min |
|--------|-------------|-------------|
| Interface | Streamlit | 1.28 |
| Backend | Python | 3.x |
| IA — indexation & similarité | Anthropic Claude (Haiku) | claude-haiku-4-5-20251001 |
| IA — enrichissement & interprétation | Anthropic Claude (Sonnet) | claude-sonnet-4-6 |
| Stockage données (index, JSON) | Google Drive API v3 | — |
| Stockage documents (docx, pdf) | Google Drive API v3 | — |
| Extraction texte | python-docx, PyPDF2 | — |
| Auth Google | google-auth / service account | 2.23 |
| Variables d'env | python-dotenv | — |

---

## 3. Hébergement & services

| Quoi | Où | Service |
|------|----|---------|
| Application web | Streamlit Community Cloud | streamlit.io |
| Index JSON (`index.json`, `enrichments_history.json`, etc.) | Google Drive — dossier data | GCP projet `memoires-tech-index` |
| Documents sources (.docx, .pdf) | Google Drive — dossier docs | GCP projet `memoires-tech-index` |
| Modèles IA | API Anthropic (cloud) | api.anthropic.com |
| Code source | GitHub — `DavigierCIDECO/memoires-tech-index` | github.com |

---

## 4. Credentials & accès utilisés

> Les valeurs réelles ne figurent pas ici — uniquement les services concernés.

| Secret | Service | Stockage |
|--------|---------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API | Streamlit Secrets |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | GCP — Service Account `memoires-tech-drive@memoires-tech-index.iam.gserviceaccount.com` | Fichier JSON à la racine (gitignored) |
| `GDRIVE_DATA_FOLDER_ID` | Google Drive — dossier data | Streamlit Secrets |
| `GDRIVE_DOCS_FOLDER_ID` | Google Drive — dossier docs | Streamlit Secrets |
| `ADMIN_PASSWORD` | Auth admin in-app | Streamlit Secrets |
| Liste utilisateurs (David, Robin, Emmanuelle) | Auth in-app (hardcodé) | `auth.py` |

---

## 5. Évaluation sécurité

### Score de risque : **7 / 20**

*(0 = aucun risque · 20 = risque maximal)*

---

### Risques identifiés

| # | Risque | Sévérité | Statut |
|---|--------|----------|--------|
| R1 | **Authentification sans mot de passe** : sélection du nom dans une liste, sans vérification d'identité. Quiconque connaît l'URL peut lire tout le contenu indexé (résumés, équipements, membres d'équipe…). | 🔴 Élevée | Ouvert — voir recommandation 1 |
| R2 | **Scope Google Drive complet** (`drive`) : le service account peut lire/écrire tout ce qui lui est partagé. Si d'autres dossiers sont partagés par erreur, ils deviennent accessibles. | 🟡 Modérée | Atténué (scope nécessaire ; isoler les partages) |
| R3 | **Credentials file à la racine** : le JSON du service account est dans le workspace. S'il est commité par erreur, les accès Drive seraient compromis. | 🟡 Modérée | Atténué (gitignored, renommé en `*service-account*.json`) |
| R4 | **Utilisateurs hardcodés dans le code** : les noms des utilisateurs sont visibles dans `auth.py`, sans chiffrement ni gestion centralisée. | 🟠 Faible-modérée | Ouvert |
| R5 | **Absence de rate limiting** sur les appels API Anthropic : une utilisation intensive (intentionnelle ou non) peut générer des coûts importants. | 🟠 Faible-modérée | Ouvert |
| R6 | **URL Streamlit Cloud potentiellement publique** : si l'app n'est pas configurée en accès restreint (viewer auth), n'importe qui peut y accéder. | 🔴 Élevée (si public) | À vérifier — voir recommandation 1 |

---

### Mesures de sécurité appliquées (2026-03-05)

| Mesure | Détail |
|--------|--------|
| **Téléchargement supprimé** | Le bouton de téléchargement des MTs a été retiré de l'UI. Les fichiers sources ne sont plus accessibles depuis l'application. |
| **`gdrive_link` non exposé** | Le champ `gdrive_link` n'est jamais envoyé au navigateur (aucun appel `st.*` ne l'affiche). Les nouvelles entrées d'index ne stockent plus ce lien. |
| **`gdrive_file_id` non exposé** | Utilisé uniquement côté serveur pour les appels Drive API, jamais rendu dans le navigateur. |

---

### Pour améliorer le niveau de sécurité

1. **Activer le Viewer Authentication Streamlit Cloud** : Settings → Sharing → "Only specific people can view this app" (login par email / whitelist). Résoudrait R1 et R6 sans modifier le code.
2. **Vérifier les partages Drive** : s'assurer dans la console Google Drive que seuls les 2 dossiers de l'app sont partagés avec le service account. → Atténue R2.
3. **Gérer les utilisateurs hors du code** : déplacer la liste des utilisateurs dans Streamlit Secrets ou un fichier de config non commité. → Résoudrait R4.
4. **Ajouter un budget API Anthropic** : configurer une alerte de coût dans la console Anthropic. → Atténue R5.
5. **Stocker le service account dans Streamlit Secrets** (contenu JSON encodé en base64) plutôt qu'en fichier local. → Résoudrait R3 complètement.
