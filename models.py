"""Modèle de données : statuts et traçabilité des documents."""
from datetime import datetime
from typing import Dict, List, Optional

# Constantes de statut
STATUS_INDEXED = "indexe_non_valide"
STATUS_VALIDATED = "valide"
STATUS_ENRICHED = "enrichi"

ALL_STATUSES = [STATUS_INDEXED, STATUS_VALIDATED, STATUS_ENRICHED]


def set_indexed_by(doc: Dict, user: str) -> Dict:
    """Marque qui a indexé le document.

    Args:
        doc: Document de l'index
        user: Nom de l'utilisateur

    Returns:
        Document mis à jour
    """
    doc["status"] = STATUS_INDEXED
    doc["indexed_by"] = user
    return doc


def validate_document(doc: Dict, user: str) -> Dict:
    """Valide un document (transition indexe_non_valide → valide).

    Args:
        doc: Document de l'index
        user: Nom du validateur

    Returns:
        Document mis à jour
    """
    doc["status"] = STATUS_VALIDATED
    doc["validated_by"] = user
    doc["validated_at"] = datetime.now().isoformat()
    return doc


def mark_enriched(doc: Dict, user: str) -> Dict:
    """Marque un document comme enrichi.

    Args:
        doc: Document de l'index
        user: Nom de l'utilisateur

    Returns:
        Document mis à jour
    """
    doc["status"] = STATUS_ENRICHED
    if "enriched_by" not in doc or not isinstance(doc["enriched_by"], list):
        doc["enriched_by"] = []
    if user not in doc["enriched_by"]:
        doc["enriched_by"].append(user)
    doc["last_enriched_by"] = user
    return doc


def migrate_document(doc: Dict) -> Dict:
    """Ajoute les nouveaux champs de traçabilité à un document existant.

    Args:
        doc: Document de l'index (potentiellement ancien format)

    Returns:
        Document avec les nouveaux champs
    """
    # Déterminer le statut initial
    if "status" not in doc:
        if doc.get("manually_enriched"):
            doc["status"] = STATUS_ENRICHED
        else:
            doc["status"] = STATUS_INDEXED

    # Champs de traçabilité
    if "indexed_by" not in doc:
        doc["indexed_by"] = "David"  # Documents existants indexés par David

    if "validated_by" not in doc:
        doc["validated_by"] = None

    if "validated_at" not in doc:
        doc["validated_at"] = None

    if "enriched_by" not in doc:
        if doc.get("manually_enriched"):
            doc["enriched_by"] = ["David"]
        else:
            doc["enriched_by"] = []

    if "last_enriched_by" not in doc:
        if doc.get("manually_enriched"):
            doc["last_enriched_by"] = "David"
        else:
            doc["last_enriched_by"] = None

    # Champs Google Drive
    if "gdrive_file_id" not in doc:
        doc["gdrive_file_id"] = None

    if "gdrive_link" not in doc:
        doc["gdrive_link"] = None

    return doc


def get_documents_by_status(index: Dict, status: str) -> List[Dict]:
    """Filtre les documents par statut.

    Args:
        index: Index complet
        status: Statut recherché

    Returns:
        Liste des documents avec ce statut
    """
    return [
        doc for doc in index.get("documents", [])
        if doc.get("status") == status
    ]


def get_status_counts(index: Dict) -> Dict[str, int]:
    """Compte les documents par statut.

    Args:
        index: Index complet

    Returns:
        Dict {statut: nombre}
    """
    counts = {s: 0 for s in ALL_STATUSES}
    for doc in index.get("documents", []):
        status = doc.get("status", STATUS_INDEXED)
        counts[status] = counts.get(status, 0) + 1
    return counts
