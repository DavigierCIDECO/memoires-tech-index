"""Script pour restaurer automatiquement les images SEMITAN perdues lors de la réindexation.

Les images physiques existent toujours, mais les métadonnées ont été perdues.
Ce script crée des entrées d'illustration avec métadonnées minimales à compléter.
"""
import json
from pathlib import Path
from datetime import datetime

import config


def restore_semitan_images():
    """Restaure les illustrations SEMITAN avec métadonnées minimales."""

    # Charger l'index
    if not config.INDEX_FILE.exists():
        print(f"❌ Index introuvable: {config.INDEX_FILE}")
        return

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    # Trouver SEMITAN
    semitan_doc = None
    for doc in index["documents"]:
        if "SEMITAN" in doc["filename"].upper():
            semitan_doc = doc
            break

    if not semitan_doc:
        print("❌ Document SEMITAN introuvable dans l'index")
        return

    print(f"✅ Document trouvé: {semitan_doc['filename']}")
    print(f"   Hash: {semitan_doc['file_hash']}")

    # Chercher les images dans le dossier
    img_dir = config.DATA_DIR / "images" / semitan_doc["file_hash"]

    if not img_dir.exists():
        print(f"❌ Dossier d'images introuvable: {img_dir}")
        return

    images = sorted(list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.jpeg")))

    if not images:
        print(f"❌ Aucune image trouvée dans {img_dir}")
        return

    print(f"✅ {len(images)} image(s) trouvée(s):")
    for img in images:
        print(f"   - {img.name}")

    # Demander confirmation
    print("\n⚠️  ATTENTION:")
    print(f"   Cela va REMPLACER les {len(semitan_doc.get('special_illustrations', []))} illustration(s) actuelles")
    print(f"   par {len(images)} nouvelles entrées avec métadonnées minimales.")

    response = input("\nContinuer ? (oui/non): ")
    if response.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée")
        return

    # Créer les entrées d'illustration
    new_illustrations = []

    for idx, img_path in enumerate(images, 1):
        # Chemin relatif
        relative_path = str(img_path.relative_to(config.DATA_DIR.parent))

        illustration = {
            "category": "À compléter",  # L'utilisateur devra compléter
            "type": "illustration",
            "description": "À compléter via l'interface d'enrichissement",
            "technical_keywords": [],  # Vide, à compléter
            "image_path": relative_path,
            "detection_method": "restauration automatique",
            "confidence": "low",
            "context": f"Image restaurée automatiquement le {datetime.now().strftime('%Y-%m-%d')}. Métadonnées à compléter.",
            "restored_at": datetime.now().isoformat()
        }

        new_illustrations.append(illustration)
        print(f"   ✓ Restauration: {img_path.name} → illustration #{idx}")

    # Remplacer les illustrations
    semitan_doc["special_illustrations"] = new_illustrations
    semitan_doc["images_restored_at"] = datetime.now().isoformat()

    # Sauvegarder l'index
    with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"✅ RESTAURATION TERMINÉE !")
    print(f"{'='*80}")
    print(f"   {len(new_illustrations)} illustration(s) restaurée(s) pour {semitan_doc['filename']}")
    print(f"   Index mis à jour: {config.INDEX_FILE}")
    print(f"\n📝 PROCHAINES ÉTAPES:")
    print(f"   1. Lancez: streamlit run enrich_manual.py")
    print(f"   2. Sélectionnez le document SEMITAN")
    print(f"   3. Pour chaque illustration, cliquez sur l'icône d'édition")
    print(f"   4. Complétez:")
    print(f"      - Catégorie (Investigation, Analyse, Modélisation, Préconisation, etc.)")
    print(f"      - Description détaillée")
    print(f"      - Mots-clés techniques (séparés par des virgules)")
    print(f"\n💡 Les images sont déjà là, il ne reste plus qu'à ajouter les métadonnées !")


if __name__ == "__main__":
    restore_semitan_images()
