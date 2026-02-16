"""Trouve les documents similaires à un nouveau projet ou document."""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import sys
from datetime import datetime, timedelta

from anthropic import Anthropic

from extractor import TextExtractor
import config

logger = logging.getLogger(__name__)


class SimilarityFinder:
    """Trouve les documents similaires."""

    # Synonymes pour améliorer la recherche
    SYNONYMES = {
        "pont": ["viaduc", "ouvrage d'art", "passerelle"],
        "viaduc": ["pont", "ouvrage d'art"],
        "passerelle": ["pont", "ouvrage d'art"],
        "bâtiment": ["immeuble", "édifice", "construction"],
        "immeuble": ["bâtiment", "édifice"],
        "diagnostic": ["expertise", "analyse", "évaluation", "inspection"],
        "expertise": ["diagnostic", "analyse"],
        "fissure": ["fissuration", "désordre", "pathologie"],
        "fissuration": ["fissure", "désordre"],
        "béton": ["béton armé", "ba"],
        "vibratoire": ["vibration", "dynamique", "modal", "modale"],
        "vibration": ["vibratoire", "dynamique"],
        "modal": ["modale", "vibratoire", "dynamique"],
        "renforcement": ["réparation", "confortement", "réhabilitation"],
        "réparation": ["renforcement", "réhabilitation"],
        "réhabilitation": ["rénovation", "renforcement", "réparation"],
    }

    def __init__(self):
        """Initialise le chercheur de similarité."""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY non définie. "
                "Créez un fichier .env avec votre clé API."
            )

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.extractor = TextExtractor()
        self.storage = config.get_storage()
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Charge l'index via le storage backend.

        Returns:
            L'index chargé
        """
        data = self.storage.read_json("index")
        if data:
            return data

        logger.error("Index introuvable. Exécutez d'abord: python indexer.py <répertoire>")
        return {"documents": []}

    def _expand_with_synonyms(self, words: set) -> set:
        """Étend un ensemble de mots avec leurs synonymes.

        Args:
            words: Ensemble de mots à étendre

        Returns:
            Ensemble étendu avec les synonymes
        """
        expanded = set(words)
        for word in words:
            word_lower = word.lower()
            if word_lower in self.SYNONYMES:
                expanded.update(self.SYNONYMES[word_lower])
        return expanded

    def _analyze_document(self, file_path: Path) -> Optional[Dict]:
        """Analyse un nouveau document pour en extraire les caractéristiques.

        Args:
            file_path: Chemin vers le document

        Returns:
            Dictionnaire avec les métadonnées du document
        """
        # Extraire le texte
        text = self.extractor.extract(file_path)

        if not text:
            logger.error(f"Impossible d'extraire le texte de {file_path}")
            return None

        # Générer un résumé avec Claude
        max_chars = 50000
        text_to_analyze = text[:max_chars]

        prompt = f"""Analyse ce document et fournis :

1. Un résumé concis (2-3 phrases)
2. Les 5-10 mots-clés/concepts principaux (séparés par des virgules)
3. Les thèmes principaux abordés (2-5 thèmes, séparés par des virgules)
4. Le type de document (ex: appel d'offres, étude technique, rapport, proposition commerciale, etc.)

Nom du fichier : {file_path.name}

Contenu :
{text_to_analyze}

Réponds au format suivant :
RÉSUMÉ: [ton résumé]
MOTS-CLÉS: [mot1, mot2, mot3, ...]
THÈMES: [thème1, thème2, ...]
TYPE: [type de document]"""

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Parser la réponse
            summary = ""
            keywords = ""
            themes = ""
            doc_type = ""

            for line in response_text.split("\n"):
                if line.startswith("RÉSUMÉ:"):
                    summary = line.replace("RÉSUMÉ:", "").strip()
                elif line.startswith("MOTS-CLÉS:"):
                    keywords = line.replace("MOTS-CLÉS:", "").strip()
                elif line.startswith("THÈMES:"):
                    themes = line.replace("THÈMES:", "").strip()
                elif line.startswith("TYPE:"):
                    doc_type = line.replace("TYPE:", "").strip()

            return {
                "filename": file_path.name,
                "summary": summary,
                "keywords": keywords,
                "themes": themes,
                "type": doc_type,
                "text_preview": text[:500]
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {e}")
            return None

    def _analyze_description(self, description: str) -> Dict:
        """Analyse une description textuelle du nouveau projet.

        Args:
            description: Description du projet

        Returns:
            Dictionnaire avec les métadonnées
        """
        prompt = f"""Analyse cette description de projet et fournis :

1. Un résumé reformulé (2-3 phrases)
2. Les 5-10 mots-clés/concepts principaux (séparés par des virgules)
3. Les thèmes principaux (2-5 thèmes, séparés par des virgules)
4. Le type de document recherché (ex: appel d'offres, étude technique, etc.)

Description :
{description}

Réponds au format suivant :
RÉSUMÉ: [ton résumé]
MOTS-CLÉS: [mot1, mot2, mot3, ...]
THÈMES: [thème1, thème2, ...]
TYPE: [type de document]"""

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Parser la réponse
            summary = ""
            keywords = ""
            themes = ""
            doc_type = ""

            for line in response_text.split("\n"):
                if line.startswith("RÉSUMÉ:"):
                    summary = line.replace("RÉSUMÉ:", "").strip()
                elif line.startswith("MOTS-CLÉS:"):
                    keywords = line.replace("MOTS-CLÉS:", "").strip()
                elif line.startswith("THÈMES:"):
                    themes = line.replace("THÈMES:", "").strip()
                elif line.startswith("TYPE:"):
                    doc_type = line.replace("TYPE:", "").strip()

            return {
                "summary": summary,
                "keywords": keywords,
                "themes": themes,
                "type": doc_type
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {e}")
            return {
                "summary": description,
                "keywords": "",
                "themes": "",
                "type": ""
            }

    def _remove_accents(self, text: str) -> str:
        """Supprime les accents d'un texte.

        Args:
            text: Texte avec potentiellement des accents

        Returns:
            Texte sans accents
        """
        import unicodedata
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )

    def _normalize_words(self, words_iterable):
        """Normalise les mots en ajoutant les formes singulier/pluriel et sans accents.

        Pour chaque mot, ajoute aussi:
        - Sa forme sans ponctuation
        - Sa forme sans accents
        - Sa forme sans 's' ou 'x' final (pluriel français basique)
        """
        import string
        normalized = set()
        for word in words_iterable:
            # Nettoyer la ponctuation
            word_clean = word.strip(string.punctuation)
            if not word_clean:
                continue

            word_lower = word_clean.lower()
            word_no_accent = self._remove_accents(word_lower)

            # Ajouter les deux formes (avec et sans accent)
            normalized.add(word_lower)
            normalized.add(word_no_accent)

            # Ajouter la forme sans 's' ou 'x' final (singulier)
            if len(word_lower) > 3 and word_lower.endswith('s') and word_lower[-2] not in 'sxz':
                normalized.add(word_lower[:-1])
                normalized.add(word_no_accent[:-1])
            elif len(word_lower) > 3 and word_lower.endswith('x'):
                normalized.add(word_lower[:-1])
                normalized.add(word_no_accent[:-1])
        return normalized

    def _calculate_temporal_bonus(self, doc: Dict, base_score: float) -> float:
        """Calcule le bonus temporel basé sur la date d'indexation.

        Args:
            doc: Document avec métadonnées
            base_score: Score de base avant bonus

        Returns:
            Bonus temporel à ajouter au score
        """
        if not config.TEMPORAL_WEIGHTING_ENABLED:
            return 0.0

        # Récupérer la date d'indexation
        indexed_at = doc.get("indexed_at")
        if not indexed_at:
            return 0.0

        try:
            # Parser la date ISO format
            indexed_date = datetime.fromisoformat(indexed_at)
            now = datetime.now()
            age = now - indexed_date

            # Calculer le bonus selon l'âge
            if age < timedelta(days=90):  # < 3 mois
                bonus_multiplier = config.TEMPORAL_BONUS_RECENT
            elif age < timedelta(days=180):  # 3-6 mois
                bonus_multiplier = config.TEMPORAL_BONUS_MEDIUM
            elif age < timedelta(days=365):  # 6-12 mois
                bonus_multiplier = config.TEMPORAL_BONUS_OLD
            else:
                return 0.0  # Pas de bonus après 12 mois

            return base_score * bonus_multiplier

        except (ValueError, TypeError) as e:
            logger.warning(f"Erreur parsing date d'indexation: {e}")
            return 0.0

    def find_similar(
        self,
        source: str,
        is_file: bool = False,
        max_results: int = 5
    ) -> List[Dict]:
        """Trouve les documents similaires.

        Args:
            source: Chemin vers fichier ou description textuelle
            is_file: True si source est un chemin de fichier
            max_results: Nombre maximum de résultats

        Returns:
            Liste des documents similaires
        """
        if not self.index["documents"]:
            logger.warning("Index vide")
            return []

        # Analyser la source
        if is_file:
            source_metadata = self._analyze_document(Path(source))
            if not source_metadata:
                return []
        else:
            source_metadata = self._analyze_description(source)

        # Comparer avec tous les documents de l'index
        logger.info("Comparaison avec les documents indexés...")

        # Extraire les mots-clés et thèmes de la source (gérer liste ou chaîne)
        source_kw = source_metadata["keywords"]
        if isinstance(source_kw, list):
            source_keywords = set(k.strip().lower() for k in source_kw if k.strip())
        else:
            source_keywords = set(k.strip().lower() for k in source_kw.split(",") if k.strip())

        source_th = source_metadata["themes"]
        if isinstance(source_th, list):
            source_themes = set(t.strip().lower() for t in source_th if t.strip())
        else:
            source_themes = set(t.strip().lower() for t in source_th.split(",") if t.strip())

        # Détecter si la requête mentionne des illustrations
        illustration_terms = [
            "illustration", "schéma", "photo", "image", "diagramme",
            "figure", "dessin", "graphique", "plan", "croquis"
        ]
        query_lower = source.lower() if not is_file else source_metadata.get("summary", "").lower()
        query_mentions_illustrations = any(term in query_lower for term in illustration_terms)

        # Détecter si la requête demande un format court
        format_filter = None
        if "format court" in query_lower:
            format_filter = "court"
            # Retirer "format court" de la requête pour le matching
            query_lower = query_lower.replace("format court", "").strip()
        elif "format standard" in query_lower or "format long" in query_lower:
            format_filter = "standard"
            query_lower = query_lower.replace("format standard", "").replace("format long", "").strip()

        # Extraire les mots de la requête pour matcher avec les illustrations
        # Normaliser pour gérer singulier/pluriel
        query_words = self._normalize_words(query_lower.split())
        # Étendre avec les synonymes pour une meilleure couverture
        query_words_expanded = self._expand_with_synonyms(query_words)
        logger.info(f"Mots recherchés (avec synonymes): {query_words_expanded}")

        scored_docs = []

        # Filtrer les documents par format si demandé
        documents_to_search = self.index["documents"]
        if format_filter:
            documents_to_search = [
                doc for doc in self.index["documents"]
                if doc.get("format_type") == format_filter
            ]
            logger.info(f"Filtrage par format '{format_filter}': {len(documents_to_search)}/{len(self.index['documents'])} documents")

        for doc in documents_to_search:
            score = 0.0
            score_breakdown = {}  # Pour déboguer

            # NOUVEAU : Chercher dans le nom du fichier
            filename_lower = doc.get("filename", "").lower()
            filename_words = set(filename_lower.replace(".", " ").replace("-", " ").replace("_", " ").split())
            filename_matches = query_words & filename_words
            filename_score = len(filename_matches) * 8.0
            score += filename_score
            score_breakdown['filename'] = filename_score

            # Comparer les mots-clés (gérer liste ou chaîne)
            doc_kw = doc.get("keywords", "")
            if isinstance(doc_kw, list):
                doc_keywords = set(k.strip().lower() for k in doc_kw if k.strip())
            else:
                doc_keywords = set(k.strip().lower() for k in doc_kw.split(",") if k.strip())
            common_keywords = source_keywords & doc_keywords
            keywords_score = len(common_keywords) * 5.0
            score += keywords_score
            score_breakdown['keywords'] = keywords_score

            # Comparer les thèmes (gérer liste ou chaîne)
            doc_th = doc.get("themes", "")
            if isinstance(doc_th, list):
                doc_themes = set(t.strip().lower() for t in doc_th if t.strip())
            else:
                doc_themes = set(t.strip().lower() for t in doc_th.split(",") if t.strip())
            common_themes = source_themes & doc_themes
            themes_score = len(common_themes) * 3.0
            score += themes_score
            score_breakdown['themes'] = themes_score

            # Comparer les résumés (recherche de mots communs)
            source_words = set(source_metadata["summary"].lower().split())
            doc_words = set(doc.get("summary", "").lower().split())
            common_words = source_words & doc_words
            summary_score = len(common_words) * 0.5
            score += summary_score
            score_breakdown['summary'] = summary_score

            # NOUVEAU : Recherche directe des mots de la requête brute dans le résumé du document
            # Ceci permet de trouver des documents même si le mot n'est pas dans les mots-clés
            doc_summary_normalized = self._normalize_words(doc.get("summary", "").lower().split())
            direct_summary_matches = query_words_expanded & doc_summary_normalized
            direct_summary_score = len(direct_summary_matches) * 15.0  # Score très élevé pour match direct

            # Bonus supplémentaire si la phrase complète de la requête apparaît dans le résumé
            if len(query_lower.split()) >= 1:
                doc_summary_lower = doc.get("summary", "").lower()
                # Normaliser aussi le résumé pour la recherche de phrase
                doc_summary_normalized_str = self._remove_accents(doc_summary_lower)
                query_normalized = self._remove_accents(query_lower)
                if query_normalized in doc_summary_normalized_str:
                    direct_summary_score += 20.0  # Bonus pour match exact de phrase

            score += direct_summary_score
            score_breakdown['direct_summary'] = direct_summary_score

            # NOUVEAU : Recherche directe dans les mots-clés du document
            doc_kw_raw = doc.get("keywords", "")
            if isinstance(doc_kw_raw, list):
                doc_keywords_for_norm = (k.strip().lower() for k in doc_kw_raw if k.strip())
            else:
                doc_keywords_for_norm = (k.strip().lower() for k in doc_kw_raw.split(",") if k.strip())
            doc_keywords_normalized = self._normalize_words(doc_keywords_for_norm)
            direct_keywords_matches = query_words_expanded & doc_keywords_normalized
            direct_keywords_score = len(direct_keywords_matches) * 20.0  # Score très élevé pour match dans mots-clés
            score += direct_keywords_score
            score_breakdown['direct_keywords'] = direct_keywords_score

            # NOUVEAU : Scoring sur les caractéristiques (matériaux, méthodologie, équipements)
            if doc.get("characteristics"):
                chars = doc["characteristics"]

                # Extraire tous les mots des characteristics
                char_words = set()

                # Matériaux
                for material in chars.get("materials", []):
                    for word in material.lower().split():
                        char_words.add(word)

                # Méthodologie
                for method in chars.get("methodology", []):
                    for word in method.lower().split():
                        char_words.add(word)

                # Équipements
                for equip in chars.get("equipment", []):
                    for word in equip.lower().split():
                        char_words.add(word)

                # Domaines (focus_areas)
                for area in chars.get("focus_areas", []):
                    for word in area.lower().split():
                        char_words.add(word)

                # Types de structures
                for struct_type in chars.get("structure_types", []):
                    for word in struct_type.lower().split():
                        char_words.add(word)

                # Références projets (très important pour la recherche)
                for ref in chars.get("project_references", []):
                    for word in ref.lower().split():
                        char_words.add(word)

                # Projets cibles
                for target in chars.get("target_projects", []):
                    for word in target.lower().split():
                        char_words.add(word)

                # Matcher avec la requête (mots individuels)
                char_matching = query_words_expanded & char_words
                char_score = len(char_matching) * 4.0

                # BONUS pour correspondance de phrase complète (multi-mots)
                # Si la requête a 2+ mots et qu'on trouve la phrase exacte dans une caractéristique
                if len(query_lower.split()) >= 2:
                    # Vérifier si la phrase complète apparaît dans les matériaux
                    for material in chars.get("materials", []):
                        if query_lower in material.lower():
                            char_score += 20.0  # Bonus important pour match exact
                            break
                    # Vérifier dans la méthodologie
                    for method in chars.get("methodology", []):
                        if query_lower in method.lower():
                            char_score += 20.0
                            break
                    # Vérifier dans les équipements
                    for equip in chars.get("equipment", []):
                        if query_lower in equip.lower():
                            char_score += 20.0
                            break

                # BONUS IMPORTANT pour références projets (recherche par nom de projet)
                for ref in chars.get("project_references", []):
                    ref_lower = ref.lower()
                    # Vérifier chaque mot de la requête
                    ref_matches = sum(1 for word in query_words if word in ref_lower)
                    if ref_matches >= 2:
                        char_score += 30.0 * ref_matches  # Gros bonus si plusieurs mots matchent
                    elif ref_matches == 1:
                        char_score += 10.0

                # Bonus pour projets cibles
                for target in chars.get("target_projects", []):
                    target_lower = target.lower()
                    target_matches = sum(1 for word in query_words if word in target_lower)
                    if target_matches >= 1:
                        char_score += 15.0 * target_matches

                score += char_score
                score_breakdown['characteristics'] = char_score
            else:
                score_breakdown['characteristics'] = 0.0

            # NOUVEAU : Scoring basé sur les special_sections
            sections_score = 0.0
            if chars and chars.get("special_sections"):
                special_sections = chars["special_sections"]

                # Pour chaque section, matcher contre la requête
                for section_name, section_summary in special_sections.items():
                    section_text = f"{section_name} {section_summary}".lower()

                    # Vérifier si la phrase complète de la requête apparaît
                    if len(query_words) >= 2 and query_lower in section_text:
                        sections_score += 25.0  # Bonus très important pour phrase exacte
                    else:
                        # Compter les mots individuels qui matchent (avec normalisation pluriels)
                        section_words_raw = section_text.split()
                        section_words = self._normalize_words(section_words_raw)
                        matching_words = query_words_expanded & section_words

                        if len(matching_words) > 0:
                            # Points pour les mots matchés
                            # Bonus si TOUS les mots de la requête matchent dans cette section
                            if len(query_words) >= 2 and len(matching_words) == len(query_words):
                                sections_score += len(matching_words) * 7.0  # Bonus pour match complet
                            else:
                                sections_score += len(matching_words) * 5.0  # Points normaux

                score += sections_score
                score_breakdown['special_sections'] = sections_score
            else:
                score_breakdown['special_sections'] = 0.0

            # NOUVEAU : Scoring basé sur les illustrations (TOUJOURS actif)
            illust_desc_score = 0.0
            illust_keyword_score = 0.0
            if doc.get("special_illustrations"):
                illustrations = doc["special_illustrations"]

                # Bonus supplémentaire si la requête mentionne explicitement des illustrations
                if query_mentions_illustrations:
                    score += len(illustrations) * 2.0

                # Matcher les mots de la requête avec les descriptions d'illustrations
                for illust in illustrations:
                    # Extraire les mots des descriptions, contextes, catégories et mots-clés techniques
                    illust_text = (
                        illust.get("description", "") + " " +
                        illust.get("context", "") + " " +
                        illust.get("type", "") + " " +
                        illust.get("category", "")
                    ).lower()

                    # Ajouter les mots-clés techniques (nouveau champ enrichi)
                    # Gérer les séparateurs virgules ET point-virgules
                    if illust.get("technical_keywords"):
                        # Extraire tous les mots-clés en splitant sur "," et ";"
                        all_keywords = []
                        for kw in illust["technical_keywords"]:
                            # Splitter d'abord sur ";" puis sur ","
                            for part in kw.split(";"):
                                for subpart in part.split(","):
                                    cleaned = subpart.strip()
                                    if cleaned:
                                        all_keywords.append(cleaned.lower())

                        illust_text += " " + " ".join(all_keywords)

                    # Normaliser pour gérer singulier/pluriel
                    illust_words = self._normalize_words(illust_text.split())
                    matching_words = query_words_expanded & illust_words

                    # Calculer le score de base
                    base_desc_score = len(matching_words) * 3.0

                    # PÉNALITÉ TOTALE pour match partiel sur requête multi-mots
                    # Si la requête a 2+ mots et qu'on ne matche qu'une partie, score = 0
                    query_word_count = len(query_lower.split())
                    if query_word_count >= 2 and len(matching_words) < query_word_count:
                        base_desc_score = 0.0  # Aucun point pour match partiel

                    illust_desc_score += base_desc_score
                    score += base_desc_score

                    # Bonus TRÈS important si match sur mots-clés techniques (plus précis)
                    if illust.get("technical_keywords"):
                        # Extraire et nettoyer les mots-clés (gérer "," et ";")
                        # Puis splitter chaque mot-clé en mots individuels
                        tech_keywords_words = []
                        for kw in illust["technical_keywords"]:
                            for part in kw.split(";"):
                                for subpart in part.split(","):
                                    cleaned = subpart.strip()
                                    if cleaned:
                                        # Ajouter chaque mot du mot-clé
                                        tech_keywords_words.extend(cleaned.split())

                        # Normaliser pour gérer singulier/pluriel
                        tech_keywords_set = self._normalize_words(tech_keywords_words)
                        tech_matching = query_words_expanded & tech_keywords_set
                        keyword_match_score = len(tech_matching) * 5.0

                        # PÉNALITÉ TOTALE pour match partiel sur requête multi-mots
                        query_word_count = len(query_lower.split())
                        if query_word_count >= 2 and len(tech_matching) < query_word_count:
                            keyword_match_score = 0.0  # Aucun point pour match partiel

                        # BONUS pour correspondance de phrase complète dans les mots-clés
                        if query_word_count >= 2:
                            for kw in illust.get("technical_keywords", []):
                                if query_lower in kw.lower():
                                    keyword_match_score += 25.0  # Bonus très important pour phrase exacte
                                    break

                        illust_keyword_score += keyword_match_score
                        score += keyword_match_score

                    # DÉSACTIVÉ: Bonus "high confidence" donnait des points même sans match
                    # if illust.get("confidence") == "high":
                    #     score += 2.0

            score_breakdown['illustrations_desc'] = illust_desc_score
            score_breakdown['illustrations_keywords'] = illust_keyword_score

            # Appliquer le bonus temporel
            temporal_bonus = self._calculate_temporal_bonus(doc, score)
            score += temporal_bonus
            score_breakdown['temporal_bonus'] = temporal_bonus

            if score > 0:
                doc_with_score = doc.copy()
                doc_with_score["similarity_score"] = score
                doc_with_score["common_keywords"] = list(common_keywords)
                doc_with_score["common_themes"] = list(common_themes)
                doc_with_score["score_breakdown"] = score_breakdown  # Pour debug
                scored_docs.append(doc_with_score)

        # Trier par score décroissant
        scored_docs.sort(key=lambda x: x["similarity_score"], reverse=True)

        return scored_docs[:max_results]

    def display_results(
        self,
        results: List[Dict],
        source_metadata: Optional[Dict] = None
    ):
        """Affiche les résultats.

        Args:
            results: Liste des résultats
            source_metadata: Métadonnées de la source (optionnel)
        """
        if not results:
            print("\nAucun document similaire trouvé")
            return

        print(f"\n{'='*80}")
        print("DOCUMENTS SIMILAIRES TROUVÉS")
        print(f"{'='*80}\n")

        if source_metadata:
            print("Votre projet :")
            print(f"  Résumé: {source_metadata['summary']}")
            print(f"  Mots-clés: {source_metadata['keywords']}")
            print(f"  Thèmes: {source_metadata['themes']}")
            print(f"\n{'-'*80}\n")

        for i, doc in enumerate(results, 1):
            print(f"{i}. {doc['filename']}")
            print(f"   Score de similarité: {doc['similarity_score']:.1f}")

            # Afficher le détail du scoring
            if doc.get("score_breakdown"):
                breakdown = doc["score_breakdown"]
                print(f"   Detail du score:")
                if breakdown.get('filename', 0) > 0:
                    print(f"      - Nom fichier: {breakdown['filename']:.1f}")
                if breakdown.get('keywords', 0) > 0:
                    print(f"      - Mots-clés: {breakdown['keywords']:.1f}")
                if breakdown.get('themes', 0) > 0:
                    print(f"      - Thèmes: {breakdown['themes']:.1f}")
                if breakdown.get('characteristics', 0) > 0:
                    print(f"      - Caractéristiques: {breakdown['characteristics']:.1f}")
                if breakdown.get('illustrations_desc', 0) > 0:
                    print(f"      - Illustrations (desc): {breakdown['illustrations_desc']:.1f}")
                if breakdown.get('illustrations_keywords', 0) > 0:
                    print(f"      - Illustrations (mots-clés): {breakdown['illustrations_keywords']:.1f}")
                if breakdown.get('summary', 0) > 0:
                    print(f"      - Résumé: {breakdown['summary']:.1f}")
                if breakdown.get('direct_summary', 0) > 0:
                    print(f"      - Match direct résumé: {breakdown['direct_summary']:.1f}")
                if breakdown.get('temporal_bonus', 0) > 0:
                    print(f"      - Bonus temporel (récent): +{breakdown['temporal_bonus']:.1f}")

            print(f"   Chemin: {doc['file_path']}")

            if doc.get("common_keywords"):
                print(f"   Mots-clés communs: {', '.join(doc['common_keywords'])}")
            if doc.get("common_themes"):
                print(f"   Thèmes communs: {', '.join(doc['common_themes'])}")

            print(f"\n   Résumé du document:")
            print(f"   {doc['summary']}")
            print(f"\n   Mots-clés: {doc['keywords']}")
            print(f"   Thèmes: {doc['themes']}")

            # Afficher les caractéristiques structurées si disponibles
            if doc.get("characteristics"):
                chars = doc["characteristics"]
                print(f"\n   📋 Caractéristiques:")
                if chars.get("materials"):
                    print(f"      Matériaux: {', '.join(chars['materials'])}")
                if chars.get("focus_areas"):
                    print(f"      Domaines: {', '.join(chars['focus_areas'])}")
                if chars.get("methodology"):
                    print(f"      Méthodologie: {', '.join(chars['methodology'])}")
                if chars.get("structure_types"):
                    print(f"      Types d'ouvrages: {', '.join(chars['structure_types'])}")
                if chars.get("geographical_scope"):
                    print(f"      Portée: {chars['geographical_scope']}")
                if chars.get("project_phase"):
                    print(f"      Phase: {chars['project_phase']}")
                if chars.get("equipment"):
                    print(f"      🔧 Équipements: {', '.join(chars['equipment'])}")
                if chars.get("team_members"):
                    print(f"      👥 Équipe: {', '.join(chars['team_members'])}")
                if chars.get("team_roles"):
                    print(f"      🎓 Compétences: {', '.join(chars['team_roles'])}")
                if chars.get("special_sections"):
                    print(f"\n   📑 Sections spéciales:")
                    for section_name, section_summary in chars["special_sections"].items():
                        print(f"      • {section_name}: {section_summary}")
                if chars.get("project_references"):
                    print(f"\n   🏆 Références projets: {', '.join(chars['project_references'])}")
                if chars.get("target_projects"):
                    print(f"\n   🎯 Projets cibles (appel d'offres): {', '.join(chars['target_projects'])}")

            # Afficher les distinctions si disponibles
            if doc.get("distinctions"):
                dist = doc["distinctions"]
                if dist.get("unique_aspects"):
                    print(f"\n   🎯 Ce qui rend ce document unique:")
                    print(f"      {dist['unique_aspects']}")
                if dist.get("differentiators"):
                    print(f"\n   🔍 Différenciateurs:")
                    for diff in dist["differentiators"]:
                        print(f"      • {diff}")
                if dist.get("positioning"):
                    print(f"\n   💡 Positionnement: {dist['positioning']}")

            # Afficher les illustrations exceptionnelles si disponibles
            if doc.get("special_illustrations"):
                illustrations = doc["special_illustrations"]
                if illustrations:
                    print(f"\n   🖼️ Illustrations exceptionnelles ({len(illustrations)}):")
                    for idx, illust in enumerate(illustrations, 1):
                        # Afficher catégorie si disponible
                        cat = illust.get('category', '')
                        type_str = illust.get('type', 'Illustration')
                        if cat:
                            print(f"\n      [{idx}] [{cat.upper()}] {type_str}")
                        else:
                            print(f"\n      [{idx}] {type_str}")

                        if illust.get('description'):
                            print(f"          Description: {illust['description']}")

                        # Afficher mots-clés techniques si disponibles
                        if illust.get('technical_keywords'):
                            print(f"          Mots-clés: {', '.join(illust['technical_keywords'])}")

                        # Afficher l'emplacement de l'image si disponible
                        if illust.get('image_path'):
                            img_path = Path(config.DATA_DIR.parent) / illust["image_path"]
                            if img_path.exists():
                                print(f"          📸 Image: {illust['image_path']}")
                            else:
                                print(f"          ⚠️ Image manquante: {illust['image_path']}")

                        if illust.get('detection_method'):
                            conf = illust.get('confidence', 'unknown')
                            print(f"          Détection: {illust['detection_method']} (confiance: {conf})")

                        if illust.get('context'):
                            # Limiter le contexte à 150 caractères pour l'affichage
                            context = illust['context']
                            if len(context) > 150:
                                context = context[:150] + "..."
                            print(f"          Contexte: {context}")

            # Afficher les métadonnées d'images si disponibles
            if doc.get("image_metadata"):
                img_meta = doc["image_metadata"]
                if img_meta.get("image_count", 0) > 0:
                    print(f"\n   📷 Métadonnées images:")
                    print(f"      Nombre d'images: {img_meta['image_count']}")
                    print(f"      Source: {img_meta.get('source', 'inconnue')}")
                    print(f"      Zones détectées: {img_meta.get('zones_detected', 0)}")

            print(f"\n{'-'*80}\n")

        # Recommandation
        print("RECOMMANDATION:")
        best_match = results[0]
        print(f"\n>> Utilisez '{best_match['filename']}' comme base")
        print(f"   (Score: {best_match['similarity_score']:.1f})")

        if len(results) > 1:
            print(f"\n>> Considerez aussi ces documents pour des sections specifiques :")
            for doc in results[1:4]:
                print(f"   - {doc['filename']} (Score: {doc['similarity_score']:.1f})")


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Trouve les mémoires techniques similaires"
    )
    parser.add_argument(
        "source",
        help="Fichier à analyser ou description du projet (entre guillemets)"
    )
    parser.add_argument(
        "--file",
        action="store_true",
        help="La source est un fichier (sinon, c'est une description)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=5,
        help="Nombre maximum de résultats (défaut: 5)"
    )

    args = parser.parse_args()

    finder = SimilarityFinder()

    # Déterminer la source
    if args.file:
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"Fichier introuvable: {args.source}")
            sys.exit(1)
        source_metadata = finder._analyze_document(source_path)
    else:
        source_metadata = finder._analyze_description(args.source)

    # Trouver les documents similaires
    results = finder.find_similar(args.source, is_file=args.file, max_results=args.max)
    finder.display_results(results, source_metadata)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
