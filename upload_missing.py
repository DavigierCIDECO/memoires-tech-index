"""Upload des documents locaux manquants vers Google Drive et mise à jour de l'index."""
import os
import sys
from pathlib import Path

# Forcer les variables d'environnement
os.environ["STORAGE_MODE"] = "gdrive"
os.environ["GDRIVE_DOCS_FOLDER_ID"] = "13yJ3buMzf03ZzLvV4aVqvVZHfyBxoCHM"
os.environ["GDRIVE_DATA_FOLDER_ID"] = "1iAd50S-eZU1YE5gn7PYkaKf9N9jeQ28b"
os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = str(
    Path(__file__).parent.parent / "memoires-tech-index-db8b0704b979.json"
)

import config
from googleapiclient.http import MediaFileUpload

storage = config.get_storage()
service = storage._get_service()
docs_folder_id = config.GDRIVE_DOCS_FOLDER_ID

# Charger l'index
index = storage.read_json("index")
docs = index.get("documents", [])
no_gdrive = [d for d in docs if not d.get("gdrive_file_id")]

print(f"Documents sans gdrive_file_id: {len(no_gdrive)}")

uploaded = 0
skipped = 0
errors = 0

for i, doc in enumerate(no_gdrive):
    fp = doc.get("file_path", "")
    if not fp or not Path(fp).exists():
        skipped += 1
        continue

    filename = doc["filename"]
    try:
        file_metadata = {
            "name": filename,
            "parents": [docs_folder_id],
        }
        media = MediaFileUpload(fp, resumable=False)
        result = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )

        file_id = result["id"]
        doc["gdrive_file_id"] = file_id
        doc["gdrive_link"] = f"https://drive.google.com/file/d/{file_id}/view"
        uploaded += 1
        print(f"  [{uploaded}] {filename}")

    except Exception as e:
        errors += 1
        print(f"  ERREUR {filename}: {e}", file=sys.stderr)

    # Sauvegarde intermédiaire toutes les 20 uploads
    if uploaded > 0 and uploaded % 20 == 0:
        storage.write_json("index", index)
        print(f"  -- Sauvegarde intermédiaire ({uploaded} uploads) --")

# Sauvegarde finale
storage.write_json("index", index)
print(f"\nTerminé: {uploaded} uploadés, {skipped} ignorés, {errors} erreurs")
