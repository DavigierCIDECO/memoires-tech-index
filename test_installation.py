"""Script de test pour vérifier l'installation."""
import sys
from pathlib import Path


def test_python_version():
    """Vérifie la version de Python."""
    print("1. Vérification de la version Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   [OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   [ERREUR] Python {version.major}.{version.minor} (3.8+ requis)")
        return False


def test_dependencies():
    """Vérifie que les dépendances sont installées."""
    print("\n2. Vérification des dépendances...")
    dependencies = [
        "anthropic",
        "docx",
        "PyPDF2",
        "dotenv"
    ]

    all_ok = True
    for dep in dependencies:
        try:
            if dep == "docx":
                __import__("docx")
            elif dep == "dotenv":
                __import__("dotenv")
            else:
                __import__(dep)
            print(f"   [OK] {dep}")
        except ImportError:
            print(f"   [ERREUR] {dep} (manquant)")
            all_ok = False

    return all_ok


def test_config():
    """Vérifie la configuration."""
    print("\n3. Vérification de la configuration...")

    env_file = Path(".env")
    if not env_file.exists():
        print("   [ERREUR] Fichier .env manquant")
        print("      -> Créez le fichier .env depuis .env.example")
        return False

    print("   [OK] Fichier .env existe")

    # Charger la config
    try:
        import config

        if not config.ANTHROPIC_API_KEY:
            print("   [ERREUR] ANTHROPIC_API_KEY non définie dans .env")
            return False

        print("   [OK] ANTHROPIC_API_KEY configurée")

        if not config.LOCAL_DOCS_PATH:
            print("   [INFO] LOCAL_DOCS_PATH non configuré (optionnel)")
        else:
            print(f"   [OK] LOCAL_DOCS_PATH: {config.LOCAL_DOCS_PATH}")

        return True

    except Exception as e:
        print(f"   [ERREUR] Erreur de chargement: {e}")
        return False


def test_data_directory():
    """Vérifie que le dossier data existe."""
    print("\n4. Vérification du dossier data...")

    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir()
        print("   [OK] Dossier data créé")
    else:
        print("   [OK] Dossier data existe")

    return True


def main():
    """Exécute tous les tests."""
    print("="*60)
    print("TEST D'INSTALLATION - Système d'Indexation de Mémoires")
    print("="*60)

    results = []

    results.append(test_python_version())
    results.append(test_dependencies())
    results.append(test_config())
    results.append(test_data_directory())

    print("\n" + "="*60)
    if all(results):
        print("[OK] INSTALLATION OK - Vous pouvez commencer à utiliser le système")
        print("\nProchaines étapes :")
        print("  1. python indexer.py <dossier>  # Indexer vos documents")
        print("  2. python search.py --stats     # Voir les statistiques")
        print("  3. python search.py <recherche> # Rechercher")
    else:
        print("[ERREUR] INSTALLATION INCOMPLÈTE - Corrigez les erreurs ci-dessus")
        print("\nAide :")
        print("  - Installez les dépendances : pip install -r requirements.txt")
        print("  - Créez le fichier .env depuis .env.example")
        print("  - Consultez le README.md pour plus de détails")
    print("="*60)

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
