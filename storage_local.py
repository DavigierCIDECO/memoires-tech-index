"""Implémentation locale du backend de stockage."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from storage import StorageBackend

logger = logging.getLogger(__name__)

# Mapping clé logique → nom de fichier JSON
JSON_KEY_MAP = {
    "index": "index.json",
    "enrichments_history": "enrichments_history.json",
    "learned_rules": "learned_rules.json",
    "learning_insights": "learning_insights.json",
    "prompt_improvements": "prompt_improvements.json",
}


class LocalStorage(StorageBackend):
    """Backend de stockage local (fichiers sur disque)."""

    def __init__(self):
        """Initialise le stockage local."""
        self.data_dir = config.DATA_DIR
        self.data_dir.mkdir(exist_ok=True)

    def _json_path(self, key: str) -> Path:
        """Résout le chemin d'un fichier JSON à partir de sa clé."""
        filename = JSON_KEY_MAP.get(key)
        if not filename:
            raise ValueError(f"Clé JSON inconnue: {key}")
        return self.data_dir / filename

    # --- JSON data ---

    def read_json(self, key: str) -> Optional[Dict]:
        path = self._json_path(key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lecture JSON {key}: {e}")
            return None

    def write_json(self, key: str, data: Dict) -> None:
        path = self._json_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def json_exists(self, key: str) -> bool:
        return self._json_path(key).exists()

    # --- Images ---

    def save_image(self, doc_hash: str, filename: str, data: bytes) -> str:
        img_dir = self.data_dir / "images" / doc_hash
        img_dir.mkdir(parents=True, exist_ok=True)
        file_path = img_dir / filename
        with open(file_path, "wb") as f:
            f.write(data)
        # Retourner le chemin relatif depuis la racine du projet
        return str(file_path.relative_to(self.data_dir.parent))

    def read_image(self, path: str) -> Optional[bytes]:
        full_path = self.data_dir.parent / path
        if not full_path.exists():
            return None
        with open(full_path, "rb") as f:
            return f.read()

    def image_exists(self, path: str) -> bool:
        return (self.data_dir.parent / path).exists()

    # --- Documents ---

    def list_documents(self) -> List[Dict]:
        """Liste les documents locaux depuis LOCAL_DOCS_PATH."""
        docs_path = config.LOCAL_DOCS_PATH
        if not docs_path:
            return []

        directory = Path(docs_path)
        if not directory.exists() or not directory.is_dir():
            return []

        result = []
        for ext in config.SUPPORTED_EXTENSIONS:
            for file_path in directory.rglob(f"*{ext}"):
                if file_path.name.startswith("~$"):
                    continue
                stat = file_path.stat()
                result.append({
                    "name": file_path.name,
                    "id": str(file_path.absolute()),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "path": file_path,
                })
        return result

    def download_document(self, doc_id: str) -> Optional[bytes]:
        """En local, le doc_id est le chemin absolu du fichier."""
        path = Path(doc_id)
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return f.read()

    def get_document_link(self, doc_id: str) -> str:
        """En local, retourne le chemin du fichier."""
        return doc_id

    # --- Verrous ---

    def _lock_path(self, name: str) -> Path:
        locks_dir = self.data_dir / ".locks"
        locks_dir.mkdir(exist_ok=True)
        return locks_dir / f"{name}.json"

    def acquire_lock(self, name: str, owner: str) -> bool:
        lock_path = self._lock_path(name)
        if lock_path.exists():
            # Vérifier si le verrou existe déjà
            info = self.get_lock_info(name)
            if info and info.get("owner") != owner:
                return False
            # Même propriétaire → renouveler
        lock_data = {
            "owner": owner,
            "acquired_at": datetime.now().isoformat(),
        }
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
        return True

    def release_lock(self, name: str, owner: str) -> bool:
        lock_path = self._lock_path(name)
        if not lock_path.exists():
            return True
        info = self.get_lock_info(name)
        if info and info.get("owner") != owner:
            return False  # Pas le propriétaire
        lock_path.unlink()
        return True

    def get_lock_info(self, name: str) -> Optional[Dict]:
        lock_path = self._lock_path(name)
        if not lock_path.exists():
            return None
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
