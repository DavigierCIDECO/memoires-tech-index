"""Script de réanalyse différentielle pour tous les documents de l'index.

Ce script recharge l'index complet, puis refait l'analyse différentielle
(Phase 3) pour TOUS les documents, leur permettant d'être comparés au corpus
complet plutôt qu'uniquement aux documents indexés avant eux.
"""
import json
import logging
from pathlib import Path
from datetime import datetime

from indexer import DocumentIndexer
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def reanalyze_all_distinctions():
    """Réanalyse les distinctions de tous les documents."""

    # Charger l'index existant
    if not config.INDEX_FILE.exists():
        logger.error(f"Index introuvable: {config.INDEX_FILE}")
        return

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    total_docs = len(index["documents"])
    logger.info(f"Index chargé: {total_docs} documents")

    if total_docs == 0:
        logger.warning("Index vide, rien à réanalyser")
        return

    # Initialiser l'indexeur (pour accéder aux méthodes)
    indexer = DocumentIndexer()

    # Statistiques
    reanalyzed_count = 0
    error_count = 0

    logger.info("\n" + "="*80)
    logger.info("DÉBUT DE LA RÉANALYSE DIFFÉRENTIELLE")
    logger.info("="*80 + "\n")

    # Pour chaque document, refaire l'analyse différentielle
    for i, doc in enumerate(index["documents"], 1):
        filename = doc["filename"]
        file_hash = doc["file_hash"]

        logger.info(f"[{i}/{total_docs}] {filename}")

        # Charger le texte du document (si disponible)
        file_path = Path(doc["file_path"])
        if not file_path.exists():
            logger.warning(f"  ⚠️  Fichier introuvable, ignoré")
            error_count += 1
            continue

        # Extraire le texte
        try:
            text = indexer.extractor.extract(file_path)
            if not text:
                logger.warning(f"  ⚠️  Échec extraction texte, ignoré")
                error_count += 1
                continue
        except Exception as e:
            logger.error(f"  ❌ Erreur extraction: {e}")
            error_count += 1
            continue

        # Créer un pseudo-metadata pour find_similar_documents
        metadata = {
            "keywords": doc.get("keywords", ""),
            "themes": doc.get("themes", ""),
            "characteristics": doc.get("characteristics", {})
        }

        # Trouver les documents similaires (en excluant le document actuel)
        logger.info(f"  → Recherche de documents similaires...")
        similar_docs = indexer._find_similar_documents(metadata, index, file_hash)

        if similar_docs:
            logger.info(f"  → Analyse différentielle ({len(similar_docs)} documents similaires)...")

            # Créer un doc_entry temporaire pour _generate_distinctions
            temp_doc = {
                "filename": filename,
                "summary": doc.get("summary", ""),
                "keywords": doc.get("keywords", ""),
                "themes": doc.get("themes", "")
            }

            # Générer les nouvelles distinctions
            try:
                new_distinctions = indexer._generate_distinctions(
                    temp_doc, similar_docs, text
                )

                # Mettre à jour le document
                doc["distinctions"] = new_distinctions
                doc["similar_documents"] = similar_docs
                doc["compared_against"] = len(similar_docs)
                doc["reanalyzed_at"] = datetime.now().isoformat()

                logger.info(f"  ✅ Réanalysé avec succès")
                reanalyzed_count += 1

            except Exception as e:
                logger.error(f"  ❌ Erreur analyse différentielle: {e}")
                error_count += 1
        else:
            logger.info(f"  → Aucun document similaire (score < 20)")
            # Mettre à jour quand même pour indiquer "analysé mais pas de similaires"
            doc["distinctions"] = {
                "unique_aspects": "Document unique dans l'index (aucun similaire avec score ≥ 20)",
                "differentiators": [],
                "positioning": "Document de référence"
            }
            doc["similar_documents"] = []
            doc["compared_against"] = 0
            doc["reanalyzed_at"] = datetime.now().isoformat()
            reanalyzed_count += 1

    # Sauvegarder l'index mis à jour
    logger.info("\n" + "="*80)
    logger.info("Sauvegarde de l'index...")
    index["last_updated"] = datetime.now().isoformat()
    index["last_reanalysis"] = datetime.now().isoformat()

    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(f"Index sauvegardé dans {config.INDEX_FILE}")

    # Résumé
    logger.info("\n" + "="*80)
    logger.info("=== RÉSUMÉ DE LA RÉANALYSE ===")
    logger.info("="*80)
    logger.info(f"Documents réanalysés: {reanalyzed_count}")
    logger.info(f"Erreurs: {error_count}")
    logger.info(f"Total: {total_docs}")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Réanalyse différentielle de tous les documents"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirmer la réanalyse (requis pour éviter les lancements accidentels)"
    )

    args = parser.parse_args()

    if not args.confirm:
        print("\n⚠️  ATTENTION: Ce script va réanalyser TOUS les documents de l'index.")
        print("   Cela implique des appels API Claude pour chaque document.")
        print(f"   Coût estimé: ~{len(json.load(open(config.INDEX_FILE, 'r', encoding='utf-8')).get('documents', [])) * 0.0025:.2f}$\n")
        print("Pour confirmer, relancez avec: python reanalyze_distinctions.py --confirm\n")
    else:
        reanalyze_all_distinctions()
