"""Interface abstraite pour le stockage des données."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class StorageBackend(ABC):
    """Interface abstraite pour les backends de stockage.

    Permet de basculer entre stockage local et Google Drive
    sans modifier le reste du code.
    """

    # --- JSON data ---
    @abstractmethod
    def read_json(self, key: str) -> Optional[Dict]:
        """Lit un fichier JSON identifié par sa clé.

        Args:
            key: Nom logique du fichier (ex: 'index', 'learned_rules')

        Returns:
            Contenu du fichier ou None si inexistant
        """
        ...

    @abstractmethod
    def write_json(self, key: str, data: Dict) -> None:
        """Écrit un fichier JSON identifié par sa clé.

        Args:
            key: Nom logique du fichier
            data: Données à écrire
        """
        ...

    @abstractmethod
    def json_exists(self, key: str) -> bool:
        """Vérifie si un fichier JSON existe.

        Args:
            key: Nom logique du fichier

        Returns:
            True si le fichier existe
        """
        ...

    # --- Images ---
    @abstractmethod
    def save_image(self, doc_hash: str, filename: str, data: bytes) -> str:
        """Sauvegarde une image d'illustration.

        Args:
            doc_hash: Hash du document associé
            filename: Nom du fichier image
            data: Contenu binaire de l'image

        Returns:
            Chemin relatif de l'image sauvegardée
        """
        ...

    @abstractmethod
    def read_image(self, path: str) -> Optional[bytes]:
        """Lit une image d'illustration.

        Args:
            path: Chemin relatif de l'image

        Returns:
            Contenu binaire ou None si inexistant
        """
        ...

    @abstractmethod
    def image_exists(self, path: str) -> bool:
        """Vérifie si une image existe.

        Args:
            path: Chemin relatif de l'image

        Returns:
            True si l'image existe
        """
        ...

    # --- Documents ---
    @abstractmethod
    def list_documents(self) -> List[Dict]:
        """Liste les documents disponibles à indexer.

        Returns:
            Liste de dicts avec au minimum: name, id, size, modified
        """
        ...

    @abstractmethod
    def download_document(self, doc_id: str) -> Optional[bytes]:
        """Télécharge un document pour extraction de texte.

        Args:
            doc_id: Identifiant du document (chemin local ou ID Drive)

        Returns:
            Contenu binaire du document ou None
        """
        ...

    @abstractmethod
    def get_document_link(self, doc_id: str) -> str:
        """Obtient un lien partageable vers le document.

        Args:
            doc_id: Identifiant du document

        Returns:
            Lien cliquable (chemin local ou URL Drive)
        """
        ...

    @abstractmethod
    def rename_document(self, doc_id: str, new_name: str) -> bool:
        """Renomme un document sur le backend de stockage.

        Args:
            doc_id: Identifiant du document (chemin local ou ID Drive)
            new_name: Nouveau nom du fichier

        Returns:
            True si le renommage a réussi
        """
        ...

    # --- Verrous ---
    @abstractmethod
    def acquire_lock(self, name: str, owner: str) -> bool:
        """Acquiert un verrou nommé.

        Args:
            name: Nom du verrou (ex: 'indexation')
            owner: Identifiant du propriétaire

        Returns:
            True si le verrou a été acquis
        """
        ...

    @abstractmethod
    def release_lock(self, name: str, owner: str) -> bool:
        """Libère un verrou nommé.

        Args:
            name: Nom du verrou
            owner: Identifiant du propriétaire

        Returns:
            True si le verrou a été libéré
        """
        ...

    @abstractmethod
    def get_lock_info(self, name: str) -> Optional[Dict]:
        """Récupère les informations d'un verrou.

        Args:
            name: Nom du verrou

        Returns:
            Dict avec owner, acquired_at ou None si pas de verrou
        """
        ...
