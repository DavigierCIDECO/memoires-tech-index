"""Configuration du système d'indexation des mémoires techniques."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


def _get_secret(key: str, default: str = "") -> str:
    """Récupère un secret depuis st.secrets (Streamlit Cloud) ou os.getenv."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


# Clé API Anthropic
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")

# Mode de stockage : "local" ou "gdrive"
STORAGE_MODE = _get_secret("STORAGE_MODE", "local")

# Chemins
LOCAL_DOCS_PATH = _get_secret("LOCAL_DOCS_PATH", "")
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
INDEX_FILE = DATA_DIR / "index.json"

# Google Drive
GDRIVE_DATA_FOLDER_ID = _get_secret("GDRIVE_DATA_FOLDER_ID", "")
GDRIVE_DOCS_FOLDER_ID = _get_secret("GDRIVE_DOCS_FOLDER_ID", "")

# Mot de passe admin
ADMIN_PASSWORD = _get_secret("ADMIN_PASSWORD", "")

# Extensions de fichiers supportées
SUPPORTED_EXTENSIONS = [".docx", ".pdf", ".doc", ".docm"]

# Paramètres de résumé
SUMMARY_MAX_TOKENS = 1500  # Augmenté pour capturer tous les champs enrichis (ILLUSTR + SECTIONS)
SUMMARY_MODEL = "claude-3-5-haiku-20241022"  # Modèle rapide et économique pour les résumés

# Paramètres pour analyse différentielle
SIMILARITY_THRESHOLD = 10.0  # Score minimum pour détecter une similarité de base
DIFFERENTIAL_ANALYSIS_THRESHOLD = 20.0  # Score minimum pour analyse différentielle (documents vraiment similaires)
MAX_DIFFERENTIAL_COMPARISONS = 5  # Max documents pour analyse différentielle

# Paramètres de pondération temporelle
TEMPORAL_WEIGHTING_ENABLED = True  # Activer/désactiver la pondération temporelle
TEMPORAL_BONUS_RECENT = 0.15  # Bonus +15% pour MTs < 3 mois
TEMPORAL_BONUS_MEDIUM = 0.10  # Bonus +10% pour MTs 3-6 mois
TEMPORAL_BONUS_OLD = 0.05     # Bonus +5% pour MTs 6-12 mois
TEMPORAL_CUTOFF_DATE = "2026-01-04"  # Documents indexés avant cette date = pas de bonus


def get_storage():
    """Factory qui retourne le backend de stockage approprié.

    Returns:
        Instance de StorageBackend (LocalStorage ou GDriveStorage)
    """
    if STORAGE_MODE == "gdrive":
        from storage_gdrive import GDriveStorage
        return GDriveStorage()
    else:
        from storage_local import LocalStorage
        return LocalStorage()
