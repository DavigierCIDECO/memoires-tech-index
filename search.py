"""Recherche dans l'index des mémoires techniques."""
import json
import logging
from pathlib import Path
from typing import List, Dict
import sys

import config

logger = logging.getLogger(__name__)


class DocumentSearcher:
    """Recherche dans l'index des documents."""

    def __init__(self):
        """Initialise le chercheur."""
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

    def _score_document(self, doc: Dict, query_terms: List[str]) -> float:
        """Calcule un score de pertinence pour un document.

        Args:
            doc: Document à scorer
            query_terms: Termes de recherche

        Returns:
            Score de pertinence (plus élevé = plus pertinent)
        """
        score = 0.0

        # Texte à analyser (en minuscules pour recherche insensible à la casse)
        searchable_text = " ".join([
            doc.get("filename", ""),
            doc.get("summary", ""),
            doc.get("keywords", ""),
            doc.get("themes", ""),
            doc.get("text_preview", "")
        ]).lower()

        for term in query_terms:
            term_lower = term.lower()

            # Compte les occurrences du terme
            occurrences = searchable_text.count(term_lower)

            # Pondération différente selon où le terme apparaît
            if term_lower in doc.get("filename", "").lower():
                score += 10.0  # Nom de fichier = très important
            if term_lower in doc.get("keywords", "").lower():
                score += 5.0  # Mots-clés = important
            if term_lower in doc.get("themes", "").lower():
                score += 3.0  # Thèmes = important
            if term_lower in doc.get("summary", "").lower():
                score += 2.0 * occurrences  # Résumé

            # Bonus pour occurrence dans le texte
            score += occurrences * 0.5

        return score

    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Recherche des documents correspondant à la requête.

        Args:
            query: Requête de recherche
            max_results: Nombre maximum de résultats

        Returns:
            Liste des documents triés par pertinence
        """
        if not self.index["documents"]:
            logger.warning("Index vide")
            return []

        # Séparer la requête en termes
        query_terms = [term.strip() for term in query.split() if term.strip()]

        if not query_terms:
            logger.warning("Requête vide")
            return []

        # Scorer tous les documents
        scored_docs = []
        for doc in self.index["documents"]:
            score = self._score_document(doc, query_terms)
            if score > 0:
                doc_with_score = doc.copy()
                doc_with_score["relevance_score"] = score
                scored_docs.append(doc_with_score)

        # Trier par score décroissant
        scored_docs.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored_docs[:max_results]

    def display_results(self, results: List[Dict], query: str):
        """Affiche les résultats de recherche.

        Args:
            results: Liste des résultats
            query: Requête originale
        """
        if not results:
            print(f"\nAucun résultat pour '{query}'")
            return

        print(f"\n{'='*80}")
        print(f"Résultats pour : {query}")
        print(f"{'='*80}\n")

        for i, doc in enumerate(results, 1):
            print(f"{i}. {doc['filename']}")
            print(f"   Score de pertinence: {doc['relevance_score']:.1f}")
            print(f"   Chemin: {doc['file_path']}")
            print(f"   Taille: {doc['file_size'] / 1024:.1f} KB")
            print(f"   Modifié: {doc['file_modified'][:10]}")
            print(f"\n   Résumé:")
            print(f"   {doc['summary']}")
            print(f"\n   Mots-clés: {doc['keywords']}")
            print(f"   Thèmes: {doc['themes']}")
            print(f"\n   Aperçu:")
            preview = doc['text_preview'][:200].replace('\n', ' ')
            print(f"   {preview}...")
            print(f"\n{'-'*80}\n")

    def get_stats(self) -> Dict:
        """Retourne des statistiques sur l'index.

        Returns:
            Dictionnaire de statistiques
        """
        if not self.index["documents"]:
            return {"total_documents": 0}

        total_size = sum(doc["file_size"] for doc in self.index["documents"])
        all_keywords = []
        all_themes = []

        for doc in self.index["documents"]:
            if doc.get("keywords"):
                all_keywords.extend([k.strip() for k in doc["keywords"].split(",")])
            if doc.get("themes"):
                all_themes.extend([t.strip() for t in doc["themes"].split(",")])

        # Compter les mots-clés les plus fréquents
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        theme_counts = {}
        for theme in all_themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

        # Top 10
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_documents": len(self.index["documents"]),
            "total_size_mb": total_size / (1024 * 1024),
            "last_updated": self.index.get("last_updated", "Inconnu"),
            "top_keywords": top_keywords,
            "top_themes": top_themes
        }

    def display_stats(self):
        """Affiche les statistiques de l'index."""
        stats = self.get_stats()

        print(f"\n{'='*80}")
        print("STATISTIQUES DE L'INDEX")
        print(f"{'='*80}\n")

        print(f"Total de documents indexés: {stats['total_documents']}")
        print(f"Taille totale: {stats['total_size_mb']:.2f} MB")
        print(f"Dernière mise à jour: {stats['last_updated']}")

        if stats.get("top_keywords"):
            print(f"\nMots-clés les plus fréquents:")
            for kw, count in stats["top_keywords"]:
                print(f"  - {kw}: {count} document(s)")

        if stats.get("top_themes"):
            print(f"\nThèmes les plus fréquents:")
            for theme, count in stats["top_themes"]:
                print(f"  - {theme}: {count} document(s)")

        print(f"\n{'='*80}\n")


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Recherche dans les mémoires techniques indexés"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Termes de recherche"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Affiche les statistiques de l'index"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Nombre maximum de résultats (défaut: 10)"
    )

    args = parser.parse_args()

    searcher = DocumentSearcher()

    if args.stats:
        searcher.display_stats()
        return

    if not args.query:
        print("Usage: python search.py <termes de recherche>")
        print("   ou: python search.py --stats")
        sys.exit(1)

    query = " ".join(args.query)
    results = searcher.search(query, max_results=args.max)
    searcher.display_results(results, query)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
