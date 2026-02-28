"""Script pour corriger les chemins d'images dupliqués dans Palais St Mélaine.

Ce script vous permet de spécifier de nouveaux chemins d'images pour les illustrations
qui pointent actuellement vers le mauvais fichier.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

import config


def fix_palais_images():
    """Corrige les chemins d'images pour Palais St Mélaine."""

    # Charger l'index
    if not config.INDEX_FILE.exists():
        print(f"❌ Index introuvable: {config.INDEX_FILE}")
        return

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    # Trouver Palais
    palais_doc = None
    for doc in index["documents"]:
        if "Palais" in doc["filename"]:
            palais_doc = doc
            break

    if not palais_doc:
        print("❌ Document Palais introuvable")
        return

    print(f"✅ Document: {palais_doc['filename']}")
    print(f"   Hash: {palais_doc['file_hash']}")

    illustrations = palais_doc.get("special_illustrations", [])
    if not illustrations:
        print("❌ Aucune illustration")
        return

    print(f"\n📋 Illustrations actuelles:")
    for idx, illust in enumerate(illustrations[:5], 1):
        img_path = illust.get("image_path", "PAS D'IMAGE")
        print(f"   {idx}. {img_path}")
        print(f"      Description: {illust.get('description', 'N/A')[:60]}...")

    print(f"\n⚠️  PROBLÈME DÉTECTÉ:")
    print(f"   Les illustrations 1, 2, et 3 pointent toutes vers illust_003.png")
    print(f"   Les fichiers illust_001.png et illust_002.png n'existent pas sur le disque")

    print(f"\n💡 SOLUTION:")
    print(f"   1. Vous devez ré-uploader les bonnes images pour les illustrations 1 et 2")
    print(f"      via l'interface d'enrichissement manuel (quand la fonctionnalité")
    print(f"      de remplacement d'image sera ajoutée)")
    print(f"   ")
    print(f"   OU")
    print(f"   ")
    print(f"   2. Vous pouvez manuellement copier les bonnes images dans:")
    print(f"      data/images/{palais_doc['file_hash']}/")
    print(f"      avec les noms: illust_001.png et illust_002.png")
    print(f"   ")
    print(f"   Ensuite, ce script mettra à jour l'index pour pointer vers")
    print(f"   les bons fichiers.")

    img_dir = config.DATA_DIR / "images" / palais_doc["file_hash"]

    # Vérifier si les fichiers manquants ont été ajoutés
    file_001 = img_dir / "illust_001.png"
    file_002 = img_dir / "illust_002.png"

    if file_001.exists() and file_002.exists():
        print(f"\n✅ Les fichiers illust_001.png et illust_002.png existent !")
        print(f"   Mise à jour de l'index...")

        # Mettre à jour les chemins
        illustrations[0]["image_path"] = str(file_001.relative_to(config.DATA_DIR.parent))
        illustrations[1]["image_path"] = str(file_002.relative_to(config.DATA_DIR.parent))
        illustrations[2]["image_path"] = str((img_dir / "illust_003.png").relative_to(config.DATA_DIR.parent))

        # Sauvegarder
        with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"   ✅ Index mis à jour avec succès !")
    else:
        print(f"\n❌ Les fichiers manquent toujours:")
        if not file_001.exists():
            print(f"   - {file_001}")
        if not file_002.exists():
            print(f"   - {file_002}")
        print(f"\n   Ajoutez les fichiers manuellement, puis relancez ce script.")


if __name__ == "__main__":
    fix_palais_images()
