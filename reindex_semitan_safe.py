"""Réindexe SEMITAN en préservant les special_illustrations."""
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import config
from indexer import DocumentIndexer

def reindex_semitan_safely():
    """Réindexe SEMITAN tout en préservant les illustrations enrichies."""

    # 1. Charger l'index actuel
    if not config.INDEX_FILE.exists():
        print(f"❌ Index introuvable: {config.INDEX_FILE}")
        return

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    # 2. Trouver SEMITAN (le "Mémoire technique", pas "éco responsable")
    semitan_doc = None
    semitan_idx = None
    for idx, doc in enumerate(index["documents"]):
        if "SEMITAN" in doc["filename"].upper() and "TECHNIQUE" in doc["filename"].upper():
            semitan_doc = doc
            semitan_idx = idx
            break

    if not semitan_doc:
        print("❌ Document SEMITAN introuvable dans l'index")
        return

    print(f"✅ Document trouvé: {semitan_doc['filename']}")
    print(f"   Hash: {semitan_doc['file_hash']}")

    # 3. Sauvegarder les special_illustrations
    saved_illustrations = semitan_doc.get("special_illustrations", [])
    print(f"   💾 {len(saved_illustrations)} illustrations sauvegardées")

    # 4. Backup de l'index complet
    backup_file = config.INDEX_FILE.with_suffix('.backup_before_semitan_reindex')
    shutil.copy(config.INDEX_FILE, backup_file)
    print(f"   💾 Backup créé: {backup_file}")

    # 5. Supprimer temporairement SEMITAN de l'index
    del index["documents"][semitan_idx]
    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"   🗑️  SEMITAN temporairement retiré de l'index")

    # 6. Réindexer SEMITAN
    print(f"\n   🔄 Réindexation en cours...")
    indexer = DocumentIndexer()
    doc_dir = Path("C:/Users/David/Documents/ClaudeCodeSandbox/MT")

    # Forcer la réindexation en traitant tous les fichiers
    indexer.index_directory(doc_dir)

    # 7. Recharger l'index
    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    # 8. Trouver le nouveau SEMITAN (le "Mémoire technique")
    new_semitan_doc = None
    new_semitan_idx = None
    for idx, doc in enumerate(index["documents"]):
        if "SEMITAN" in doc["filename"].upper() and "TECHNIQUE" in doc["filename"].upper():
            new_semitan_doc = doc
            new_semitan_idx = idx
            break

    if not new_semitan_doc:
        print("❌ ERREUR: SEMITAN non trouvé après réindexation!")
        print("   Restauration du backup...")
        shutil.copy(backup_file, config.INDEX_FILE)
        return

    print(f"   ✅ SEMITAN réindexé")

    # 9. Restaurer les special_illustrations
    new_semitan_doc["special_illustrations"] = saved_illustrations
    index["documents"][new_semitan_idx] = new_semitan_doc

    # 10. Sauvegarder l'index final
    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"   ✅ Illustrations restaurées ({len(saved_illustrations)} illustrations)")

    # 11. Vérifier les special_sections
    special_sections = new_semitan_doc.get("characteristics", {}).get("special_sections", {})
    print(f"\n📋 Résultat:")
    print(f"   special_sections: {len(special_sections)} sections")
    if special_sections:
        print(f"   Sections capturées:")
        for section_name in list(special_sections.keys())[:5]:
            print(f"      - {section_name}")
    else:
        print(f"   ⚠️  AUCUNE SECTION CAPTURÉE (vérifier debug_claude_response.txt)")

    print(f"\n✅ Réindexation terminée avec succès!")
    print(f"   Backup conservé: {backup_file}")

if __name__ == "__main__":
    reindex_semitan_safely()
