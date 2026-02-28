"""Interface Streamlit pour enrichir manuellement les illustrations des documents.

Permet d'uploader des captures d'écran et d'ajouter des métadonnées détaillées
pour chaque illustration importante.
"""
import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import hashlib
import shutil
from PIL import ImageGrab
import io

import config

# Configuration de la page
st.set_page_config(
    page_title="Enrichissement Manuel - Illustrations",
    page_icon="🖼️",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .illustration-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .category-badge {
        background-color: #1f77b4;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def load_index():
    """Charge l'index."""
    if not config.INDEX_FILE.exists():
        st.error(f"Index introuvable: {config.INDEX_FILE}")
        return None

    with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index):
    """Sauvegarde l'index avec flush pour garantir l'écriture complète."""
    try:
        index["last_updated"] = datetime.now().isoformat()

        # Écrire dans un fichier temporaire d'abord
        temp_file = config.INDEX_FILE.with_suffix('.tmp')
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            f.flush()  # Forcer l'écriture dans le buffer du système
            import os
            os.fsync(f.fileno())  # Forcer l'écriture physique sur disque

        # Remplacer l'ancien fichier par le nouveau (opération atomique)
        import shutil
        shutil.move(str(temp_file), str(config.INDEX_FILE))

        print(f"[DEBUG] Index saved successfully at {datetime.now().isoformat()}")
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la sauvegarde: {e}")
        import traceback
        print(f"[ERROR] {traceback.format_exc()}")
        return False


def get_image_dir(doc_hash):
    """Obtient le répertoire d'images pour un document."""
    img_dir = config.DATA_DIR / "images" / doc_hash
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


def save_uploaded_image(uploaded_file_or_image, doc_hash, illust_index):
    """Sauvegarde une image uploadée ou du presse-papiers.

    Args:
        uploaded_file_or_image: Fichier uploadé par Streamlit OU Image PIL
        doc_hash: Hash du document
        illust_index: Index de l'illustration

    Returns:
        Chemin relatif de l'image sauvegardée
    """
    img_dir = get_image_dir(doc_hash)

    # Déterminer si c'est un fichier uploadé ou une image PIL
    from PIL import Image

    if isinstance(uploaded_file_or_image, Image.Image):
        # Image PIL du presse-papiers
        file_ext = '.png'
        filename = f"illust_{illust_index:03d}{file_ext}"
        file_path = img_dir / filename

        # Sauvegarder directement l'image PIL
        uploaded_file_or_image.save(file_path, format='PNG')
    else:
        # Fichier uploadé
        file_ext = Path(uploaded_file_or_image.name).suffix.lower()
        if file_ext not in ['.png', '.jpg', '.jpeg']:
            file_ext = '.png'

        filename = f"illust_{illust_index:03d}{file_ext}"
        file_path = img_dir / filename

        # Sauvegarder depuis le buffer
        with open(file_path, "wb") as f:
            f.write(uploaded_file_or_image.getbuffer())

    # Retourner le chemin relatif
    return str(file_path.relative_to(config.DATA_DIR.parent))


def edit_illustration_inline(doc, index_data, idx, illust):
    """Formulaire d'édition inline pour une illustration.

    Args:
        doc: Document contenant l'illustration
        index_data: Index complet
        idx: Index de l'illustration (1-based)
        illust: Dictionnaire de l'illustration
    """
    # Utiliser un compteur de version pour forcer le rechargement après sauvegarde
    # Cela crée un formulaire avec un ID différent, donc de nouveaux widgets
    version = st.session_state.get(f"form_version_{idx}", 0)

    with st.form(f"edit_form_{idx}_v{version}"):
        # Debug: afficher les valeurs actuelles chargées
        with st.expander("🔍 Debug: Valeurs chargées depuis l'index", expanded=False):
            st.caption(f"Version du formulaire: {version} (incrémenté à chaque sauvegarde)")
            st.json({
                "category": illust.get("category", "N/A"),
                "type": illust.get("type", "N/A"),
                "description": illust.get("description", "N/A")[:100] + "..." if len(illust.get("description", "")) > 100 else illust.get("description", "N/A"),
                "keywords": illust.get("technical_keywords", []),
                "updated_at": illust.get("updated_at", "Jamais")
            })
            st.caption("⚠️ Si les champs ne correspondent pas à ces valeurs, rechargez la page (F5)")

        # Catégorie
        predefined_categories = [
            "Investigation",
            "Analyse",
            "Modélisation",
            "Préconisation",
            "Méthodologie",
            "Références",
            "Autre..."
        ]

        current_cat = illust.get("category", "")

        # Déterminer l'index par défaut
        if current_cat in predefined_categories:
            category_idx = predefined_categories.index(current_cat)
        elif current_cat:
            # Catégorie personnalisée existante → sélectionner "Autre..."
            category_idx = len(predefined_categories) - 1
        else:
            category_idx = 0

        category_choice = st.selectbox("Catégorie :", predefined_categories, index=category_idx)

        # Champ personnalisé seulement si "Autre..." est sélectionné
        custom_category = ""
        if category_choice == "Autre...":
            # Pré-remplir avec la catégorie actuelle si elle n'est pas dans la liste
            default_custom = current_cat if current_cat not in predefined_categories else ""
            custom_category = st.text_input("Catégorie personnalisée :", value=default_custom)

        # Déterminer la catégorie finale
        if category_choice == "Autre...":
            category = custom_category
        else:
            category = category_choice

        # Type
        current_type = illust.get("type", "schéma")
        type_options = ["Schéma", "Photo", "Graphique", "Plan", "Diagramme", "Tableau", "Autre"]
        type_idx = type_options.index(current_type.capitalize()) if current_type.capitalize() in type_options else 0
        illustration_type = st.selectbox("Type :", type_options, index=type_idx)

        # Description
        description = st.text_area(
            "Description détaillée :",
            value=illust.get("description", ""),
            height=100
        )

        # Mots-clés
        current_keywords = illust.get("technical_keywords", [])
        keywords_str = ", ".join(current_keywords) if current_keywords else ""
        keywords_input = st.text_input(
            "Mots-clés techniques (virgules) :",
            value=keywords_str
        )

        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        # Remplacement d'image (optionnel)
        st.markdown("---")
        st.markdown("### 🖼️ Remplacer l'image (optionnel)")

        # Afficher l'image actuelle si elle existe
        current_img_path = illust.get("image_path")
        if current_img_path:
            full_img_path = Path(config.DATA_DIR.parent) / current_img_path
            if full_img_path.exists():
                st.image(str(full_img_path), caption="Image actuelle", width=200)
            else:
                st.warning("⚠️ Image actuelle introuvable")

        # Upload nouvelle image
        new_image = st.file_uploader(
            "Choisir une nouvelle image",
            type=['png', 'jpg', 'jpeg'],
            help="L'image actuelle sera remplacée si vous uploadez un nouveau fichier"
        )

        # Bouton sauvegarder
        if st.form_submit_button("💾 Sauvegarder", type="primary", width='stretch'):
            if not category:
                st.error("⚠️ Catégorie requise")
            elif not description:
                st.error("⚠️ Description requise")
            elif not keywords:
                st.error("⚠️ Au moins un mot-clé requis")
            else:
                # Mettre à jour les métadonnées
                illust["category"] = category
                illust["type"] = illustration_type.lower()
                illust["description"] = description
                illust["technical_keywords"] = keywords
                illust["updated_at"] = datetime.now().isoformat()

                # Sauvegarder la nouvelle image si uploadée
                if new_image is not None:
                    new_image_path = save_uploaded_image(
                        new_image,
                        doc["file_hash"],
                        idx
                    )
                    illust["image_path"] = new_image_path
                    illust["image_updated_at"] = datetime.now().isoformat()

                # Sauvegarder l'index
                if save_index(index_data):
                    # Incrémenter le compteur de version pour créer un nouveau formulaire
                    # avec de nouveaux widgets au prochain rendu
                    current_version = st.session_state.get(f"form_version_{idx}", 0)
                    st.session_state[f"form_version_{idx}"] = current_version + 1

                    # Marquer le succès dans session_state pour persister après rerun
                    st.session_state[f"save_success_{idx}"] = True
                    st.rerun()
                else:
                    st.error("❌ Échec de la sauvegarde")


def display_existing_illustrations(doc, index):
    """Affiche les illustrations existantes d'un document."""
    illustrations = doc.get("special_illustrations", [])

    if not illustrations:
        st.info("Aucune illustration enrichie pour ce document")
        return

    st.markdown(f"### 🖼️ Illustrations existantes ({len(illustrations)})")

    for idx, illust in enumerate(illustrations, 1):
        with st.container():
            col1, col2, col3 = st.columns([0.3, 0.5, 0.2])

            with col1:
                # Afficher l'image si disponible
                if illust.get("image_path"):
                    img_path = Path(config.DATA_DIR.parent) / illust["image_path"]
                    if img_path.exists():
                        st.image(str(img_path), width=150)  # Miniature dans la liste
                    else:
                        st.warning("Image introuvable")
                else:
                    st.info("Pas d'image")

            with col2:
                cat = illust.get("category", "N/A")
                st.markdown(f"**[{idx}] [{cat.upper()}] {illust.get('type', 'Illustration')}**")
                st.caption(illust.get("description", "Pas de description"))

                if illust.get("technical_keywords"):
                    st.markdown(f"🔑 {', '.join(illust['technical_keywords'])}")

                # Afficher la date de dernière modification si elle existe
                if illust.get("updated_at"):
                    from datetime import datetime
                    try:
                        updated_dt = datetime.fromisoformat(illust["updated_at"])
                        st.caption(f"🕐 Modifiée: {updated_dt.strftime('%d/%m/%Y %H:%M')}")
                    except:
                        pass

            with col3:
                # Bouton de suppression
                if st.button("🗑️ Supprimer", key=f"del_{idx}", width='stretch'):
                    st.session_state[f"delete_illust_{idx}"] = True
                    st.rerun()

            # Afficher message de succès si sauvegarde récente
            if st.session_state.get(f"save_success_{idx}"):
                st.success(f"✅ Illustration #{idx} mise à jour avec succès !")
                # Nettoyer le flag après affichage
                del st.session_state[f"save_success_{idx}"]

            # Expander d'édition inline
            with st.expander(f"✏️ Éditer l'illustration #{idx}", expanded=False):
                edit_illustration_inline(doc, index, idx, illust)


def main():
    """Point d'entrée principal."""

    st.markdown('<p class="main-title">🖼️ Enrichissement Manuel des Illustrations</p>',
                unsafe_allow_html=True)

    # Charger l'index
    index = load_index()
    if not index:
        return

    # Statistiques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Documents", len(index.get("documents", [])))
    with col2:
        enriched_count = sum(1 for doc in index.get("documents", [])
                           if doc.get("special_illustrations"))
        st.metric("🖼️ Avec illustrations", enriched_count)
    with col3:
        manual_count = sum(1 for doc in index.get("documents", [])
                         for illust in doc.get("special_illustrations", [])
                         if illust.get("image_path"))
        st.metric("📸 Avec captures", manual_count)

    st.markdown("---")

    # Sélection du document
    st.markdown("## 1️⃣ Sélectionner un document")

    # Trier les documents par nom
    documents = sorted(index.get("documents", []), key=lambda d: d["filename"])

    # Champ de recherche pour filtrer
    search_term = st.text_input(
        "🔍 Rechercher un document :",
        placeholder="Tapez pour filtrer la liste...",
        help="Recherche dans les noms de fichiers"
    )

    # Filtrer les documents selon la recherche
    if search_term:
        filtered_docs = [
            doc for doc in documents
            if search_term.lower() in doc["filename"].lower()
        ]
    else:
        filtered_docs = documents

    if not filtered_docs:
        st.warning(f"Aucun document trouvé avec '{search_term}'")
        return

    # Afficher le nombre de résultats si filtré
    if search_term:
        st.caption(f"📄 {len(filtered_docs)} document(s) trouvé(s)")

    doc_options = [f"{doc['filename']}" for doc in filtered_docs]
    selected_doc_name = st.selectbox(
        "Choisir un mémoire technique :",
        options=doc_options,
        help="Sélectionnez le document à enrichir"
    )

    if not selected_doc_name:
        return

    # Trouver le document sélectionné
    selected_doc = next((doc for doc in filtered_docs if doc["filename"] == selected_doc_name), None)

    if not selected_doc:
        st.error("Document introuvable")
        return

    # Afficher les infos du document
    with st.expander("📄 Informations du document", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Fichier:** {selected_doc['filename']}")
            st.write(f"**Résumé:** {selected_doc.get('summary', 'N/A')[:200]}...")
        with col2:
            st.write(f"**Mots-clés:** {selected_doc.get('keywords', 'N/A')}")
            st.write(f"**Thèmes:** {selected_doc.get('themes', 'N/A')}")

    st.markdown("---")

    # Afficher les illustrations existantes
    st.markdown("## 2️⃣ Illustrations existantes")
    display_existing_illustrations(selected_doc, index)

    # Gérer les suppressions
    for idx in range(1, len(selected_doc.get("special_illustrations", [])) + 1):
        if st.session_state.get(f"delete_illust_{idx}"):
            selected_doc["special_illustrations"].pop(idx - 1)
            save_index(index)
            del st.session_state[f"delete_illust_{idx}"]
            st.success(f"Illustration #{idx} supprimée")
            st.rerun()

    st.markdown("---")

    # Formulaire d'ajout d'illustration
    st.markdown("## 3️⃣ Ajouter une nouvelle illustration")

    # Section presse-papiers AVANT le formulaire
    st.markdown("### 📋 Option 1: Coller depuis le presse-papiers")

    col_paste1, col_paste2 = st.columns([0.3, 0.7])

    with col_paste1:
        if st.button("📋 Coller depuis le presse-papiers", type="secondary", width='stretch'):
            try:
                img = ImageGrab.grabclipboard()
                if img:
                    st.session_state.clipboard_image = img
                    st.success("✅ Image récupérée !")
                    st.rerun()
                else:
                    st.error("❌ Aucune image dans le presse-papiers")
            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

    with col_paste2:
        st.info("💡 **Utilisation :** IMPR ÉCRAN → Sélectionnez la zone → Ctrl+C → Cliquez sur 'Coller'")

    # Afficher l'image du presse-papiers si disponible
    if 'clipboard_image' not in st.session_state:
        st.session_state.clipboard_image = None

    if st.session_state.clipboard_image:
        col_img1, col_img2 = st.columns([0.5, 0.5])
        with col_img1:
            st.image(st.session_state.clipboard_image, width=300)  # Preview taille réduite
        with col_img2:
            if st.button("🗑️ Effacer l'image du presse-papiers"):
                st.session_state.clipboard_image = None
                st.rerun()

    st.markdown("---")

    # Formulaire avec upload de fichier OU utilisation de l'image du presse-papiers
    with st.form("add_illustration"):
        col1, col2 = st.columns([0.4, 0.6])

        with col1:
            st.markdown("### 📸 Option 2: Uploader un fichier")

            uploaded_file = st.file_uploader(
                "Uploader un fichier :",
                type=['png', 'jpg', 'jpeg'],
                help="Drag & drop ou sélection de fichier (alternative au presse-papiers)"
            )

            if uploaded_file:
                st.image(uploaded_file, width=300)  # Preview taille réduite

        with col2:
            st.markdown("### 📝 Métadonnées")

            # Catégorie avec options prédéfinies + personnalisée
            predefined_categories = [
                "Investigation",
                "Analyse",
                "Modélisation",
                "Préconisation",
                "Méthodologie",
                "Références",
                "Autre..."
            ]

            category_choice = st.selectbox(
                "Catégorie :",
                options=predefined_categories,
                help="Sélectionnez la catégorie de l'illustration"
            )

            if category_choice == "Autre...":
                category = st.text_input(
                    "Catégorie personnalisée :",
                    placeholder="Ex: Planification, Organisation, Sécurité..."
                )
            else:
                category = category_choice

            # Type
            illustration_type = st.selectbox(
                "Type :",
                options=["Schéma", "Photo", "Graphique", "Plan", "Diagramme", "Tableau", "Autre"],
                help="Type d'illustration"
            )

            # Description
            description = st.text_area(
                "Description détaillée :",
                height=100,
                placeholder="Décrivez précisément ce que montre l'illustration...",
                help="Soyez précis : équipements, techniques, résultats, configurations..."
            )

            # Mots-clés techniques
            keywords_input = st.text_input(
                "Mots-clés techniques (séparés par des virgules) :",
                placeholder="plats carbone, renforcement, collage époxy...",
                help="3-8 mots-clés techniques pour faciliter la recherche"
            )

            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        # Bouton de soumission
        submitted = st.form_submit_button("➕ Ajouter l'illustration", type="primary", width='stretch')

        if submitted:
            # Récupérer l'image du presse-papiers depuis session_state
            clipboard_image = st.session_state.get('clipboard_image', None)

            # Validation
            errors = []
            if not uploaded_file and not clipboard_image:
                errors.append("⚠️ Veuillez fournir une capture d'écran (fichier ou presse-papiers)")
            if not category:
                errors.append("⚠️ Veuillez sélectionner ou saisir une catégorie")
            if not description:
                errors.append("⚠️ Veuillez saisir une description")
            if not keywords:
                errors.append("⚠️ Veuillez ajouter au moins un mot-clé technique")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Préparer l'illustration
                if "special_illustrations" not in selected_doc:
                    selected_doc["special_illustrations"] = []

                # PROTECTION ANTI-BUG: Recharger l'index depuis le disque pour avoir
                # le nombre d'illustrations le plus à jour (évite les bugs de cache)
                fresh_index = load_index()
                if fresh_index:
                    fresh_doc = next((d for d in fresh_index["documents"]
                                     if d["file_hash"] == selected_doc["file_hash"]), None)
                    if fresh_doc:
                        current_count = len(fresh_doc.get("special_illustrations", []))
                        illust_index = current_count + 1
                        # Mettre à jour selected_doc avec les illustrations actuelles
                        selected_doc["special_illustrations"] = fresh_doc.get("special_illustrations", [])
                    else:
                        illust_index = len(selected_doc["special_illustrations"]) + 1
                else:
                    illust_index = len(selected_doc["special_illustrations"]) + 1

                # Log pour debug
                print(f"[DEBUG] Creating illustration #{illust_index} for {selected_doc['filename']}")

                # Sauvegarder l'image (fichier ou presse-papiers)
                image_to_save = uploaded_file if uploaded_file else clipboard_image
                image_path = save_uploaded_image(
                    image_to_save,
                    selected_doc["file_hash"],
                    illust_index
                )

                # Vérifier que le fichier a bien été créé
                full_img_path = Path(config.DATA_DIR.parent) / image_path
                if not full_img_path.exists():
                    st.error(f"❌ ERREUR CRITIQUE: L'image n'a pas été sauvegardée correctement!")
                    st.stop()

                # Créer l'entrée d'illustration
                new_illustration = {
                    "category": category,
                    "type": illustration_type.lower(),
                    "description": description,
                    "technical_keywords": keywords,
                    "image_path": image_path,
                    "detection_method": "enrichissement manuel",
                    "confidence": "high",
                    "context": f"Ajouté manuellement le {datetime.now().strftime('%Y-%m-%d')}",
                    "added_at": datetime.now().isoformat()
                }

                # Ajouter à la liste
                selected_doc["special_illustrations"].append(new_illustration)
                selected_doc["manually_enriched_at"] = datetime.now().isoformat()

                # Sauvegarder l'index
                save_index(index)

                # Nettoyer le presse-papiers de la session
                if 'clipboard_image' in st.session_state:
                    st.session_state.clipboard_image = None

                st.success(f"✅ Illustration ajoutée avec succès !")
                st.balloons()
                st.rerun()

    # Instructions
    st.markdown("---")
    with st.expander("ℹ️ Comment faire une bonne capture d'écran ?"):
        st.markdown("""
        **Conseils pour des captures efficaces :**

        1. **Outil de capture** : Utilisez `Windows + Shift + S` (Windows) ou `Cmd + Shift + 4` (Mac)

        2. **Cadrage** :
           - Capturez uniquement l'illustration (pas le texte autour)
           - Incluez les légendes/annotations si pertinentes
           - Assurez-vous que le texte est lisible

        3. **Qualité** :
           - Résolution suffisante (évitez de zoomer trop)
           - Contraste correct
           - Pas de reflets ou zones floues

        4. **Organisation** :
           - Nommez vos captures de façon claire (avant upload)
           - Ajoutez des descriptions précises
           - Utilisez des mots-clés pertinents

        5. **Catégories** :
           - **Investigation** : Photos terrain, équipements, protocoles
           - **Analyse** : Graphiques, courbes, résultats de mesures
           - **Modélisation** : Modèles numériques, calculs, simulations
           - **Préconisation** : Schémas de réparation, solutions techniques
           - **Références** : Exemples de projets passés, réalisations
        """)


if __name__ == "__main__":
    main()
