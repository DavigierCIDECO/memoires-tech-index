"""Indexation des mémoires techniques avec génération de résumés via Claude."""
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib

from anthropic import Anthropic

from extractor import TextExtractor
from image_extractor import ImageExtractor
import config

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Indexe les documents et génère des résumés."""

    def __init__(self):
        """Initialise l'indexeur."""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY non définie. "
                "Créez un fichier .env avec votre clé API."
            )

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.extractor = TextExtractor()
        self.storage = config.get_storage()

        # Créer le dossier data s'il n'existe pas (mode local)
        config.DATA_DIR.mkdir(exist_ok=True)

        # Charger les règles apprises
        self.learned_rules = self._load_learned_rules()
        if self.learned_rules:
            logger.info(f"📚 {len(self.learned_rules)} règle(s) apprise(s) chargée(s)")

    def _load_learned_rules(self) -> List[Dict]:
        """Charge les règles apprises depuis le fichier de règles.

        Returns:
            Liste des règles apprises
        """
        try:
            data = self.storage.read_json("learned_rules")
            if data:
                return data.get("rules", [])
            return []
        except Exception as e:
            logger.warning(f"Impossible de charger les règles apprises: {e}")
            return []

    def _format_learned_rules_for_prompt(self) -> str:
        """Formate les règles apprises pour inclusion dans le prompt.

        Returns:
            Texte formaté des règles ou chaîne vide si aucune règle
        """
        if not self.learned_rules:
            return ""

        rules_text = "\n\n📚 RÈGLES APPRISES (à appliquer systématiquement) :\n"
        rules_text += "Ces règles ont été apprises des enrichissements manuels précédents.\n\n"

        for rule in self.learned_rules:
            champ = rule.get("champ", "")
            prompt_addition = rule.get("prompt_addition", "")
            if champ and prompt_addition:
                rules_text += f"Pour le champ '{champ}':\n{prompt_addition}\n\n"

        return rules_text

    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcule le hash MD5 d'un fichier.

        Args:
            file_path: Chemin vers le fichier

        Returns:
            Hash MD5 du fichier
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _compute_bytes_hash(self, data: bytes) -> str:
        """Calcule le hash MD5 de données binaires.

        Args:
            data: Données binaires

        Returns:
            Hash MD5
        """
        return hashlib.md5(data).hexdigest()

    def _parse_enhanced_analysis(self, response_text: str) -> Dict:
        """Parse la réponse enrichie de Claude avec caractéristiques structurées.

        Args:
            response_text: Texte de la réponse Claude

        Returns:
            Dictionnaire avec résumé, mots-clés, thèmes et caractéristiques
        """
        result = {
            "summary": "",
            "keywords": "",
            "themes": "",
            "characteristics": {
                "materials": [],
                "focus_areas": [],
                "methodology": [],
                "structure_types": [],
                "geographical_scope": "",
                "project_phase": "",
                "equipment": [],
                "team_members": [],
                "team_roles": [],
                "special_sections": {},
                "project_references": [],
                "target_projects": []
            },
            "illustrations_from_text": []
        }

        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("RÉSUMÉ:"):
                result["summary"] = line.replace("RÉSUMÉ:", "").strip()
            elif line.startswith("MOTS-CLÉS:"):
                result["keywords"] = line.replace("MOTS-CLÉS:", "").strip()
            elif line.startswith("THÈMES:"):
                result["themes"] = line.replace("THÈMES:", "").strip()
            elif line.startswith("MATÉRIAUX:"):
                value = line.replace("MATÉRIAUX:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["materials"] = [m.strip() for m in value.split(",")]
            elif line.startswith("DOMAINES:"):
                value = line.replace("DOMAINES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["focus_areas"] = [d.strip() for d in value.split(",")]
            elif line.startswith("MÉTHODOLOGIE:"):
                value = line.replace("MÉTHODOLOGIE:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["methodology"] = [m.strip() for m in value.split(",")]
            elif line.startswith("TYPES:"):
                value = line.replace("TYPES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["structure_types"] = [t.strip() for t in value.split(",")]
            elif line.startswith("PORTÉE:"):
                value = line.replace("PORTÉE:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["geographical_scope"] = value
            elif line.startswith("PHASE:"):
                value = line.replace("PHASE:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["project_phase"] = value
            elif line.startswith("ÉQUIPEMENTS:"):
                value = line.replace("ÉQUIPEMENTS:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["equipment"] = [e.strip() for e in value.split(",")]
            elif line.startswith("MEMBRES:"):
                value = line.replace("MEMBRES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["team_members"] = [m.strip() for m in value.split(",")]
            elif line.startswith("RÔLES:"):
                value = line.replace("RÔLES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["team_roles"] = [r.strip() for r in value.split(",")]
            elif line.startswith("RÉFÉRENCES:"):
                value = line.replace("RÉFÉRENCES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["project_references"] = [r.strip() for r in value.split(",")]
            elif line.startswith("CIBLES:"):
                value = line.replace("CIBLES:", "").strip()
                if value and value.lower() != "non spécifié":
                    result["characteristics"]["target_projects"] = [e.strip() for e in value.split(",")]
            elif line.startswith("ILLUSTR:"):
                value = line.replace("ILLUSTR:", "").strip()
                if value and value.lower() != "non spécifié":
                    illustration = {}
                    parts = value.split("|")
                    for part in parts:
                        part = part.strip()
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip()
                            if key == "cat":
                                illustration["category"] = val
                            elif key == "type":
                                illustration["type"] = val
                            elif key == "desc":
                                illustration["description"] = val
                            elif key == "keys":
                                illustration["technical_keywords"] = [k.strip() for k in val.split(",") if k.strip()]
                            elif key == "ctx":
                                illustration["context"] = val

                    if illustration:
                        illustration["detection_method"] = "analyse textuelle (Claude)"
                        illustration["confidence"] = "medium"
                        result["illustrations_from_text"].append(illustration)
            elif line.startswith("- ") and ":" in line:
                parts = line[2:].split(":", 1)
                if len(parts) == 2:
                    section_name = parts[0].strip()
                    section_summary = parts[1].strip()

                    if section_summary.startswith("{") or section_summary.startswith("["):
                        if "'titre':" in section_summary or '"titre":' in section_summary:
                            import re
                            match = re.search(r"['\"]titre['\"]:\s*['\"]([^'\"]+)['\"]", section_summary)
                            if match:
                                section_summary = match.group(1)
                            else:
                                continue
                        else:
                            continue

                    if section_name and section_summary and section_name.lower() not in ["aucun", "(aucun)", "none", "n/a"]:
                        result["characteristics"]["special_sections"][section_name] = section_summary

        return result

    def _generate_enhanced_summary(self, text: str, filename: str) -> Dict:
        """Génère un résumé enrichi avec caractéristiques structurées via Claude.

        Args:
            text: Texte du document
            filename: Nom du fichier

        Returns:
            Dictionnaire avec résumé, mots-clés, thèmes et caractéristiques
        """
        max_chars = 50000
        text_to_analyze = text[:max_chars]
        if len(text) > max_chars:
            text_to_analyze += "\n\n[... texte tronqué ...]"

        learned_rules_section = self._format_learned_rules_for_prompt()

        prompt = f"""Analysez ce mémoire technique et fournissez une analyse structurée :

1. RÉSUMÉ : Un résumé concis en 2-3 phrases du contenu principal

2. MOTS-CLÉS : 5-10 mots-clés/concepts principaux (séparés par des virgules)

3. THÈMES : 2-5 thèmes principaux (séparés par des virgules)

4. CARACTÉRISTIQUES STRUCTURÉES :

   MATÉRIAUX : Types de matériaux mentionnés (ex: béton armé, maçonnerie, acier)
   Listez uniquement ceux EXPLICITEMENT mentionnés, séparés par des virgules.

   DOMAINES : Domaines d'intervention (ex: diagnostic, réhabilitation, instrumentation)
   Listez 2-4 domaines, séparés par des virgules.

   MÉTHODOLOGIE : Méthodes utilisées (ex: analyse modale, auscultation, carottages)
   Listez les méthodes spécifiques, séparées par des virgules.

   TYPES : Types de structures (ex: pont, viaduc, bâtiment)
   Listez les types mentionnés, séparés par des virgules.

   PORTÉE : Portée géographique (ex: Département de l'Allier, national, site spécifique)
   Indiquez la portée en 1-3 mots.

   PHASE : Phase de projet (ex: diagnostic, conception, exécution, suivi)
   Indiquez la phase principale.

   ÉQUIPEMENTS : Matériels et équipements spécifiques mentionnés
   Pour matériel SPÉCIFIQUE/DISTINCTIF: listez précisément (ex: géoradar, corrosimètre, nacelle positive, waders, passerelle ABC130)
   Pour matériel COMMUN: utilisez la famille (ex: matériels de mesure, matériels de débroussaillage)
   Séparés par des virgules.

   MEMBRES : Noms des personnes mentionnées dans l'équipe (ex: Lionel, Houssem, David, Alaa)
   Séparés par des virgules. Mettez "non spécifié" si aucun nom.

   RÔLES : Compétences et rôles de l'équipe (ex: ingénieur structure, alpiniste cordiste, chef de projet)
   Séparés par des virgules. Mettez "non spécifié" si aucun.

   RÉFÉRENCES : Projets/missions de référence mentionnés pour crédibiliser (ex: Pont d'Orbeil, Viaduc de Rive de Gier)
   Listez les projets spécifiques mentionnés comme références ou réalisations antérieures, séparés par des virgules.
   Mettez "non spécifié" si aucun.

   CIBLES : Projets/bâtiments qui sont l'objet de cet appel d'offres ou de cette mission (ex: bâtiment siège SEMITAN, hangar Trocardière)
   Ce sont les ouvrages/projets pour lesquels ce mémoire technique est rédigé, PAS des exemples passés.
   Séparés par des virgules. Mettez "non spécifié" si aucun.

5. ILLUSTRATIONS EXCEPTIONNELLES : Identifiez les illustrations techniques pertinentes avec leurs détails

   Cherchez les passages où une illustration technique est présente ou devrait logiquement exister :
   - Mentions explicites : "Figure X", "Schéma ci-dessous", "Photo en annexe", graphique, tableau, etc.
   - Méthodes/protocoles décrits sous forme de liste suggérant un schéma/photo
   - Résultats présentés (courbes, graphiques, tableaux de mesures)
   - Modélisations, calculs, simulations numériques
   - Préconisations de réparation/renforcement avec schémas
   - Équipements, installations, configurations techniques

   Pour chaque illustration pertinente, identifiez :

   CATÉGORIE (choisir UNE catégorie principale) :
   - Investigation : photos/schémas d'équipements terrain, protocoles d'essais, installations de mesure
   - Analyse : graphiques de résultats, courbes, tableaux de mesures, cartographies
   - Modélisation : modèles numériques (éléments finis, etc.), schémas de calcul, diagrammes structurels
   - Préconisation : schémas de réparation/renforcement, solutions techniques, plans d'intervention
   - Méthodologie : organigrammes, processus, planning, organisation

   DESCRIPTION DÉTAILLÉE : Décrivez PRÉCISÉMENT ce que montre l'illustration :
   - Équipements visibles : géoradar, carotteuse, ferroscan, accéléromètres, etc.
   - Techniques montrées : renforcement par plats carbone, injection résine, sondages géotechniques, etc.
   - Type de résultats : courbes charge-déplacement, cartographies de défauts, modèle 3D, etc.
   - Détails techniques importants : dimensions, matériaux, méthodes de fixation, etc.

   MOTS-CLÉS TECHNIQUES (3-5 mots-clés spécifiques à cette illustration) :
   Exemples : plats carbone, modèle éléments finis, courbe fréquentielle, carottage diamant, etc.

   Format de réponse (une illustration par ligne) :
   ILLUSTR: CAT=[catégorie] | TYPE=[schéma/photo/graphique/plan] | DESC=[description détaillée] | KEYS=[mot-clé1, mot-clé2, mot-clé3] | CTX=[contexte court]

   Si aucune illustration pertinente détectée, mettez "non spécifié".

6. ASPECTS TECHNIQUES DISTINCTIFS : Identifiez le CONTENU technique DISTINCTIF du document (PAS la structure organisationnelle, PAS les aspects environnementaux génériques)

   ⚠️ NE CHERCHEZ PAS les titres de sections du document (comme "Méthodologie", "Organisation", etc.)
   ✅ CHERCHEZ PLUTÔT le contenu technique spécifique qui rend ce document unique

   🚫 ANTI-HALLUCINATION - RÈGLE CRITIQUE :
   - N'incluez QUE les aspects EXPLICITEMENT présents et DÉTAILLÉS dans le document
   - Si un aspect n'est pas clairement décrit dans le texte, NE L'INCLUEZ PAS
   - Il est PRÉFÉRABLE de lister MOINS d'aspects (ou AUCUN) plutôt que d'inventer
   - Pour un devis, une offre commerciale ou un document court, il peut n'y avoir AUCUN aspect technique distinctif - c'est NORMAL, répondez alors "ASPECTS: (aucun)"
   - Chaque aspect listé DOIT correspondre à un contenu RÉEL et VÉRIFIABLE dans le document
   - NE PAS inférer ou deviner des aspects basés sur le type de projet ou le contexte général

   PRIORITÉ ABSOLUE - Identifiez ces éléments techniques qui DISTINGUENT ce document :

   A. ASPECTS TECHNIQUES NORMATIFS ET RÉGLEMENTAIRES :
   - Normes et réglements spécifiques appliqués (ex: Eurocodes, DTU, normes NF)
   - ⚠️ N'incluez une section normative QUE si le document DÉTAILLE réellement des normes ou règlements précis (numéros de normes, articles, exigences spécifiques)
   - La simple MENTION de normes dans un contexte général ne suffit PAS à créer une section spéciale
   - Si une section normative est justifiée, incluez les mots "Normes" et "Règlements" dans le nom
   - Référentiels techniques particuliers
   - Exigences réglementaires spécifiques au projet

   B. CALCULS ET DIMENSIONNEMENTS DÉTAILLÉS :
   - Exemples de calculs structurels (ex: calcul poutre HEA180, dimensionnement chevêtre)
   - Calculs spécifiques (ex: plancher collaborant, hangar aéronautique, trémies)
   - Notes de calcul détaillées
   - Vérifications aux états limites

   C. MÉTHODOLOGIES ET APPROCHES TECHNIQUES :
   - Notes méthodologiques spécifiques (ex: limitations géoradar sur planchers collaborants)
   - Protocoles techniques particuliers
   - Articulations entre disciplines (ex: coordination béton armé / charpente métallique)
   - Démarches d'optimisation techniques (optimisation structurelle, optimisation coûts/matériaux)

   D. QUALITÉ ET CONTRÔLES :
   - Plans d'Assurance Qualité (PAQ) détaillés
   - Procédures de contrôle spécifiques
   - Points d'arrêt et points critiques

   E. ASPECTS TEMPORELS ET ORGANISATIONNELS TECHNIQUES :
   - Phasage technique spécifique
   - Mesures techniques pour respecter délais
   - Contraintes d'exploitation particulières

   ⚠️ IGNOREZ les sections génériques suivantes (présentes dans beaucoup de documents) :
   - Gestion des déchets, tri, recyclage
   - Charte éco-responsable, engagements environnementaux généraux
   - Modalités de déplacement, covoiturage
   - Formation et sensibilisation générale
   - Sauf si elles contiennent des aspects techniques très spécifiques

   ⚠️ IMPORTANT - Noms des aspects :
   - Utilisez des noms DESCRIPTIFS et RECHERCHABLES (ex: "Normes Eurocodes", "PAQ détaillé", "Calculs plancher collaborant")
   - Pas de noms génériques comme "Aspects normatifs" ou "Gestion qualité"
   - Soyez SPÉCIFIQUE: si Eurocodes EC0/EC1/EC3 sont mentionnés, écrivez "Application Eurocodes EC0 EC1 EC3"
   - Si PAQ est détaillé, écrivez "PAQ - Plan Assurance Qualité" ou "Plan Assurance Qualité détaillé"
   - Si calculs spécifiques, listez-les: "Calcul plancher collaborant", "Dimensionnement chevêtre"

   ⚠️ FORMAT OBLIGATOIRE (chaque ligne DOIT avoir les deux-points ":") :
   - Nom aspect: détail spécifique (max 10 mots)

   TOUJOURS respecter: "- [Nom]: [description courte]"
   JAMAIS juste: "- [Nom]" (SANS description)

   Limitez-vous aux 5-8 aspects LES PLUS DISTINCTIFS techniquement.
   Si le document ne contient aucun aspect technique distinctif (ex: devis, offre commerciale simple), répondez simplement "ASPECTS: (aucun)"
{learned_rules_section}
Nom du fichier : {filename}

Contenu :
{text_to_analyze}

FORMAT DE RÉPONSE STRICT :
RÉSUMÉ: [résumé]
MOTS-CLÉS: [mot1, mot2, ...]
THÈMES: [thème1, thème2, ...]
MATÉRIAUX: [mat1, mat2, ...] (ou "non spécifié")
DOMAINES: [dom1, dom2, ...]
MÉTHODOLOGIE: [méth1, méth2, ...] (ou "non spécifié")
TYPES: [type1, type2, ...] (ou "non spécifié")
PORTÉE: [portée]
PHASE: [phase]
ÉQUIPEMENTS: [équip1, équip2, ...] (ou "non spécifié")
MEMBRES: [nom1, nom2, ...] (ou "non spécifié")
RÔLES: [rôle1, rôle2, ...] (ou "non spécifié")
RÉFÉRENCES: [projet1, projet2, ...] (ou "non spécifié")
CIBLES: [projet/bâtiment1, projet/bâtiment2, ...] (ou "non spécifié")
ILLUSTR: CAT=[catégorie] | TYPE=[schéma/photo/graphique/plan] | DESC=[description détaillée] | KEYS=[mot-clé1, mot-clé2, mot-clé3] | CTX=[contexte court]
ILLUSTR: CAT=[catégorie2] | TYPE=[type2] | DESC=[description2] | KEYS=[keys2] | CTX=[contexte2] (si plusieurs illustrations)
ASPECTS:
⚠️ NE COPIE PAS les exemples ci-dessous ! Ils montrent juste le FORMAT attendu.
N'inclus QUE les aspects RÉELLEMENT présents et détaillés dans CE document.

Format attendu (exemples de FORMAT, pas de contenu à copier):
- [Nom de l'aspect réel du document]: [description courte, max 10 mots]
- [Autre aspect réel]: [sa description]

Exemples de TYPES d'aspects (à adapter au contenu réel):
- Si le doc parle de normes spécifiques → "Normes [lesquelles]: [application]"
- Si le doc a un PAQ détaillé → "PAQ: [ce qu'il couvre]"
- Si le doc a des calculs spécifiques → "[Type de calcul]: [objet]"

PAS comme ceci:
- Chapitre 1 (Compréhension): présentation des objectifs ← titres de chapitres
- Méthodologie: protocoles d'investigation ← trop générique
- rse: {{'titre': '...', 'sous_sections': [...]}} ← pas de dictionnaires !

⚠️ JAMAIS de dictionnaires, listes, accolades {{}} ou crochets []
⚠️ Si aucun aspect distinctif n'est trouvé, répondre "ASPECTS: (aucun)" """

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # DEBUG: Sauvegarder la réponse brute pour diagnostic
            debug_file = Path("debug_claude_response.txt")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== RÉPONSE CLAUDE POUR {filename} ===\n\n")
                f.write(response_text)
                f.write("\n\n=== FIN RÉPONSE ===\n")

            return self._parse_enhanced_analysis(response_text)

        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé: {e}")
            return {
                "summary": "Erreur lors de la génération du résumé",
                "keywords": "",
                "themes": "",
                "characteristics": {
                    "materials": [],
                    "focus_areas": [],
                    "methodology": [],
                    "structure_types": [],
                    "geographical_scope": "",
                    "project_phase": "",
                    "equipment": [],
                    "team_members": [],
                    "team_roles": [],
                    "special_sections": {},
                    "project_references": [],
                    "target_projects": []
                },
                "illustrations_from_text": []
            }

    def _find_similar_documents(
        self, current_doc_metadata: Dict, index: Dict, file_hash: str
    ) -> List[Dict]:
        """Trouve les documents similaires au document actuel."""
        existing_docs = [
            doc for doc in index["documents"] if doc["file_hash"] != file_hash
        ]

        if len(existing_docs) < 1:
            return []

        source_keywords = set(
            k.strip().lower()
            for k in current_doc_metadata["keywords"].split(",")
            if k.strip()
        )
        source_themes = set(
            t.strip().lower()
            for t in current_doc_metadata["themes"].split(",")
            if t.strip()
        )

        scored_docs = []

        for doc in existing_docs:
            score = 0.0

            doc_keywords = set(
                k.strip().lower()
                for k in doc.get("keywords", "").split(",")
                if k.strip()
            )
            common_keywords = source_keywords & doc_keywords
            score += len(common_keywords) * 5.0

            doc_themes = set(
                t.strip().lower()
                for t in doc.get("themes", "").split(",")
                if t.strip()
            )
            common_themes = source_themes & doc_themes
            score += len(common_themes) * 3.0

            if "characteristics" in doc and "characteristics" in current_doc_metadata:
                current_materials = set(
                    m.lower() for m in current_doc_metadata["characteristics"]["materials"]
                )
                doc_materials = set(
                    m.lower() for m in doc["characteristics"].get("materials", [])
                )
                score += len(current_materials & doc_materials) * 2.0

                current_focus = set(
                    f.lower() for f in current_doc_metadata["characteristics"]["focus_areas"]
                )
                doc_focus = set(
                    f.lower() for f in doc["characteristics"].get("focus_areas", [])
                )
                score += len(current_focus & doc_focus) * 2.0

                current_equipment = set(
                    e.lower() for e in current_doc_metadata["characteristics"].get("equipment", [])
                )
                doc_equipment = set(
                    e.lower() for e in doc["characteristics"].get("equipment", [])
                )
                score += len(current_equipment & doc_equipment) * 3.0

                current_members = set(
                    m.lower() for m in current_doc_metadata["characteristics"].get("team_members", [])
                )
                doc_members = set(
                    m.lower() for m in doc["characteristics"].get("team_members", [])
                )
                score += len(current_members & doc_members) * 1.0

                current_roles = set(
                    r.lower() for r in current_doc_metadata["characteristics"].get("team_roles", [])
                )
                doc_roles = set(
                    r.lower() for r in doc["characteristics"].get("team_roles", [])
                )
                score += len(current_roles & doc_roles) * 1.0

            if score >= config.DIFFERENTIAL_ANALYSIS_THRESHOLD:
                similar_doc = {
                    "file_hash": doc["file_hash"],
                    "filename": doc["filename"],
                    "similarity_score": score,
                    "common_keywords": list(common_keywords),
                    "common_themes": list(common_themes),
                    "summary": doc.get("summary", "")
                }
                scored_docs.append(similar_doc)

        scored_docs.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_docs[:config.MAX_DIFFERENTIAL_COMPARISONS]

    def _generate_distinctions(
        self, current_doc: Dict, similar_docs: List[Dict], text: str
    ) -> Dict:
        """Génère l'analyse différentielle comparant le document actuel aux similaires."""
        if not similar_docs:
            return {
                "unique_aspects": "Premier document de ce type dans l'index",
                "differentiators": [],
                "positioning": "Document de référence"
            }

        similar_summaries = "\n".join([
            f"- {doc['filename']}: {doc['summary'][:200]}"
            for doc in similar_docs
        ])

        prompt = f"""Vous êtes un expert en analyse de mémoires techniques.

DOCUMENT ACTUEL :
Nom : {current_doc['filename']}
Résumé : {current_doc['summary']}
Mots-clés : {current_doc['keywords']}

DOCUMENTS SIMILAIRES DÉJÀ INDEXÉS :
{similar_summaries}

TÂCHE : Identifiez ce qui rend le DOCUMENT ACTUEL DIFFÉRENT et UNIQUE par rapport aux documents similaires.

1. ASPECTS UNIQUES : En 1-2 phrases, qu'est-ce qui le distingue ?
2. DIFFÉRENCIATEURS : Listez 2-4 éléments concrets qui le différencient (format : "- différenciateur")
3. POSITIONNEMENT : En une phrase, comment le positionner ?

Extrait du document actuel (pour affiner l'analyse) :
{text[:10000]}

FORMAT DE RÉPONSE STRICT :
UNIQUE: [description]
DIFFÉRENCIATEURS:
- [diff1]
- [diff2]
POSITIONNEMENT: [positionnement]"""

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            unique_aspects = ""
            differentiators = []
            positioning = ""

            in_diff_section = False

            for line in response_text.split("\n"):
                line = line.strip()

                if line.startswith("UNIQUE:"):
                    unique_aspects = line.replace("UNIQUE:", "").strip()
                elif line.startswith("DIFFÉRENCIATEURS:"):
                    in_diff_section = True
                elif line.startswith("POSITIONNEMENT:"):
                    in_diff_section = False
                    positioning = line.replace("POSITIONNEMENT:", "").strip()
                elif in_diff_section and line.startswith("-"):
                    differentiators.append(line[1:].strip())

            return {
                "unique_aspects": unique_aspects,
                "differentiators": differentiators,
                "positioning": positioning
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse différentielle: {e}")
            return {
                "unique_aspects": "Analyse différentielle non disponible",
                "differentiators": [],
                "positioning": ""
            }

    def _correlate_illustrations(
        self,
        illustrations_from_text: List[Dict],
        images_metadata: Dict,
        zones: List[Dict],
        img_extractor: ImageExtractor,
        text: str
    ) -> List[Dict]:
        """Corrèle les illustrations détectées par Claude avec celles extraites du document."""
        special_illustrations = []

        for illust in illustrations_from_text:
            special_illustrations.append({
                "type": illust.get("type", "illustration méthodologique"),
                "description": illust.get("description", ""),
                "context": illust.get("context", ""),
                "detection_method": "analyse textuelle (Claude)",
                "confidence": "medium"
            })

        correlated = img_extractor.correlate_zones_and_images(
            zones, images_metadata, text
        )

        for illust in correlated:
            is_duplicate = False
            illust_context = illust.get("context", "").lower()

            for existing in special_illustrations:
                existing_context = existing.get("context", "").lower()
                if illust_context and existing_context:
                    common_length = len(set(illust_context.split()) & set(existing_context.split()))
                    if common_length > 10:
                        is_duplicate = True
                        if "image" in illust.get("detection_method", ""):
                            existing["confidence"] = "high"
                            existing["detection_method"] = "corrélation texte + image"
                        break

            if not is_duplicate:
                special_illustrations.append(illust)

        confidence_order = {"high": 3, "medium": 2, "low": 1}
        special_illustrations.sort(
            key=lambda x: confidence_order.get(x.get("confidence", "low"), 0),
            reverse=True
        )

        return special_illustrations[:10]

    def _scan_directory(self, directory: Path) -> List[Path]:
        """Scanne un répertoire pour trouver les documents supportés."""
        files = []
        for ext in config.SUPPORTED_EXTENSIONS:
            files.extend(directory.rglob(f"*{ext}"))
        return files

    def get_files_to_process(self, path: Path) -> List[Path]:
        """Retourne la liste des fichiers à traiter pour un chemin donné."""
        if not path.exists():
            return []

        if path.is_file():
            return [path] if not path.name.startswith('~$') else []

        files = self._scan_directory(path)
        files = [f for f in files if not f.name.startswith('~$')]
        return files

    def _load_existing_index(self) -> Dict:
        """Charge l'index existant via le storage backend."""
        data = self.storage.read_json("index")
        if data:
            return data
        return {"documents": [], "last_updated": None}

    def _save_index(self, index: Dict):
        """Sauvegarde l'index via le storage backend."""
        index["last_updated"] = datetime.now().isoformat()
        self.storage.write_json("index", index)
        logger.info("Index sauvegardé")

    def index_single_file(self, file_path: Path, force_reindex: bool = False, user: str = "David") -> Dict:
        """Indexe un seul fichier.

        Args:
            file_path: Chemin du fichier
            force_reindex: Si True, réindexe même si déjà indexé
            user: Nom de l'utilisateur qui indexe

        Returns:
            Dict avec statut: "indexed", "skipped", ou "error"
        """
        if not file_path.exists() or not file_path.is_file():
            return {"status": "error", "message": "Fichier introuvable"}

        index = self._load_existing_index()
        existing_docs = {doc["file_hash"]: doc for doc in index["documents"]}

        file_hash = self._compute_file_hash(file_path)

        if not force_reindex and file_hash in existing_docs:
            return {"status": "skipped", "message": "Déjà indexé"}

        existing_special_illustrations = None
        existing_manual_enrichments = None
        existing_document_format = None
        if file_hash in existing_docs:
            existing_doc = existing_docs[file_hash]
            existing_special_illustrations = existing_doc.get("special_illustrations")
            existing_manual_enrichments = existing_doc.get("manual_enrichments")
            existing_document_format = existing_doc.get("document_format")
            index["documents"] = [d for d in index["documents"] if d["file_hash"] != file_hash]

        text, page_count = self.extractor.extract_with_metadata(file_path)

        if not text:
            return {"status": "error", "message": "Échec de l'extraction du texte"}

        format_type = "court" if page_count and page_count <= 10 else "standard"

        metadata = self._generate_enhanced_summary(text, file_path.name)

        doc_entry = {
            "filename": file_path.name,
            "file_path": str(file_path.absolute()),
            "file_hash": file_hash,
            "summary": metadata["summary"],
            "keywords": metadata["keywords"],
            "themes": metadata["themes"],
            "characteristics": metadata["characteristics"],
            "page_count": page_count,
            "format_type": format_type,
            "special_illustrations": metadata.get("illustrations_from_text", []),
            "indexed_at": datetime.now().isoformat(),
            "analysis_version": "2.0",
            # Nouveaux champs de traçabilité
            "status": "indexe_non_valide",
            "indexed_by": user,
            "validated_by": None,
            "validated_at": None,
            "enriched_by": [],
            "last_enriched_by": None,
            "gdrive_file_id": None,
            "gdrive_link": None,
        }

        if existing_special_illustrations:
            manual_illusts = [i for i in existing_special_illustrations
                           if i.get("detection_method") == "enrichissement manuel"]
            if manual_illusts:
                doc_entry["special_illustrations"].extend(manual_illusts)

        if existing_manual_enrichments:
            doc_entry["manual_enrichments"] = existing_manual_enrichments
            doc_entry["manually_enriched"] = True

        if existing_document_format:
            doc_entry["document_format"] = existing_document_format

        index["documents"].append(doc_entry)
        self._save_index(index)

        return {
            "status": "indexed",
            "message": "Indexé avec succès",
            "filename": file_path.name,
            "doc_entry": doc_entry,
        }

    def index_from_drive(self, doc_id: str, doc_name: str, force_reindex: bool = False, user: str = "David") -> Dict:
        """Indexe un document depuis Google Drive.

        Télécharge le fichier en local temporaire, l'indexe, puis ajoute les métadonnées Drive.
        """
        storage = config.get_storage()

        # Télécharger le document
        data = storage.download_document(doc_id)
        if not data:
            return {"status": "error", "message": "Impossible de télécharger le document depuis le Drive"}

        # Écrire dans un fichier temporaire avec le bon suffixe
        suffix = Path(doc_name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        try:
            # Calculer le hash avant indexation pour retrouver le document après
            file_hash = self._compute_file_hash(tmp_path)

            result = self.index_single_file(tmp_path, force_reindex=force_reindex, user=user)

            # Si indexé avec succès, mettre à jour les métadonnées Drive
            if result["status"] == "indexed":
                index = self._load_existing_index()
                for doc in index["documents"]:
                    if doc["file_hash"] == file_hash:
                        doc["filename"] = doc_name
                        doc["file_path"] = ""
                        doc["gdrive_file_id"] = doc_id
                        doc["gdrive_link"] = storage.get_document_link(doc_id)
                        break
                self._save_index(index)
                result["filename"] = doc_name

            return result
        finally:
            tmp_path.unlink(missing_ok=True)

    def index_directory(self, directory: Path, force_reindex: bool = False, user: str = "David"):
        """Indexe tous les documents d'un répertoire ou un fichier individuel."""
        if not directory.exists():
            logger.error(f"Chemin introuvable: {directory}")
            return

        if directory.is_file():
            logger.info(f"Traitement du fichier: {directory}")
            files = [directory]
        else:
            logger.info(f"Scan du répertoire: {directory}")
            files = self._scan_directory(directory)

        logger.info(f"Trouvé {len(files)} fichier(s)")

        index = self._load_existing_index()
        existing_docs = {doc["file_hash"]: doc for doc in index["documents"]}

        files = [f for f in files if not f.name.startswith('~$')]
        logger.info(f"Après filtrage des fichiers temporaires: {len(files)} fichier(s)")

        indexed_count = 0
        skipped_count = 0
        error_count = 0

        for file_path in files:
            logger.info(f"Traitement de: {file_path.name}")

            file_hash = self._compute_file_hash(file_path)

            if not force_reindex and file_hash in existing_docs:
                logger.info(f"  → Déjà indexé, ignoré")
                skipped_count += 1
                continue

            existing_special_illustrations = None
            if file_hash in existing_docs:
                existing_special_illustrations = existing_docs[file_hash].get("special_illustrations", None)
                if existing_special_illustrations:
                    logger.info(f"  → Préservation de {len(existing_special_illustrations)} illustration(s) enrichie(s) manuellement")

            text, page_count = self.extractor.extract_with_metadata(file_path)

            if not text:
                logger.warning(f"  → Échec de l'extraction")
                error_count += 1
                continue

            format_type = "court" if page_count and page_count <= 10 else "standard"
            if page_count:
                logger.info(f"  → {page_count} page(s) - Format: {format_type}")

            logger.info(f"  → Extraction des images et détection de zones...")
            img_extractor = ImageExtractor()
            images_metadata = img_extractor.extract_images_metadata(file_path, text)
            illustration_zones = img_extractor.detect_illustration_zones(text)

            logger.info(
                f"     Images: {images_metadata.get('image_count', 0)}, "
                f"Zones détectées: {len(illustration_zones)}"
            )

            logger.info(f"  → Phase 1: Analyse enrichie...")
            metadata = self._generate_enhanced_summary(text, file_path.name)

            logger.info(f"  → Corrélation des illustrations...")
            special_illustrations = self._correlate_illustrations(
                metadata.get("illustrations_from_text", []),
                images_metadata,
                illustration_zones,
                img_extractor,
                text
            )

            if special_illustrations:
                logger.info(f"     {len(special_illustrations)} illustration(s) exceptionnelle(s) détectée(s)")

            final_illustrations = existing_special_illustrations if existing_special_illustrations else special_illustrations

            doc_entry = {
                "filename": file_path.name,
                "file_path": str(file_path.absolute()),
                "file_hash": file_hash,
                "file_size": file_path.stat().st_size,
                "file_modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                "text_length": len(text),
                "page_count": page_count,
                "format_type": format_type,
                "summary": metadata["summary"],
                "keywords": metadata["keywords"],
                "themes": metadata["themes"],
                "characteristics": metadata["characteristics"],
                "special_illustrations": final_illustrations,
                "image_metadata": {
                    "image_count": images_metadata.get("image_count", 0),
                    "source": images_metadata.get("source", ""),
                    "zones_detected": len(illustration_zones)
                },
                "indexed_at": datetime.now().isoformat(),
                "text_preview": text[:500],
                "analysis_version": "2.0",
                # Nouveaux champs de traçabilité
                "status": "indexe_non_valide",
                "indexed_by": user,
                "validated_by": None,
                "validated_at": None,
                "enriched_by": [],
                "last_enriched_by": None,
                "gdrive_file_id": None,
                "gdrive_link": None,
            }

            logger.info(f"  → Phase 2: Recherche de similarités...")
            similar_docs = self._find_similar_documents(metadata, index, file_hash)

            doc_entry["similar_documents"] = similar_docs
            doc_entry["compared_against"] = len(similar_docs)

            if similar_docs:
                logger.info(
                    f"  → Phase 3: Analyse différentielle "
                    f"({len(similar_docs)} documents similaires)..."
                )
                distinctions = self._generate_distinctions(
                    doc_entry, similar_docs, text
                )
            else:
                logger.info(f"  → Phase 3: Ignorée (aucun document similaire)")
                distinctions = {
                    "unique_aspects": "Premier document de ce type dans l'index",
                    "differentiators": [],
                    "positioning": "Document de référence"
                }

            doc_entry["distinctions"] = distinctions

            existing_docs[file_hash] = doc_entry
            indexed_count += 1
            logger.info(f"  ✓ Indexé avec succès")

            if indexed_count % 10 == 0:
                index["documents"] = list(existing_docs.values())
                self._save_index(index)
                logger.info(f"  💾 Sauvegarde progressive ({indexed_count} documents indexés)")

        index["documents"] = list(existing_docs.values())
        self._save_index(index)

        logger.info(f"\n=== Résumé de l'indexation ===")
        logger.info(f"Indexés: {indexed_count}")
        logger.info(f"Ignorés (déjà indexés): {skipped_count}")
        logger.info(f"Erreurs: {error_count}")
        logger.info(f"Total dans l'index: {len(index['documents'])}")


def main():
    """Point d'entrée principal."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Indexe les mémoires techniques"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Répertoire ou fichier à indexer (défaut: LOCAL_DOCS_PATH du .env)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force la réindexation de tous les fichiers"
    )

    args = parser.parse_args()

    if args.directory:
        directory = Path(args.directory)
    elif config.LOCAL_DOCS_PATH:
        directory = Path(config.LOCAL_DOCS_PATH)
    else:
        print("Erreur: Spécifiez un répertoire ou configurez LOCAL_DOCS_PATH dans .env")
        sys.exit(1)

    indexer = DocumentIndexer()
    indexer.index_directory(directory, force_reindex=args.force)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()
