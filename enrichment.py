"""Module d'enrichissement manuel des documents indexés."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from anthropic import Anthropic
import config

logger = logging.getLogger(__name__)

# Import dynamique pour éviter les imports circulaires
def get_learning_system():
    """Importe le système d'apprentissage de manière lazy."""
    from learning import LearningSystem
    return LearningSystem()


class EnrichmentManager:
    """Gère l'enrichissement manuel des documents indexés."""

    def __init__(self):
        """Initialise le gestionnaire d'enrichissement."""
        if not config.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY non définie. "
                "Créez un fichier .env avec votre clé API."
            )

        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.storage = config.get_storage()

    def load_index(self) -> Dict:
        """Charge l'index depuis le backend de stockage.

        Returns:
            L'index chargé
        """
        data = self.storage.read_json("index")
        if data is None:
            logger.error("Index introuvable dans le storage")
            return {"documents": []}
        return data

    def save_index(self, index: Dict):
        """Sauvegarde l'index via le backend de stockage.

        Args:
            index: L'index à sauvegarder
        """
        index["last_updated"] = datetime.now().isoformat()
        self.storage.write_json("index", index)
        logger.info("Index sauvegardé via storage")

    def get_document(self, file_hash: str) -> Optional[Dict]:
        """Récupère un document par son hash.

        Args:
            file_hash: Hash du fichier

        Returns:
            Document ou None si introuvable
        """
        index = self.load_index()
        for doc in index.get("documents", []):
            if doc.get("file_hash") == file_hash:
                return doc
        return None

    def rename_document(self, file_hash: str, new_filename: str, source_directory: str = None) -> dict:
        """Renomme un document de manière atomique (fichier physique + index JSON).

        Args:
            file_hash: Hash du fichier à renommer
            new_filename: Nouveau nom de fichier
            source_directory: Répertoire source (optionnel, sinon déduit de file_path)

        Returns:
            Dictionnaire avec success, message, old_filename, new_filename
        """
        index = self.load_index()

        # Trouver le document par file_hash
        doc = None
        doc_index = None
        for i, d in enumerate(index.get("documents", [])):
            if d.get("file_hash") == file_hash:
                doc = d
                doc_index = i
                break

        if doc is None:
            return {
                "success": False,
                "message": f"Document introuvable avec le hash {file_hash}",
                "old_filename": None,
                "new_filename": new_filename,
            }

        old_filename = doc.get("filename", "")

        # Validation : nouveau nom non vide
        if not new_filename or not new_filename.strip():
            return {
                "success": False,
                "message": "Le nouveau nom de fichier ne peut pas être vide",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

        new_filename = new_filename.strip()

        # Validation : pas de caractères invalides Windows
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            if char in new_filename:
                return {
                    "success": False,
                    "message": f"Le nom de fichier contient un caractère invalide : '{char}'",
                    "old_filename": old_filename,
                    "new_filename": new_filename,
                }

        # Validation : nouveau nom différent de l'ancien
        if new_filename == old_filename:
            return {
                "success": False,
                "message": "Le nouveau nom est identique à l'ancien",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

        # Validation : extension préservée
        old_ext = Path(old_filename).suffix.lower()
        new_ext = Path(new_filename).suffix.lower()
        if old_ext != new_ext:
            return {
                "success": False,
                "message": f"L'extension doit être préservée ({old_ext}). Nouveau nom : '{new_filename}'",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

        # Renommer le fichier sur le backend de stockage
        storage = config.get_storage()
        gdrive_id = doc.get("gdrive_file_id")

        if gdrive_id:
            # Mode Drive : renommer via l'API
            renamed = storage.rename_document(gdrive_id, new_filename)
        else:
            # Mode local : renommer le fichier physique
            file_path = doc.get("file_path", "")
            if source_directory:
                file_path = str(Path(source_directory) / old_filename)
            renamed = storage.rename_document(file_path, new_filename)

        if not renamed:
            return {
                "success": False,
                "message": "Erreur lors du renommage du fichier sur le stockage",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

        # Mettre à jour l'index
        try:
            doc["filename"] = new_filename
            if not gdrive_id:
                old_path = Path(doc.get("file_path", ""))
                doc["file_path"] = str(old_path.parent / new_filename) if str(old_path) else ""

            # Mettre à jour les cross-références dans similar_documents
            for other_doc in index.get("documents", []):
                if other_doc.get("file_hash") == file_hash:
                    continue
                for sim_doc in other_doc.get("similar_documents", []):
                    if sim_doc.get("file_hash") == file_hash:
                        sim_doc["filename"] = new_filename

            index["documents"][doc_index] = doc
            self.save_index(index)

            self._save_enrichment_history(
                file_hash,
                new_filename,
                {
                    "modifications": [
                        {
                            "action": "RENOMMER",
                            "champ": "filename",
                            "ancienne_valeur": old_filename,
                            "valeur": new_filename,
                            "raison": "Renommage manuel du document",
                        }
                    ],
                    "résumé_modifications": f"Renommage : {old_filename} → {new_filename}",
                },
            )

            logger.info(f"Document renommé avec succès : {old_filename} → {new_filename}")

            return {
                "success": True,
                "message": f"Document renommé avec succès : {old_filename} → {new_filename}",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'index : {e}")
            # Tenter un rollback du renommage
            if gdrive_id:
                storage.rename_document(gdrive_id, old_filename)
            return {
                "success": False,
                "message": f"Erreur lors de la mise à jour de l'index : {e}",
                "old_filename": old_filename,
                "new_filename": new_filename,
            }

    def _format_illustrations_for_prompt(self, illustrations: List[Dict]) -> str:
        """Formate les illustrations pour le prompt.

        Args:
            illustrations: Liste des illustrations

        Returns:
            Texte formaté
        """
        if not illustrations:
            return "(aucune illustration)"

        formatted = []
        for idx, illust in enumerate(illustrations, 1):
            desc = illust.get('description', 'Sans description')[:80]
            keywords = ', '.join(illust.get('technical_keywords', [])[:3])
            category = illust.get('category', 'N/A')
            formatted.append(f"[{idx}] {desc} | Catégorie: {category} | Mots-clés: {keywords}")

        return "\n".join(formatted)

    def interpret_natural_language_changes(
        self, doc: Dict, natural_language_input: str
    ) -> Dict:
        """Interprète un enrichissement en langage naturel et propose des modifications.

        Args:
            doc: Document à enrichir
            natural_language_input: Instructions en langage naturel

        Returns:
            Dictionnaire avec modifications proposées
        """
        # Construire le contexte actuel du document
        current_state = {
            "résumé": doc.get("summary", ""),
            "mots-clés": doc.get("keywords", ""),
            "thèmes": doc.get("themes", ""),
            "nombre_pages": doc.get("page_count"),
            "format_document": doc.get("document_format", "non spécifié"),
            "caractéristiques": doc.get("characteristics", {}),
            "sections_spéciales": doc.get("characteristics", {}).get("special_sections", {}),
            "illustrations": doc.get("special_illustrations", [])
        }

        # Formater les sections spéciales pour l'affichage
        sections_speciales_str = "(aucune)"
        if current_state['sections_spéciales']:
            sections_speciales_str = "\n".join([
                f"  - {nom}: {desc[:80]}..." if len(desc) > 80 else f"  - {nom}: {desc}"
                for nom, desc in current_state['sections_spéciales'].items()
            ])

        # Prompt pour Claude pour interpréter les modifications
        prompt = f"""Tu es un assistant qui aide à enrichir manuellement l'indexation d'un mémoire technique.

DOCUMENT ACTUEL:
Nom: {doc.get('filename', 'Inconnu')}

ÉTAT ACTUEL DE L'INDEXATION:
- Résumé: {current_state['résumé']}
- Mots-clés: {current_state['mots-clés']}
- Thèmes: {current_state['thèmes']}
- Nombre de pages: {current_state['nombre_pages'] if current_state['nombre_pages'] else 'non spécifié'}
- Format du document: {current_state['format_document']}
- Matériaux: {', '.join(current_state['caractéristiques'].get('materials', []))}
- Domaines: {', '.join(current_state['caractéristiques'].get('focus_areas', []))}
- Méthodologie: {', '.join(current_state['caractéristiques'].get('methodology', []))}
- Équipements: {', '.join(current_state['caractéristiques'].get('equipment', []))}
- Membres équipe: {', '.join(current_state['caractéristiques'].get('team_members', []))}
- Rôles équipe: {', '.join(current_state['caractéristiques'].get('team_roles', []))}
- Références projets: {', '.join(current_state['caractéristiques'].get('project_references', []))}
- Projets cibles: {', '.join(current_state['caractéristiques'].get('target_projects', []))}
- Sections spéciales:
{sections_speciales_str}

ILLUSTRATIONS ACTUELLES ({len(current_state['illustrations'])}):
{self._format_illustrations_for_prompt(current_state['illustrations'])}

INSTRUCTION DE L'UTILISATEUR:
{natural_language_input}

TÂCHE:
Analyse l'instruction de l'utilisateur et génère les modifications à appliquer au format structuré JSON.

Les actions possibles sont:
1. MODIFIER: Remplacer complètement une valeur (texte ou dict)
2. AJOUTER: Ajouter des éléments à une liste
3. RETIRER: Retirer des éléments d'une liste
4. CRÉER: Créer une nouvelle section spéciale ou illustration
5. VIDER: Vider complètement un champ (pour special_sections notamment)

FORMAT DE RÉPONSE (JSON strict):
{{
  "modifications": [
    {{
      "action": "AJOUTER|RETIRER|MODIFIER|CRÉER|VIDER",
      "champ": "summary|keywords|themes|document_format|materials|focus_areas|methodology|equipment|team_members|team_roles|project_references|target_projects|special_sections|special_illustrations",
      "valeur": "valeur ou liste de valeurs (peut être null pour VIDER)",
      "raison": "explication courte de pourquoi cette modification"
    }}
  ],
  "résumé_modifications": "description en 1-2 phrases de toutes les modifications"
}}

CHAMPS SPÉCIAUX:
- document_format: Format du document, par exemple "court (moins de 10 pages)", "standard", "long (plus de 50 pages)"
- special_sections: Sections spéciales du document (dict). Utiliser VIDER pour supprimer toutes les sections spéciales.

EXEMPLES:
Input: "ajoute béton précontraint dans les matériaux et retire acier"
Output:
{{
  "modifications": [
    {{"action": "AJOUTER", "champ": "materials", "valeur": ["béton précontraint"], "raison": "Matériau manquant mentionné"}},
    {{"action": "RETIRER", "champ": "materials", "valeur": ["acier"], "raison": "Matériau non pertinent"}}
  ],
  "résumé_modifications": "Ajout de 'béton précontraint' et retrait de 'acier' dans les matériaux"
}}

Input: "change le résumé pour mettre en avant l'aspect diagnostic patrimonial"
Output:
{{
  "modifications": [
    {{"action": "MODIFIER", "champ": "summary", "valeur": "Diagnostic patrimonial approfondi de l'ouvrage avec...", "raison": "Accent sur l'aspect patrimonial"}}
  ],
  "résumé_modifications": "Résumé modifié pour mettre en avant le diagnostic patrimonial"
}}

Input: "ajoute une illustration: schéma de carottage avec foreuse, catégorie 'méthodologie', mots-clés 'carottage, béton, prélèvement'"
Output:
{{
  "modifications": [
    {{
      "action": "CRÉER",
      "champ": "special_illustrations",
      "valeur": {{
        "type": "Schéma méthodologique",
        "description": "Schéma de carottage avec foreuse diamant",
        "category": "méthodologie",
        "technical_keywords": ["carottage", "béton", "prélèvement", "foreuse"],
        "confidence": "high",
        "detection_method": "enrichissement manuel"
      }},
      "raison": "Ajout d'une nouvelle illustration manquante"
    }}
  ],
  "résumé_modifications": "Ajout d'une illustration sur le protocole de carottage"
}}

Input: "ajoute une illustration avec chemin image data/images/abc123/photo.jpg: photo de pont, catégorie 'diagnostic', mots-clés 'pont, fissure, pathologie'"
Output:
{{
  "modifications": [
    {{
      "action": "CRÉER",
      "champ": "special_illustrations",
      "valeur": {{
        "type": "Photo terrain",
        "description": "Photo de pont montrant fissures et pathologies",
        "category": "diagnostic",
        "technical_keywords": ["pont", "fissure", "pathologie"],
        "image_path": "data/images/abc123/photo.jpg",
        "confidence": "high",
        "detection_method": "enrichissement manuel"
      }},
      "raison": "Ajout d'une illustration avec image uploadée"
    }}
  ],
  "résumé_modifications": "Ajout d'une photo de diagnostic de pont"
}}

Input: "modifie l'illustration 1: ajoute les mots-clés 'géoradar, radar pénétrant, détection armatures'"
Output:
{{
  "modifications": [
    {{
      "action": "MODIFIER",
      "champ": "special_illustrations",
      "valeur": {{
        "index": 0,
        "updates": {{
          "technical_keywords": ["géoradar", "radar pénétrant", "détection armatures"]
        }}
      }},
      "raison": "Enrichissement des mots-clés de l'illustration 1"
    }}
  ],
  "résumé_modifications": "Ajout de mots-clés techniques à l'illustration 1"
}}

Input: "modifie l'illustration 2: change description 'Nouvelle description', catégorie 'diagnostic', type 'Photo', mots-clés 'a,b,c', chemin image 'data/images/abc123/new.jpg'"
Output:
{{
  "modifications": [
    {{
      "action": "MODIFIER",
      "champ": "special_illustrations",
      "valeur": {{
        "index": 1,
        "updates": {{
          "description": "Nouvelle description",
          "category": "diagnostic",
          "type": "Photo",
          "technical_keywords": ["a", "b", "c"],
          "image_path": "data/images/abc123/new.jpg"
        }}
      }},
      "raison": "Mise à jour complète de l'illustration 2"
    }}
  ],
  "résumé_modifications": "Modification de tous les champs de l'illustration 2"
}}

Input: "ce mémoire technique est au format court (moins de 10 pages)"
Output:
{{
  "modifications": [
    {{"action": "MODIFIER", "champ": "document_format", "valeur": "court (moins de 10 pages)", "raison": "Format du document spécifié par l'utilisateur"}}
  ],
  "résumé_modifications": "Format du document défini comme court"
}}

Input: "il n'y a aucune section spéciale dans ce mémoire technique"
Output:
{{
  "modifications": [
    {{"action": "VIDER", "champ": "special_sections", "valeur": null, "raison": "Pas de section spéciale dans ce document"}}
  ],
  "résumé_modifications": "Suppression de toutes les sections spéciales"
}}

Input: "ajoute les sections spéciales: RSE (sécurité, déchets), Décarbonation (déplacements, numérique)"
Output:
{{
  "modifications": [
    {{"action": "CRÉER", "champ": "special_sections", "valeur": {{"RSE": "sécurité, gestion des déchets", "Décarbonation": "déplacements, systèmes numériques"}}, "raison": "Sections spéciales mentionnées par l'utilisateur"}}
  ],
  "résumé_modifications": "Ajout de 2 sections spéciales: RSE et Décarbonation"
}}

Input: "vide les sections et ajoute: Habilitations (CACES, SS4), PAQ (contrôle qualité)"
Output:
{{
  "modifications": [
    {{"action": "VIDER", "champ": "special_sections", "valeur": null, "raison": "Nettoyage des sections existantes"}},
    {{"action": "CRÉER", "champ": "special_sections", "valeur": {{"Habilitations": "CACES, SS4", "PAQ": "contrôle qualité"}}, "raison": "Nouvelles sections spécifiées"}}
  ],
  "résumé_modifications": "Sections vidées puis ajout de Habilitations et PAQ"
}}

Input: "enlève les sections spéciales Normes Eurocodes et PAQ"
Output:
{{
  "modifications": [
    {{"action": "RETIRER", "champ": "special_sections", "valeur": ["Normes Eurocodes", "PAQ"], "raison": "Sections à supprimer spécifiées par l'utilisateur"}}
  ],
  "résumé_modifications": "Retrait des sections Normes Eurocodes et PAQ"
}}

Input: "retire la section spéciale Analyse modale"
Output:
{{
  "modifications": [
    {{"action": "RETIRER", "champ": "special_sections", "valeur": ["Analyse modale"], "raison": "Section à supprimer"}}
  ],
  "résumé_modifications": "Retrait de la section Analyse modale"
}}

IMPORTANT:
- Réponds UNIQUEMENT en JSON valide
- Ne génère que les modifications demandées par l'utilisateur, ne propose pas de modifications non demandées
- Si tu modifies document_format, assure-toi qu'il soit cohérent avec le nombre de pages réel du document (court = moins de 10 pages, standard = 10-50 pages, long = plus de 50 pages)
- Sois précis sur les valeurs à ajouter/retirer
- Pour MODIFIER un résumé, propose un nouveau résumé complet en gardant les éléments clés existants
- Pour modifier une illustration existante, utilise son numéro (1-indexed) et convertis en index 0-based (illustration 1 = index 0, illustration 2 = index 1, etc.)
- Pour les illustrations, utilise toujours le champ "technical_keywords" pour les mots-clés techniques (pas "keywords")
- Pour special_sections: TOUJOURS utiliser le format simple {{"nom": "description"}}. JAMAIS de dictionnaires imbriqués comme {{"nom": {{"titre": "...", "sous_sections": [...]}}}}. La description doit être une chaîne de texte simple.
"""

        try:
            message = self.client.messages.create(
                model=config.SUMMARY_MODEL,
                max_tokens=config.SUMMARY_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            original_response = response_text  # Garder l'original pour debug

            # Parser le JSON de réponse
            # Nettoyer la réponse si elle contient des markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Si toujours pas de JSON, essayer de trouver le JSON dans la réponse
            if not response_text.strip().startswith("{"):
                # Chercher le premier { et le dernier }
                start_idx = response_text.find("{")
                end_idx = response_text.rfind("}")
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    response_text = response_text[start_idx:end_idx + 1]

            if not response_text.strip():
                raise json.JSONDecodeError("Réponse vide", "", 0)

            modifications = json.loads(response_text)

            # Ajouter l'input original pour historique
            modifications["original_input"] = natural_language_input
            modifications["interpreted_at"] = datetime.now().isoformat()

            return modifications

        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON: {e}")
            logger.error(f"Réponse brute: {original_response}")
            return {
                "error": f"Erreur d'interprétation: {str(e)}",
                "raw_response": original_response,
                "modifications": [],
                "résumé_modifications": "Échec de l'interprétation"
            }
        except Exception as e:
            logger.error(f"Erreur lors de l'interprétation: {e}")
            return {
                "error": str(e),
                "modifications": [],
                "résumé_modifications": "Erreur lors de l'interprétation"
            }

    def apply_enrichment(
        self, file_hash: str, modifications: Dict, user_validated: bool = True
    ) -> bool:
        """Applique les enrichissements validés par l'utilisateur.

        Args:
            file_hash: Hash du document
            modifications: Modifications à appliquer
            user_validated: Si l'utilisateur a validé

        Returns:
            True si succès, False sinon
        """
        if not user_validated:
            logger.info("Enrichissement non validé par l'utilisateur, annulation")
            return False

        index = self.load_index()

        # Trouver le document
        doc_index = None
        for i, doc in enumerate(index.get("documents", [])):
            if doc.get("file_hash") == file_hash:
                doc_index = i
                break

        if doc_index is None:
            logger.error(f"Document introuvable: {file_hash}")
            return False

        doc = index["documents"][doc_index]

        # Appliquer chaque modification
        for modif in modifications.get("modifications", []):
            action = modif.get("action")
            champ = modif.get("champ")
            valeur = modif.get("valeur")

            if action == "MODIFIER":
                if champ == "summary":
                    doc["summary"] = valeur
                elif champ == "keywords":
                    doc["keywords"] = valeur
                elif champ == "themes":
                    doc["themes"] = valeur
                elif champ == "document_format":
                    doc["document_format"] = valeur
                elif champ == "special_sections":
                    # Remplacer les sections spéciales
                    if "characteristics" not in doc:
                        doc["characteristics"] = {}
                    if isinstance(valeur, dict):
                        doc["characteristics"]["special_sections"] = valeur
                elif champ == "special_illustrations":
                    # Modifier une illustration existante
                    # valeur devrait contenir: {"index": 0, "updates": {...}}
                    if isinstance(valeur, dict) and "index" in valeur:
                        idx = valeur["index"]
                        updates = valeur.get("updates", {})
                        if "special_illustrations" in doc and 0 <= idx < len(doc["special_illustrations"]):
                            # Mettre à jour les champs spécifiés
                            for key, value in updates.items():
                                doc["special_illustrations"][idx][key] = value
                        else:
                            logger.warning(f"Index d'illustration invalide: {idx}")
                elif champ in ["materials", "focus_areas", "methodology", "structure_types",
                           "equipment", "team_members", "team_roles", "project_references",
                           "target_projects"]:
                    # MODIFIER remplace complètement la liste
                    if "characteristics" not in doc:
                        doc["characteristics"] = {}
                    # Convertir en liste si c'est une chaîne
                    if isinstance(valeur, str):
                        # Séparer par virgules et nettoyer
                        valeur = [v.strip() for v in valeur.split(",") if v.strip()]
                    elif not isinstance(valeur, list):
                        valeur = [valeur]
                    doc["characteristics"][champ] = valeur
                    logger.info(f"Champ '{champ}' modifié: {valeur}")
                else:
                    logger.warning(f"Champ MODIFIER non supporté: {champ}")

            elif action == "AJOUTER":
                # Gestion des champs texte (keywords, themes) - ajout à la chaîne existante
                if champ == "keywords":
                    current_keywords = doc.get("keywords", "")
                    # Parser les mots-clés existants
                    existing = [k.strip().lower() for k in current_keywords.split(",") if k.strip()]
                    # Ajouter les nouveaux mots-clés
                    new_keywords = valeur if isinstance(valeur, list) else [valeur]
                    for kw in new_keywords:
                        if kw.strip().lower() not in existing:
                            if current_keywords:
                                current_keywords += f", {kw.strip()}"
                            else:
                                current_keywords = kw.strip()
                            existing.append(kw.strip().lower())
                    doc["keywords"] = current_keywords
                    logger.info(f"Mots-clés mis à jour: {current_keywords}")

                elif champ == "themes":
                    current_themes = doc.get("themes", "")
                    # Parser les thèmes existants
                    existing = [t.strip().lower() for t in current_themes.split(",") if t.strip()]
                    # Ajouter les nouveaux thèmes
                    new_themes = valeur if isinstance(valeur, list) else [valeur]
                    for theme in new_themes:
                        if theme.strip().lower() not in existing:
                            if current_themes:
                                current_themes += f", {theme.strip()}"
                            else:
                                current_themes = theme.strip()
                            existing.append(theme.strip().lower())
                    doc["themes"] = current_themes
                    logger.info(f"Thèmes mis à jour: {current_themes}")

                elif champ in ["materials", "focus_areas", "methodology", "structure_types",
                           "equipment", "team_members", "team_roles", "project_references",
                           "target_projects"]:
                    if "characteristics" not in doc:
                        doc["characteristics"] = {}
                    if champ not in doc["characteristics"]:
                        doc["characteristics"][champ] = []

                    # Ajouter les valeurs si elles n'existent pas déjà
                    current_values = [v.lower() for v in doc["characteristics"][champ]]
                    for v in valeur if isinstance(valeur, list) else [valeur]:
                        if v.lower() not in current_values:
                            doc["characteristics"][champ].append(v)

                elif champ == "special_illustrations":
                    # Ajouter des mots-clés à une illustration existante
                    # valeur devrait contenir: {"index": 0, "technical_keywords": [...]}
                    if isinstance(valeur, dict) and "index" in valeur:
                        idx = valeur["index"]
                        if "special_illustrations" in doc and 0 <= idx < len(doc["special_illustrations"]):
                            illust = doc["special_illustrations"][idx]
                            # Ajouter les mots-clés techniques
                            if "technical_keywords" in valeur:
                                if "technical_keywords" not in illust:
                                    illust["technical_keywords"] = []
                                existing = [k.lower() for k in illust["technical_keywords"]]
                                for kw in valeur["technical_keywords"]:
                                    if kw.lower() not in existing:
                                        illust["technical_keywords"].append(kw)
                        else:
                            logger.warning(f"Index d'illustration invalide: {idx}")

            elif action == "RETIRER":
                # Gestion des champs texte (keywords, themes)
                if champ == "keywords":
                    current_keywords = doc.get("keywords", "")
                    keywords_list = [k.strip() for k in current_keywords.split(",") if k.strip()]
                    valeurs_a_retirer = [v.lower() for v in (valeur if isinstance(valeur, list) else [valeur])]
                    keywords_list = [k for k in keywords_list if k.lower() not in valeurs_a_retirer]
                    doc["keywords"] = ", ".join(keywords_list)
                    logger.info(f"Mots-clés après retrait: {doc['keywords']}")

                elif champ == "themes":
                    current_themes = doc.get("themes", "")
                    themes_list = [t.strip() for t in current_themes.split(",") if t.strip()]
                    valeurs_a_retirer = [v.lower() for v in (valeur if isinstance(valeur, list) else [valeur])]
                    themes_list = [t for t in themes_list if t.lower() not in valeurs_a_retirer]
                    doc["themes"] = ", ".join(themes_list)
                    logger.info(f"Thèmes après retrait: {doc['themes']}")

                elif champ in ["materials", "focus_areas", "methodology", "structure_types",
                           "equipment", "team_members", "team_roles", "project_references",
                           "target_projects"]:
                    if "characteristics" in doc and champ in doc["characteristics"]:
                        # Retirer les valeurs
                        valeurs_a_retirer = [v.lower() for v in (valeur if isinstance(valeur, list) else [valeur])]
                        doc["characteristics"][champ] = [
                            v for v in doc["characteristics"][champ]
                            if v.lower() not in valeurs_a_retirer
                        ]

                elif champ == "special_sections":
                    # Retirer des sections spécifiques par leur nom (avec matching partiel)
                    if "characteristics" in doc and "special_sections" in doc["characteristics"]:
                        sections = doc["characteristics"]["special_sections"]
                        noms_a_retirer = [v.lower() for v in (valeur if isinstance(valeur, list) else [valeur])]

                        def should_remove(section_name):
                            """Vérifie si la section doit être retirée (matching partiel)."""
                            section_lower = section_name.lower()
                            for nom in noms_a_retirer:
                                # Match exact ou partiel (le nom à retirer est contenu dans le nom de section)
                                if nom in section_lower or section_lower in nom:
                                    return True
                            return False

                        # Garder seulement les sections qui ne doivent pas être retirées
                        sections_filtrees = {
                            nom: desc for nom, desc in sections.items()
                            if not should_remove(nom)
                        }
                        removed = set(sections.keys()) - set(sections_filtrees.keys())
                        doc["characteristics"]["special_sections"] = sections_filtrees
                        logger.info(f"Sections retirées: {removed}")
                        logger.info(f"Sections restantes: {list(sections_filtrees.keys())}")

            elif action == "CRÉER":
                if champ == "special_sections":
                    # valeur devrait être un dict {nom_section: description}
                    if "characteristics" not in doc:
                        doc["characteristics"] = {}
                    if "special_sections" not in doc["characteristics"]:
                        doc["characteristics"]["special_sections"] = {}

                    if isinstance(valeur, dict):
                        # Nettoyer les valeurs si elles sont des dicts imbriqués
                        cleaned_sections = {}
                        for nom, desc in valeur.items():
                            if isinstance(desc, dict):
                                # Extraire le titre ou aplatir le dict
                                if "titre" in desc:
                                    titre = desc["titre"]
                                    sous_sections = desc.get("sous_sections", [])
                                    if sous_sections:
                                        cleaned_sections[nom] = f"{titre} ({', '.join(sous_sections)})"
                                    else:
                                        cleaned_sections[nom] = titre
                                else:
                                    # Convertir le dict en string
                                    cleaned_sections[nom] = str(desc)
                                logger.warning(f"Section '{nom}' convertie de dict en string")
                            else:
                                cleaned_sections[nom] = desc
                        doc["characteristics"]["special_sections"].update(cleaned_sections)

                elif champ == "special_illustrations":
                    # valeur devrait être une illustration complète
                    if "special_illustrations" not in doc:
                        doc["special_illustrations"] = []

                    if isinstance(valeur, dict):
                        doc["special_illustrations"].append(valeur)
                    elif isinstance(valeur, list):
                        doc["special_illustrations"].extend(valeur)

            elif action == "VIDER":
                # Vider complètement un champ
                if champ == "special_sections":
                    if "characteristics" in doc and "special_sections" in doc["characteristics"]:
                        doc["characteristics"]["special_sections"] = {}
                        logger.info("Sections spéciales vidées")
                elif champ == "special_illustrations":
                    doc["special_illustrations"] = []
                    logger.info("Illustrations vidées")
                elif champ in ["materials", "focus_areas", "methodology", "structure_types",
                             "equipment", "team_members", "team_roles", "project_references",
                             "target_projects"]:
                    if "characteristics" in doc and champ in doc["characteristics"]:
                        doc["characteristics"][champ] = []
                        logger.info(f"Champ {champ} vidé")
                else:
                    logger.warning(f"Champ VIDER non supporté: {champ}")

        # Marquer comme enrichi manuellement
        if "manual_enrichments" not in doc:
            doc["manual_enrichments"] = []

        enrichment_entry = {
            "timestamp": datetime.now().isoformat(),
            "original_input": modifications.get("original_input", ""),
            "résumé": modifications.get("résumé_modifications", ""),
            "modifications_count": len(modifications.get("modifications", []))
        }
        doc["manual_enrichments"].append(enrichment_entry)
        doc["manually_enriched"] = True
        doc["last_manual_enrichment"] = datetime.now().isoformat()

        # Sauvegarder l'index mis à jour
        index["documents"][doc_index] = doc
        self.save_index(index)

        # Sauvegarder dans l'historique des enrichissements (pour apprentissage)
        self._save_enrichment_history(file_hash, doc.get("filename"), modifications)

        # Déclencher l'apprentissage automatique
        try:
            logger.info("Déclenchement du cycle d'apprentissage automatique...")
            learning_system = get_learning_system()
            learning_result = learning_system.run_learning_cycle()

            if learning_result.get("success"):
                improvements_count = len(learning_result.get("improvements", {}).get("improvements", []))
                logger.info(f"Apprentissage terminé: {improvements_count} amélioration(s) proposée(s)")
            else:
                logger.warning("Échec du cycle d'apprentissage")
        except Exception as e:
            logger.error(f"Erreur lors de l'apprentissage: {e}")
            # Ne pas bloquer l'enrichissement si l'apprentissage échoue

        logger.info(f"Enrichissement appliqué avec succès pour {doc.get('filename')}")
        return True

    def _save_enrichment_history(
        self, file_hash: str, filename: str, modifications: Dict
    ):
        """Sauvegarde l'historique des enrichissements pour apprentissage futur.

        Args:
            file_hash: Hash du document
            filename: Nom du fichier
            modifications: Modifications appliquées
        """
        # Charger l'historique existant
        history = self.storage.read_json("enrichments_history")
        if history is None:
            history = {"enrichments": []}

        # Ajouter cette enrichissement
        history["enrichments"].append({
            "timestamp": datetime.now().isoformat(),
            "file_hash": file_hash,
            "filename": filename,
            "modifications": modifications
        })

        # Sauvegarder
        self.storage.write_json("enrichments_history", history)
        logger.info("Enrichissement sauvegardé dans l'historique")

    def get_enrichment_stats(self) -> Dict:
        """Récupère les statistiques d'enrichissement.

        Returns:
            Statistiques d'enrichissement
        """
        history = self.storage.read_json("enrichments_history")
        if history is None:
            return {
                "total_enrichments": 0,
                "documents_enriched": 0,
                "last_enrichment": None
            }

        enrichments = history.get("enrichments", [])
        unique_docs = set(e.get("file_hash") for e in enrichments)

        return {
            "total_enrichments": len(enrichments),
            "documents_enriched": len(unique_docs),
            "last_enrichment": enrichments[-1].get("timestamp") if enrichments else None
        }
