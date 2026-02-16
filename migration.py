"""Script one-shot pour migrer l'index existant vers le nouveau format.

Ajoute les champs de traçabilité (status, indexed_by, validated_by, etc.)
à tous les documents existants dans l'index.

Usage:
    python migration.py
"""
import json
import logging
import shutil
from datetime import datetime

import config
from models import migrate_document

logger = logging.getLogger(__name__)


def migrate_index():
    """Migre l'index existant vers le nouveau format avec statuts et traçabilité."""
    if not config.INDEX_FILE.exists():
        print("Index introuvable. Rien à migrer.")
        return

    # Backup avant migration
    backup_name = f"index_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = config.DATA_DIR / backup_name
    shutil.copy2(config.INDEX_FILE, backup_path)
    print(f"Backup créé : {backup_path}")

    # Charger l'index
    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    documents = index.get("documents", [])
    migrated = 0

    for doc in documents:
        migrate_document(doc)
        migrated += 1

    # Sauvegarder
    index["last_updated"] = datetime.now().isoformat()
    index["schema_version"] = "2.0"

    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Migration terminée : {migrated} document(s) mis à jour.")
    print(f"  - indexe_non_valide : {sum(1 for d in documents if d['status'] == 'indexe_non_valide')}")
    print(f"  - enrichi : {sum(1 for d in documents if d['status'] == 'enrichi')}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_index()
