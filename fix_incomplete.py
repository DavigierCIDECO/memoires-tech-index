"""Script pour identifier et supprimer les documents incomplets de l'index."""
import json
import logging
from pathlib import Path
from datetime import datetime

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fix_incomplete_documents():
    """Supprime les documents incomplets de l'index pour permettre leur réindexation."""

    # Charger l'index
    if not config.INDEX_FILE.exists():
        logger.error(f"Index introuvable: {config.INDEX_FILE}")
        return

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    total_docs = len(index["documents"])
    logger.info(f"Index chargé: {total_docs} documents")

    # Identifier les documents incomplets
    incomplete = []
    complete = []

    for doc in index["documents"]:
        is_incomplete = False
        issues = []

        # Vérifier les champs essentiels
        if not doc.get('summary') or doc['summary'] == 'Erreur lors de la génération du résumé':
            is_incomplete = True
            issues.append('summary manquant/erreur')
        if not doc.get('keywords'):
            is_incomplete = True
            issues.append('keywords manquants')

        if is_incomplete:
            incomplete.append({
                'doc': doc,
                'issues': issues
            })
        else:
            complete.append(doc)

    logger.info(f"\nDocuments complets: {len(complete)}")
    logger.info(f"Documents incomplets: {len(incomplete)}")

    if not incomplete:
        logger.info("\n✅ Aucun document incomplet trouvé !")
        return

    # Afficher la liste
    logger.info("\n" + "="*80)
    logger.info("DOCUMENTS INCOMPLETS À RÉINDEXER")
    logger.info("="*80 + "\n")

    for i, item in enumerate(incomplete, 1):
        doc = item['doc']
        logger.info(f"{i}. {doc['filename']}")
        logger.info(f"   Problèmes: {', '.join(item['issues'])}")

    # Sauvegarder la liste des fichiers à réindexer
    files_to_reindex = [item['doc']['file_path'] for item in incomplete]
    list_file = config.DATA_DIR / "incomplete_files.txt"

    with open(list_file, "w", encoding="utf-8") as f:
        for file_path in files_to_reindex:
            f.write(file_path + "\n")

    logger.info(f"\n📝 Liste sauvegardée dans: {list_file}")

    # Demander confirmation
    print("\n" + "="*80)
    print("⚠️  ATTENTION: Cette opération va:")
    print(f"   1. Supprimer {len(incomplete)} documents incomplets de l'index")
    print(f"   2. Garder {len(complete)} documents complets")
    print(f"   3. Vous pourrez ensuite réindexer les {len(incomplete)} fichiers manquants")
    print("="*80)

    response = input("\nContinuer? (oui/non): ")

    if response.lower() not in ['oui', 'o', 'yes', 'y']:
        logger.info("Opération annulée")
        return

    # Créer backup
    backup_file = config.DATA_DIR / f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    logger.info(f"\n💾 Backup créé: {backup_file}")

    # Mettre à jour l'index
    index["documents"] = complete
    index["last_updated"] = datetime.now().isoformat()

    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✅ Index mis à jour: {len(complete)} documents")
    logger.info(f"\n📋 Prochaines étapes:")
    logger.info(f"   1. Rechargez vos crédits API Anthropic")
    logger.info(f"   2. Lancez: python indexer.py \"C:\\Users\\David\\Documents\\ClaudeCodeSandbox\\MT\"")
    logger.info(f"   3. {len(incomplete)} documents seront réindexés")


if __name__ == "__main__":
    fix_incomplete_documents()
