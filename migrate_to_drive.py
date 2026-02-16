#!/usr/bin/env python3
"""One-shot migration script to upload local data to Google Drive.

Uploads JSON data files, extracted images, and source documents (.docx/.pdf)
to Google Drive, then updates the index with gdrive_file_id and gdrive_link
for each document.

The script is idempotent: it checks if a file already exists in the target
Drive folder (by name) before uploading.

Usage:
    python migrate_to_drive.py \
        --credentials service_account.json \
        --data-folder-id 1ABC... \
        --docs-folder-id 1XYZ...

    # Dry run (no uploads):
    python migrate_to_drive.py \
        --credentials service_account.json \
        --data-folder-id 1ABC... \
        --docs-folder-id 1XYZ... \
        --dry-run
"""
import argparse
import json
import logging
import mimetypes
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

# ---------------------------------------------------------------------------
# Project paths (mirrors config.py without importing it, to stay standalone)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"
INDEX_FILE = DATA_DIR / "index.json"

JSON_FILES = [
    "index.json",
    "enrichments_history.json",
    "learned_rules.json",
    "learning_insights.json",
    "prompt_improvements.json",
]

SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".doc", ".docm"}

logger = logging.getLogger("migrate_to_drive")


# ---------------------------------------------------------------------------
# Google Drive helpers
# ---------------------------------------------------------------------------

def get_drive_service(credentials_path: str):
    """Build an authenticated Google Drive v3 service."""
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_files_in_folder(service, folder_id: str) -> Dict[str, dict]:
    """Return a dict mapping filename -> {id, name, mimeType} for all files
    directly inside *folder_id*.  Handles pagination.
    """
    result: Dict[str, dict] = {}
    page_token = None
    query = f"'{folder_id}' in parents and trashed = false"

    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, webViewLink)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        for f in resp.get("files", []):
            result[f["name"]] = f
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return result


def list_subfolders_in_folder(service, folder_id: str) -> Dict[str, str]:
    """Return a dict mapping subfolder name -> subfolder id."""
    result: Dict[str, str] = {}
    page_token = None
    query = (
        f"'{folder_id}' in parents and trashed = false "
        f"and mimeType = 'application/vnd.google-apps.folder'"
    )

    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        for f in resp.get("files", []):
            result[f["name"]] = f["id"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return result


def create_folder(service, name: str, parent_id: str) -> str:
    """Create a folder inside *parent_id* and return its ID."""
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id", supportsAllDrives=True).execute()
    return folder["id"]


def upload_file(
    service,
    local_path: Path,
    parent_id: str,
    mime_type: Optional[str] = None,
) -> dict:
    """Upload a local file to a Drive folder. Returns the created file metadata."""
    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(str(local_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

    metadata = {
        "name": local_path.name,
        "parents": [parent_id],
    }
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
    created = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink", supportsAllDrives=True)
        .execute()
    )
    return created


# ---------------------------------------------------------------------------
# Step 1 - Upload JSON data files
# ---------------------------------------------------------------------------

def upload_json_files(
    service, data_folder_id: str, dry_run: bool
) -> Dict[str, str]:
    """Upload the 5 JSON data files to the Drive data folder.

    Returns a dict mapping filename -> Drive file ID for uploaded files.
    """
    existing = list_files_in_folder(service, data_folder_id)
    uploaded: Dict[str, str] = {}

    for filename in JSON_FILES:
        local_path = DATA_DIR / filename
        if not local_path.exists():
            logger.warning("JSON file not found locally, skipping: %s", filename)
            continue

        if filename in existing:
            logger.info(
                "[SKIP] %s already exists in Drive (id=%s)",
                filename,
                existing[filename]["id"],
            )
            uploaded[filename] = existing[filename]["id"]
            continue

        if dry_run:
            logger.info("[DRY-RUN] Would upload JSON: %s", filename)
            continue

        logger.info("Uploading JSON: %s ...", filename)
        result = upload_file(
            service, local_path, data_folder_id, mime_type="application/json"
        )
        logger.info(
            "  -> uploaded as %s (id=%s)", result["name"], result["id"]
        )
        uploaded[filename] = result["id"]

    return uploaded


# ---------------------------------------------------------------------------
# Step 2 - Upload images preserving data/images/{hash}/ structure
# ---------------------------------------------------------------------------

def upload_images(
    service, data_folder_id: str, dry_run: bool
) -> int:
    """Upload all images from data/images/{hash}/ into Drive, preserving
    the directory structure under an 'images' subfolder inside data_folder_id.

    Returns the total number of images uploaded (or that would be uploaded).
    """
    if not IMAGES_DIR.exists():
        logger.info("No local images directory found; skipping image upload.")
        return 0

    hash_dirs = sorted(
        [d for d in IMAGES_DIR.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )
    if not hash_dirs:
        logger.info("No image hash directories found; skipping.")
        return 0

    # Ensure 'images' subfolder exists in the data Drive folder
    subfolders = list_subfolders_in_folder(service, data_folder_id)
    images_drive_id = subfolders.get("images")

    if images_drive_id is None:
        if dry_run:
            logger.info("[DRY-RUN] Would create 'images' subfolder in data folder")
            # Cannot continue meaningfully in dry-run; just count files
            count = sum(
                1
                for hd in hash_dirs
                for f in hd.iterdir()
                if f.is_file()
            )
            logger.info("[DRY-RUN] Would upload %d image(s) total", count)
            return count
        else:
            images_drive_id = create_folder(service, "images", data_folder_id)
            logger.info("Created 'images' subfolder (id=%s)", images_drive_id)

    # Cache of existing hash sub-folders on Drive
    existing_hash_folders = list_subfolders_in_folder(service, images_drive_id)

    total_uploaded = 0

    for hash_dir in hash_dirs:
        hash_name = hash_dir.name
        image_files = sorted([f for f in hash_dir.iterdir() if f.is_file()])
        if not image_files:
            continue

        # Get or create the hash subfolder on Drive
        hash_folder_id = existing_hash_folders.get(hash_name)
        if hash_folder_id is None:
            if dry_run:
                logger.info(
                    "[DRY-RUN] Would create subfolder 'images/%s' and upload %d file(s)",
                    hash_name,
                    len(image_files),
                )
                total_uploaded += len(image_files)
                continue
            else:
                hash_folder_id = create_folder(
                    service, hash_name, images_drive_id
                )
                logger.info(
                    "Created subfolder images/%s (id=%s)",
                    hash_name,
                    hash_folder_id,
                )
                existing_hash_folders[hash_name] = hash_folder_id

        # List existing files in that hash folder
        existing_images = list_files_in_folder(service, hash_folder_id)

        for img_path in image_files:
            if img_path.name in existing_images:
                logger.debug(
                    "[SKIP] images/%s/%s already on Drive",
                    hash_name,
                    img_path.name,
                )
                continue

            if dry_run:
                logger.info(
                    "[DRY-RUN] Would upload images/%s/%s",
                    hash_name,
                    img_path.name,
                )
                total_uploaded += 1
                continue

            logger.info("Uploading images/%s/%s ...", hash_name, img_path.name)
            upload_file(service, img_path, hash_folder_id)
            total_uploaded += 1

    logger.info("Images upload complete: %d file(s) processed.", total_uploaded)
    return total_uploaded


# ---------------------------------------------------------------------------
# Step 3 - Upload .docx / .pdf documents from LOCAL_DOCS_PATH
# ---------------------------------------------------------------------------

def _resolve_local_docs_path() -> Optional[Path]:
    """Resolve LOCAL_DOCS_PATH from the project's .env or environment."""
    # Try to load from dotenv without importing config (to stay standalone)
    try:
        from dotenv import load_dotenv

        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    raw = os.getenv("LOCAL_DOCS_PATH", "")
    if not raw:
        return None
    p = Path(raw)
    if p.exists() and p.is_dir():
        return p
    return None


def upload_documents(
    service,
    docs_folder_id: str,
    dry_run: bool,
) -> Dict[str, dict]:
    """Upload .docx / .pdf documents from LOCAL_DOCS_PATH to the Drive
    documents folder.

    Returns a dict mapping document filename -> {id, webViewLink} for every
    document present on Drive after this step (including already-existing ones).
    """
    docs_path = _resolve_local_docs_path()
    if docs_path is None:
        logger.warning(
            "LOCAL_DOCS_PATH is not set or does not exist. "
            "Skipping document upload."
        )
        return {}

    # Collect local document files
    local_docs: List[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        for f in docs_path.rglob(f"*{ext}"):
            if f.name.startswith("~$"):
                continue
            local_docs.append(f)
    local_docs.sort(key=lambda p: p.name)

    if not local_docs:
        logger.info("No documents found in %s", docs_path)
        return {}

    logger.info("Found %d local document(s) in %s", len(local_docs), docs_path)

    existing = list_files_in_folder(service, docs_folder_id)

    result: Dict[str, dict] = {}
    uploaded_count = 0

    for doc_path in local_docs:
        name = doc_path.name
        if name in existing:
            logger.info("[SKIP] %s already on Drive (id=%s)", name, existing[name]["id"])
            result[name] = {
                "id": existing[name]["id"],
                "webViewLink": existing[name].get("webViewLink", ""),
            }
            continue

        if dry_run:
            logger.info("[DRY-RUN] Would upload document: %s", name)
            continue

        logger.info("Uploading document: %s ...", name)
        created = upload_file(service, doc_path, docs_folder_id)
        logger.info("  -> id=%s", created["id"])
        result[name] = {
            "id": created["id"],
            "webViewLink": created.get("webViewLink", ""),
        }
        uploaded_count += 1

    logger.info(
        "Document upload complete: %d new, %d already existed.",
        uploaded_count,
        len(result) - uploaded_count,
    )
    return result


# ---------------------------------------------------------------------------
# Step 4 & 5 - Update the index with gdrive metadata and re-upload it
# ---------------------------------------------------------------------------

def update_index_with_drive_ids(
    service,
    data_folder_id: str,
    drive_docs: Dict[str, dict],
    dry_run: bool,
) -> int:
    """Read the local index, add gdrive_file_id and gdrive_link to each
    document entry that was uploaded, then re-upload the index.

    Returns the number of documents updated in the index.
    """
    if not INDEX_FILE.exists():
        logger.error("Index file not found: %s", INDEX_FILE)
        return 0

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    documents = index.get("documents", [])
    updated = 0

    for doc in documents:
        filename = doc.get("filename", "")
        if not filename:
            continue

        # Check if we already have Drive metadata
        if doc.get("gdrive_file_id") and doc.get("gdrive_link"):
            logger.debug(
                "[SKIP] %s already has gdrive metadata in index", filename
            )
            continue

        info = drive_docs.get(filename)
        if info is None:
            logger.debug(
                "No Drive info for %s (not uploaded or not found)", filename
            )
            continue

        doc["gdrive_file_id"] = info["id"]
        doc["gdrive_link"] = info.get("webViewLink", "")
        updated += 1
        logger.info("Updated index entry: %s -> gdrive_file_id=%s", filename, info["id"])

    if updated == 0 and not dry_run:
        logger.info("No index entries needed updating.")
        return 0

    if dry_run:
        logger.info(
            "[DRY-RUN] Would update %d index entries and re-upload index.json",
            updated,
        )
        return updated

    # Write updated index locally
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    logger.info("Local index.json updated with %d new Drive entries.", updated)

    # Re-upload index.json to Drive (overwrite if exists)
    existing_data_files = list_files_in_folder(service, data_folder_id)
    if "index.json" in existing_data_files:
        # Update the existing file in place
        file_id = existing_data_files["index.json"]["id"]
        media = MediaFileUpload(
            str(INDEX_FILE), mimetype="application/json", resumable=True
        )
        service.files().update(
            fileId=file_id, media_body=media, fields="id", supportsAllDrives=True
        ).execute()
        logger.info("Re-uploaded updated index.json (id=%s)", file_id)
    else:
        # Upload fresh (should not happen since step 1 uploaded it)
        result = upload_file(
            service, INDEX_FILE, data_folder_id, mime_type="application/json"
        )
        logger.info("Uploaded updated index.json (id=%s)", result["id"])

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Migrate local memoires-tech-index data to Google Drive."
    )
    parser.add_argument(
        "--credentials",
        default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        help=(
            "Path to Google service-account JSON key file. "
            "Defaults to GOOGLE_APPLICATION_CREDENTIALS env var."
        ),
    )
    parser.add_argument(
        "--data-folder-id",
        default=os.getenv("GDRIVE_DATA_FOLDER_ID", ""),
        help=(
            "Google Drive folder ID for data (JSON + images). "
            "Defaults to GDRIVE_DATA_FOLDER_ID env var."
        ),
    )
    parser.add_argument(
        "--docs-folder-id",
        default=os.getenv("GDRIVE_DOCS_FOLDER_ID", ""),
        help=(
            "Google Drive folder ID for source documents (.docx/.pdf). "
            "Defaults to GDRIVE_DOCS_FOLDER_ID env var."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually doing it.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )

    args = parser.parse_args()

    # ---- Logging setup ----
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # ---- Validate required args ----
    if not args.credentials:
        parser.error(
            "Service-account credentials are required. "
            "Use --credentials or set GOOGLE_APPLICATION_CREDENTIALS."
        )
    if not Path(args.credentials).exists():
        parser.error(f"Credentials file not found: {args.credentials}")

    if not args.data_folder_id:
        parser.error(
            "Data folder ID is required. "
            "Use --data-folder-id or set GDRIVE_DATA_FOLDER_ID."
        )
    if not args.docs_folder_id:
        parser.error(
            "Documents folder ID is required. "
            "Use --docs-folder-id or set GDRIVE_DOCS_FOLDER_ID."
        )

    dry_run = args.dry_run
    if dry_run:
        logger.info("=== DRY RUN MODE - no files will be uploaded ===")

    # ---- Authenticate ----
    logger.info("Authenticating with Google Drive API ...")
    service = get_drive_service(args.credentials)
    logger.info("Authenticated successfully.")

    # ---- Step 1: JSON data files ----
    logger.info("=" * 60)
    logger.info("STEP 1/5: Upload JSON data files")
    logger.info("=" * 60)
    upload_json_files(service, args.data_folder_id, dry_run)

    # ---- Step 2: Images ----
    logger.info("=" * 60)
    logger.info("STEP 2/5: Upload images")
    logger.info("=" * 60)
    upload_images(service, args.data_folder_id, dry_run)

    # ---- Step 3: Documents ----
    logger.info("=" * 60)
    logger.info("STEP 3/5: Upload documents from LOCAL_DOCS_PATH")
    logger.info("=" * 60)
    drive_docs = upload_documents(service, args.docs_folder_id, dry_run)

    # ---- Step 4: Update index ----
    logger.info("=" * 60)
    logger.info("STEP 4/5: Update index with Drive file IDs")
    logger.info("=" * 60)
    updated = update_index_with_drive_ids(
        service, args.data_folder_id, drive_docs, dry_run
    )

    # ---- Step 5 (re-upload) is handled inside update_index_with_drive_ids ----
    logger.info("=" * 60)
    logger.info("STEP 5/5: Re-upload updated index (done in step 4)")
    logger.info("=" * 60)

    # ---- Summary ----
    logger.info("=" * 60)
    logger.info("Migration complete%s.", " (DRY RUN)" if dry_run else "")
    logger.info("  Index entries updated with Drive metadata: %d", updated)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
