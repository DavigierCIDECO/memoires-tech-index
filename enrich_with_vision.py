"""Script pour enrichir les illustrations d'un document avec Claude Vision API.

Utilise l'API Vision de Claude pour "voir" réellement les images et générer
des descriptions techniques précises avec catégorisation et mots-clés.
"""
import json
import logging
import base64
from pathlib import Path
from datetime import datetime
import argparse

from anthropic import Anthropic
from docx import Document
from PIL import Image
import io

import config
from image_extractor import ImageExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VisionEnricher:
    """Enrichit les illustrations avec Claude Vision API."""

    def __init__(self):
        """Initialise l'enrichisseur."""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY non définie")

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.img_extractor = ImageExtractor()

    def _extract_images_from_docx(self, file_path: Path) -> list:
        """Extrait les images brutes d'un fichier DOCX.

        Args:
            file_path: Chemin vers le fichier DOCX

        Returns:
            Liste de tuples (index, image_bytes, format)
        """
        try:
            doc = Document(str(file_path))
            images = []

            for i, rel in enumerate(doc.part.rels.values()):
                if "image" in rel.target_ref:
                    image_part = rel.target_part
                    image_bytes = image_part.blob

                    # Déterminer le format
                    content_type = image_part.content_type
                    if 'png' in content_type:
                        img_format = 'png'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        img_format = 'jpeg'
                    else:
                        img_format = 'png'  # Par défaut

                    images.append((i, image_bytes, img_format))

            return images

        except Exception as e:
            logger.error(f"Erreur extraction images DOCX: {e}")
            return []

    def _analyze_image_with_vision(self, image_bytes: bytes, img_format: str, context: str = "") -> dict:
        """Analyse une image avec Claude Vision API.

        Args:
            image_bytes: Données brutes de l'image
            img_format: Format de l'image (png, jpeg)
            context: Contexte textuel optionnel

        Returns:
            Dictionnaire avec analyse de l'illustration
        """
        # Encoder l'image en base64
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Construire le prompt pour Vision API
        prompt = f"""Analysez cette illustration technique et fournissez une description structurée :

CATÉGORIE (choisir UNE catégorie principale) :
- Investigation : photos/schémas d'équipements terrain, protocoles d'essais, installations de mesure
- Analyse : graphiques de résultats, courbes, tableaux de mesures, cartographies
- Modélisation : modèles numériques (éléments finis, etc.), schémas de calcul, diagrammes structurels
- Préconisation : schémas de réparation/renforcement, solutions techniques, plans d'intervention
- Méthodologie : organigrammes, processus, planning, organisation

TYPE : schéma, photo, graphique, plan, diagramme, tableau

DESCRIPTION DÉTAILLÉE (3-5 phrases précises) :
Décrivez exactement ce qui est visible :
- Équipements montrés (géoradar, carotteuse, capteurs, etc.)
- Techniques de réparation/renforcement (plats carbone, injection résine, tirants, etc.)
- Résultats présentés (courbes, valeurs, cartographies)
- Configuration structurelle (poutre, dalle, poteau, assemblage, etc.)
- Matériaux visibles (béton, acier, carbone, bois, maçonnerie)
- Annotations, dimensions, légendes importantes

MOTS-CLÉS TECHNIQUES (5-8 mots-clés spécifiques) :
Exemples : plats carbone, modèle éléments finis, courbe charge-déplacement, renforcement poutre, etc.

ÉQUIPEMENTS VISIBLES (liste, ou "aucun") :
Matériel technique identifiable dans l'image

TECHNIQUES MONTRÉES (liste, ou "aucune") :
Méthodes de diagnostic, réparation, renforcement visibles

{f'CONTEXTE TEXTUEL : {context}' if context else ''}

FORMAT DE RÉPONSE STRICT :
CATÉGORIE: [Investigation/Analyse/Modélisation/Préconisation/Méthodologie]
TYPE: [schéma/photo/graphique/plan/diagramme/tableau]
DESCRIPTION: [description détaillée en 3-5 phrases]
MOTS-CLÉS: [mot-clé1, mot-clé2, mot-clé3, mot-clé4, mot-clé5]
ÉQUIPEMENTS: [équip1, équip2, ...] (ou "aucun")
TECHNIQUES: [tech1, tech2, ...] (ou "aucune")
"""

        try:
            # Appel Vision API
            message = self.client.messages.create(
                model="claude-opus-4-6",  # Modèle Opus avec vision
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{img_format}",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }]
            )

            response_text = message.content[0].text

            # Parser la réponse
            result = {
                "category": "",
                "type": "",
                "description": "",
                "technical_keywords": [],
                "equipment_shown": [],
                "techniques_shown": []
            }

            for line in response_text.split("\n"):
                line = line.strip()
                if line.startswith("CATÉGORIE:"):
                    result["category"] = line.replace("CATÉGORIE:", "").strip()
                elif line.startswith("TYPE:"):
                    result["type"] = line.replace("TYPE:", "").strip()
                elif line.startswith("DESCRIPTION:"):
                    result["description"] = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("MOTS-CLÉS:"):
                    value = line.replace("MOTS-CLÉS:", "").strip()
                    if value and value.lower() != "aucun":
                        result["technical_keywords"] = [k.strip() for k in value.split(",")]
                elif line.startswith("ÉQUIPEMENTS:"):
                    value = line.replace("ÉQUIPEMENTS:", "").strip()
                    if value and value.lower() != "aucun":
                        result["equipment_shown"] = [e.strip() for e in value.split(",")]
                elif line.startswith("TECHNIQUES:"):
                    value = line.replace("TECHNIQUES:", "").strip()
                    if value and value.lower() not in ["aucune", "aucun"]:
                        result["techniques_shown"] = [t.strip() for t in value.split(",")]

            return result

        except Exception as e:
            logger.error(f"Erreur Vision API: {e}")
            return None

    def enrich_document(self, document_filename: str, max_images: int = 10):
        """Enrichit les illustrations d'un document spécifique.

        Args:
            document_filename: Nom du fichier (ou chemin complet)
            max_images: Nombre max d'images à analyser (coût!)
        """
        # Charger l'index
        if not config.INDEX_FILE.exists():
            logger.error(f"Index introuvable: {config.INDEX_FILE}")
            return

        with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
            index = json.load(f)

        # Trouver le document
        doc_entry = None
        for doc in index["documents"]:
            if document_filename in doc["filename"] or document_filename in doc["file_path"]:
                doc_entry = doc
                break

        if not doc_entry:
            logger.error(f"Document '{document_filename}' introuvable dans l'index")
            logger.info("Documents disponibles:")
            for doc in index["documents"][:10]:
                logger.info(f"  - {doc['filename']}")
            return

        file_path = Path(doc_entry["file_path"])
        if not file_path.exists():
            logger.error(f"Fichier introuvable: {file_path}")
            return

        logger.info(f"\n{'='*80}")
        logger.info(f"ENRICHISSEMENT VISION : {doc_entry['filename']}")
        logger.info(f"{'='*80}\n")

        # Extraire les images
        if file_path.suffix.lower() == ".docx":
            images = self._extract_images_from_docx(file_path)
        else:
            logger.error(f"Format {file_path.suffix} non supporté (uniquement .docx pour l'instant)")
            return

        total_images = len(images)
        logger.info(f"Images trouvées: {total_images}")

        if total_images == 0:
            logger.warning("Aucune image à enrichir")
            return

        # Limiter au nombre max
        images_to_process = images[:max_images]
        logger.info(f"Images à analyser: {len(images_to_process)} (max: {max_images})")

        estimated_cost = len(images_to_process) * 0.015  # ~$0.015 per image
        logger.info(f"Coût estimé: ${estimated_cost:.2f}\n")

        # Demander confirmation
        response = input(f"Analyser {len(images_to_process)} images ? (oui/non): ")
        if response.lower() not in ['oui', 'o', 'yes', 'y']:
            logger.info("Opération annulée")
            return

        # Analyser chaque image
        enriched_illustrations = []

        for idx, (img_idx, img_bytes, img_format) in enumerate(images_to_process, 1):
            logger.info(f"\n[{idx}/{len(images_to_process)}] Analyse de l'image #{img_idx}...")

            analysis = self._analyze_image_with_vision(img_bytes, img_format)

            if analysis:
                illustration = {
                    "category": analysis.get("category", ""),
                    "type": analysis.get("type", ""),
                    "description": analysis.get("description", ""),
                    "technical_keywords": analysis.get("technical_keywords", []),
                    "equipment_shown": analysis.get("equipment_shown", []),
                    "techniques_shown": analysis.get("techniques_shown", []),
                    "detection_method": "Vision API (Claude)",
                    "confidence": "high",
                    "context": f"Image #{img_idx} du document"
                }

                enriched_illustrations.append(illustration)

                logger.info(f"  ✓ [{analysis.get('category', 'N/A')}] {analysis.get('type', 'N/A')}")
                logger.info(f"    {analysis.get('description', 'N/A')[:80]}...")
                if analysis.get('technical_keywords'):
                    logger.info(f"    Mots-clés: {', '.join(analysis['technical_keywords'][:3])}...")
            else:
                logger.warning(f"  ✗ Échec de l'analyse")

        # Mettre à jour l'index
        doc_entry["special_illustrations"] = enriched_illustrations
        doc_entry["vision_enriched_at"] = datetime.now().isoformat()
        doc_entry["vision_images_analyzed"] = len(enriched_illustrations)

        # Sauvegarder
        with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Enrichissement terminé !")
        logger.info(f"{'='*80}")
        logger.info(f"Illustrations enrichies: {len(enriched_illustrations)}")
        logger.info(f"Index mis à jour: {config.INDEX_FILE}")


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Enrichit les illustrations d'un document avec Vision API"
    )
    parser.add_argument(
        "document",
        help="Nom du fichier ou chemin complet"
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=10,
        help="Nombre maximum d'images à analyser (défaut: 10)"
    )

    args = parser.parse_args()

    enricher = VisionEnricher()
    enricher.enrich_document(args.document, max_images=args.max_images)


if __name__ == "__main__":
    main()
