"""Implémentation Google Drive du backend de stockage."""
import io
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

import config
from storage import StorageBackend

logger = logging.getLogger(__name__)

# Mapping cle logique -> nom de fichier JSON
JSON_KEY_MAP = {
    "index": "index.json",
    "enrichments_history": "enrichments_history.json",
    "learned_rules": "learned_rules.json",
    "learning_insights": "learning_insights.json",
    "prompt_improvements": "prompt_improvements.json",
}

# Scopes requis pour l'API Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive"]

# TTL du cache en secondes
CACHE_TTL_SECONDS = 30


class GDriveStorage(StorageBackend):
    """Backend de stockage Google Drive."""

    def __init__(self):
        """Initialise le backend Google Drive."""
        self._service = None
        self._data_folder_id = config.GDRIVE_DATA_FOLDER_ID
        self._docs_folder_id = config.GDRIVE_DOCS_FOLDER_ID
        # Cache des IDs de sous-dossiers pour eviter des lookups repetes
        self._folder_id_cache: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _get_service(self):
        """Retourne une instance authentifiee du service Google Drive.

        Tente de charger les credentials depuis st.secrets (cle
        ``GOOGLE_SERVICE_ACCOUNT_JSON``), puis depuis un fichier dont le
        chemin est indique par ``GOOGLE_SERVICE_ACCOUNT_FILE``.

        Le service est mis en cache sur l'instance pour eviter de
        re-creer la connexion a chaque appel.
        """
        if self._service is not None:
            return self._service

        creds = None

        # 1. Essayer depuis st.secrets (JSON string)
        try:
            import streamlit as st

            if hasattr(st, "secrets"):
                sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
                if sa_json:
                    info = json.loads(sa_json) if isinstance(sa_json, str) else dict(sa_json)
                    creds = service_account.Credentials.from_service_account_info(
                        info, scopes=SCOPES
                    )
        except Exception:
            pass

        # 2. Fallback : fichier sur disque
        if creds is None:
            sa_file = config._get_secret("GOOGLE_SERVICE_ACCOUNT_FILE", "")
            if sa_file:
                creds = service_account.Credentials.from_service_account_file(
                    sa_file, scopes=SCOPES
                )

        if creds is None:
            raise RuntimeError(
                "Impossible de charger les credentials Google. "
                "Definissez GOOGLE_SERVICE_ACCOUNT_JSON dans st.secrets ou "
                "GOOGLE_SERVICE_ACCOUNT_FILE dans l'environnement."
            )

        self._service = build("drive", "v3", credentials=creds)
        return self._service

    def _find_file(self, name: str, parent_id: str) -> Optional[Dict]:
        """Recherche un fichier par nom dans un dossier parent.

        Args:
            name: Nom exact du fichier recherche.
            parent_id: ID du dossier parent Drive.

        Returns:
            Dict avec les metadonnees du fichier ou None.
        """
        service = self._get_service()
        escaped_name = name.replace("'", "\\'")
        query = (
            f"name = '{escaped_name}' and '{parent_id}' in parents "
            f"and trashed = false"
        )
        try:
            resp = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name, mimeType, size, modifiedTime)",
                    pageSize=1,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            files = resp.get("files", [])
            return files[0] if files else None
        except Exception as e:
            logger.error(f"Erreur recherche fichier '{name}' dans {parent_id}: {e}")
            return None

    def _create_folder(self, name: str, parent_id: str) -> str:
        """Cree un sous-dossier dans le dossier parent et retourne son ID.

        Si le dossier existe deja, retourne simplement son ID.
        """
        existing = self._find_file(name, parent_id)
        if existing:
            return existing["id"]

        service = self._get_service()
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        try:
            folder = (
                service.files()
                .create(body=metadata, fields="id", supportsAllDrives=True)
                .execute()
            )
            folder_id = folder["id"]
            logger.info(f"Dossier '{name}' cree: {folder_id}")
            return folder_id
        except Exception as e:
            logger.error(f"Erreur creation dossier '{name}': {e}")
            raise

    def _upload_file(
        self,
        name: str,
        content: bytes,
        mime_type: str,
        parent_id: str,
    ) -> str:
        """Upload ou met a jour un fichier sur Google Drive.

        Si un fichier de meme nom existe deja dans le dossier parent,
        il est mis a jour (update). Sinon il est cree.

        Returns:
            L'ID du fichier cree / mis a jour.
        """
        service = self._get_service()
        existing = self._find_file(name, parent_id)
        media = MediaIoBaseUpload(
            io.BytesIO(content), mimetype=mime_type, resumable=True
        )

        try:
            if existing:
                # Mise a jour du contenu (on ne change pas les parents)
                updated = (
                    service.files()
                    .update(
                        fileId=existing["id"],
                        media_body=media,
                        fields="id",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                return updated["id"]
            else:
                metadata = {
                    "name": name,
                    "parents": [parent_id],
                }
                created = (
                    service.files()
                    .create(
                        body=metadata,
                        media_body=media,
                        fields="id",
                        supportsAllDrives=True,
                    )
                    .execute()
                )
                return created["id"]
        except Exception as e:
            logger.error(f"Erreur upload fichier '{name}': {e}")
            raise

    def _download_file(self, file_id: str) -> Optional[bytes]:
        """Telecharge le contenu d'un fichier Drive.

        Args:
            file_id: ID du fichier Google Drive.

        Returns:
            Contenu binaire du fichier ou None en cas d'erreur.
        """
        service = self._get_service()
        try:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Erreur telechargement fichier {file_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Cache session_state (TTL 30 s)
    # ------------------------------------------------------------------

    def _cache_get(self, cache_key: str) -> Optional[Any]:
        """Lit une valeur du cache session_state si encore valide."""
        try:
            import streamlit as st

            store = st.session_state.get("_gdrive_cache", {})
            entry = store.get(cache_key)
            if entry is None:
                return None
            if time.time() - entry["ts"] > CACHE_TTL_SECONDS:
                # Expire
                store.pop(cache_key, None)
                st.session_state["_gdrive_cache"] = store
                return None
            return entry["data"]
        except Exception:
            return None

    def _cache_set(self, cache_key: str, data: Any) -> None:
        """Ecrit une valeur dans le cache session_state."""
        try:
            import streamlit as st

            store = st.session_state.get("_gdrive_cache", {})
            store[cache_key] = {"data": data, "ts": time.time()}
            st.session_state["_gdrive_cache"] = store
        except Exception:
            pass

    def _cache_invalidate(self, cache_key: str) -> None:
        """Invalide une entree du cache."""
        try:
            import streamlit as st

            store = st.session_state.get("_gdrive_cache", {})
            store.pop(cache_key, None)
            st.session_state["_gdrive_cache"] = store
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers de resolution de dossiers
    # ------------------------------------------------------------------

    def _get_images_folder_id(self, doc_hash: str) -> str:
        """Retourne l'ID du sous-dossier data/images/{doc_hash},
        en le creant si necessaire."""
        images_root_id = self._get_or_create_subfolder("images", self._data_folder_id)
        return self._get_or_create_subfolder(doc_hash, images_root_id)

    def _get_locks_folder_id(self) -> str:
        """Retourne l'ID du sous-dossier data/locks/."""
        return self._get_or_create_subfolder("locks", self._data_folder_id)

    def _get_or_create_subfolder(self, name: str, parent_id: str) -> str:
        """Retourne l'ID d'un sous-dossier, avec cache interne."""
        cache_key = f"{parent_id}/{name}"
        if cache_key in self._folder_id_cache:
            return self._folder_id_cache[cache_key]
        folder_id = self._create_folder(name, parent_id)
        self._folder_id_cache[cache_key] = folder_id
        return folder_id

    # ------------------------------------------------------------------
    # JSON data
    # ------------------------------------------------------------------

    def _json_filename(self, key: str) -> str:
        """Resout le nom de fichier JSON a partir de la cle logique."""
        filename = JSON_KEY_MAP.get(key)
        if not filename:
            raise ValueError(f"Cle JSON inconnue: {key}")
        return filename

    def read_json(self, key: str) -> Optional[Dict]:
        # Verifier le cache
        cached = self._cache_get(f"json:{key}")
        if cached is not None:
            return cached

        filename = self._json_filename(key)
        file_info = self._find_file(filename, self._data_folder_id)
        if not file_info:
            return None

        raw = self._download_file(file_info["id"])
        if raw is None:
            return None

        try:
            data = json.loads(raw.decode("utf-8"))
            self._cache_set(f"json:{key}", data)
            return data
        except Exception as e:
            logger.error(f"Erreur decodage JSON '{key}': {e}")
            return None

    def write_json(self, key: str, data: Dict) -> None:
        filename = self._json_filename(key)
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._upload_file(filename, content, "application/json", self._data_folder_id)
        # Mettre a jour le cache
        self._cache_set(f"json:{key}", data)

    def json_exists(self, key: str) -> bool:
        # Verifier le cache d'abord
        cached = self._cache_get(f"json:{key}")
        if cached is not None:
            return True

        filename = self._json_filename(key)
        return self._find_file(filename, self._data_folder_id) is not None

    # ------------------------------------------------------------------
    # Images
    # ------------------------------------------------------------------

    def save_image(self, doc_hash: str, filename: str, data: bytes) -> str:
        folder_id = self._get_images_folder_id(doc_hash)

        # Determiner le type MIME
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

        self._upload_file(filename, data, mime_type, folder_id)
        # Retourner un chemin logique coherent avec le format local
        return f"data/images/{doc_hash}/{filename}"

    def read_image(self, path: str) -> Optional[bytes]:
        """Lit une image depuis Google Drive en resolvant le chemin logique."""
        parts = path.replace("\\", "/").split("/")
        # Chemin attendu: data/images/{doc_hash}/{filename}
        try:
            images_idx = parts.index("images")
            doc_hash = parts[images_idx + 1]
            filename = parts[images_idx + 2]
        except (ValueError, IndexError):
            logger.error(f"Chemin image invalide: {path}")
            return None

        folder_id = self._get_images_folder_id(doc_hash)
        file_info = self._find_file(filename, folder_id)
        if not file_info:
            return None
        return self._download_file(file_info["id"])

    def image_exists(self, path: str) -> bool:
        parts = path.replace("\\", "/").split("/")
        try:
            images_idx = parts.index("images")
            doc_hash = parts[images_idx + 1]
            filename = parts[images_idx + 2]
        except (ValueError, IndexError):
            return False

        # Verifier l'existence du dossier images puis du fichier
        images_root = self._find_file("images", self._data_folder_id)
        if not images_root:
            return False
        hash_folder = self._find_file(doc_hash, images_root["id"])
        if not hash_folder:
            return False
        return self._find_file(filename, hash_folder["id"]) is not None

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def list_documents(self) -> List[Dict]:
        if not self._docs_folder_id:
            return []

        # Verifier le cache
        cached = self._cache_get("documents_list")
        if cached is not None:
            return cached

        service = self._get_service()
        supported = config.SUPPORTED_EXTENSIONS  # [".docx", ".pdf", ".doc", ".docm"]

        result: List[Dict] = []
        page_token = None

        try:
            while True:
                query = (
                    f"'{self._docs_folder_id}' in parents and trashed = false "
                    f"and mimeType != 'application/vnd.google-apps.folder'"
                )
                resp = (
                    service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, size, modifiedTime, mimeType)",
                        pageSize=1000,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )

                for f in resp.get("files", []):
                    name = f.get("name", "")
                    # Filtrer par extension supportee
                    if not any(name.lower().endswith(ext) for ext in supported):
                        continue
                    result.append(
                        {
                            "name": name,
                            "id": f["id"],
                            "size": int(f.get("size", 0)),
                            "modified": f.get("modifiedTime", ""),
                            "mimeType": f.get("mimeType", ""),
                        }
                    )

                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

            self._cache_set("documents_list", result)
            return result
        except Exception as e:
            logger.error(f"Erreur listing documents: {e}")
            return []

    def download_document(self, doc_id: str) -> Optional[bytes]:
        return self._download_file(doc_id)

    def get_document_link(self, doc_id: str) -> str:
        """Retourne l'URL de visualisation Google Drive du document."""
        return f"https://drive.google.com/file/d/{doc_id}/view"

    # ------------------------------------------------------------------
    # Verrous (locks)
    # ------------------------------------------------------------------

    def acquire_lock(self, name: str, owner: str) -> bool:
        locks_folder = self._get_locks_folder_id()
        lock_filename = f"{name}.json"

        # Verifier si un verrou existe deja
        existing = self._find_file(lock_filename, locks_folder)
        if existing:
            raw = self._download_file(existing["id"])
            if raw:
                try:
                    info = json.loads(raw.decode("utf-8"))
                    if info.get("owner") != owner:
                        return False
                    # Meme proprietaire -> renouveler
                except Exception:
                    pass

        lock_data = {
            "owner": owner,
            "acquired_at": datetime.now().isoformat(),
        }
        content = json.dumps(lock_data, ensure_ascii=False, indent=2).encode("utf-8")
        self._upload_file(lock_filename, content, "application/json", locks_folder)
        return True

    def release_lock(self, name: str, owner: str) -> bool:
        locks_folder = self._get_locks_folder_id()
        lock_filename = f"{name}.json"

        existing = self._find_file(lock_filename, locks_folder)
        if not existing:
            return True  # Pas de verrou, rien a liberer

        raw = self._download_file(existing["id"])
        if raw:
            try:
                info = json.loads(raw.decode("utf-8"))
                if info.get("owner") != owner:
                    return False  # Pas le proprietaire
            except Exception:
                pass

        # Supprimer le fichier verrou (mise a la corbeille)
        service = self._get_service()
        try:
            service.files().delete(fileId=existing["id"], supportsAllDrives=True).execute()
        except Exception as e:
            logger.error(f"Erreur suppression verrou '{name}': {e}")
            return False
        return True

    def get_lock_info(self, name: str) -> Optional[Dict]:
        locks_folder = self._get_locks_folder_id()
        lock_filename = f"{name}.json"

        existing = self._find_file(lock_filename, locks_folder)
        if not existing:
            return None

        raw = self._download_file(existing["id"])
        if raw is None:
            return None

        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None
