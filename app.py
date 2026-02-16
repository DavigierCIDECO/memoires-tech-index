"""Interface Streamlit pour la recherche de mémoires techniques similaires."""
import streamlit as st
import json
from pathlib import Path
from typing import List, Dict
import sys
from datetime import datetime
from io import BytesIO

from PIL import Image

# Ajouter le répertoire courant au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from find_similar import SimilarityFinder
from enrichment import EnrichmentManager
from learning import LearningSystem
from indexer import DocumentIndexer
from auth import require_user, get_current_user, is_admin, require_admin_password, show_user_badge
from models import (
    STATUS_INDEXED, STATUS_VALIDATED, STATUS_ENRICHED,
    validate_document, mark_enriched, get_status_counts, get_documents_by_status, migrate_document,
)
import config

# Configuration de la page
st.set_page_config(
    page_title="Recherche Mémoires Techniques",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .score-badge {
        background-color: #1f77b4;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
    }
    .info-section {
        margin-top: 0.5rem;
        padding: 0.5rem;
        background-color: white;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


def _get_storage():
    """Récupère le storage backend."""
    return config.get_storage()


def _load_index():
    """Charge l'index via le storage backend."""
    storage = _get_storage()
    data = storage.read_json("index")
    if data:
        return data
    return {"documents": [], "last_updated": None}


def _save_index(index):
    """Sauvegarde l'index via le storage backend."""
    storage = _get_storage()
    index["last_updated"] = datetime.now().isoformat()
    storage.write_json("index", index)


def _load_image_from_storage(image_path: str):
    """Charge une image via le storage backend.

    Returns:
        PIL Image ou None
    """
    storage = _get_storage()
    data = storage.read_image(image_path)
    if data:
        try:
            return Image.open(BytesIO(data))
        except Exception:
            return None
    # Fallback: essayer en tant que chemin local direct
    local_path = Path(config.DATA_DIR.parent) / image_path
    if local_path.exists():
        try:
            return Image.open(local_path)
        except Exception:
            return None
    return None


def score_illustration_relevance(illust: Dict, query: str) -> float:
    """Score la pertinence d'une illustration par rapport à la requête."""
    score = 0.0
    query_words = set(query.lower().split())

    if illust.get("technical_keywords"):
        tech_keywords_set = set()
        for kw in illust["technical_keywords"]:
            for part in kw.split(";"):
                for subpart in part.split(","):
                    cleaned = subpart.strip().lower()
                    if cleaned:
                        for word in cleaned.split():
                            tech_keywords_set.add(word)
        tech_matching = query_words & tech_keywords_set
        score += len(tech_matching) * 10.0

    if illust.get("description"):
        desc_words = set(illust["description"].lower().split())
        desc_matching = query_words & desc_words
        score += len(desc_matching) * 3.0

    if illust.get("category"):
        cat_words = set(illust["category"].lower().split())
        cat_matching = query_words & cat_words
        score += len(cat_matching) * 2.0

    return score


def _display_document_link(doc: Dict):
    """Affiche un lien vers le document (chemin local ou lien Drive)."""
    if doc.get("gdrive_link"):
        st.markdown(f"[Ouvrir dans Google Drive]({doc['gdrive_link']})")
    elif doc.get("file_path"):
        st.caption(f"📁 {doc['file_path']}")


def display_result(doc: Dict, rank: int, query: str = ""):
    """Affiche un résultat de recherche de manière élégante."""
    with st.container():
        col1, col2 = st.columns([0.05, 0.95])

        with col1:
            st.markdown(f"### {rank}")

        with col2:
            st.markdown(f"""
            <div class="result-card">
                <h3>
                    {doc['filename']}
                    <span class="score-badge">Score: {doc['similarity_score']:.1f}</span>
                </h3>
            </div>
            """, unsafe_allow_html=True)

            if doc.get("common_keywords") or doc.get("common_themes"):
                col_k, col_t = st.columns(2)
                with col_k:
                    if doc.get("common_keywords"):
                        st.markdown("**🔑 Mots-clés communs:**")
                        st.write(", ".join(doc["common_keywords"]))
                with col_t:
                    if doc.get("common_themes"):
                        st.markdown("**🏷️ Thèmes communs:**")
                        st.write(", ".join(doc["common_themes"]))

            # Lien vers le document
            _display_document_link(doc)

            # Aperçu des illustrations exceptionnelles
            if doc.get("special_illustrations"):
                illustrations = doc["special_illustrations"]
                if illustrations:
                    st.markdown(f"**🖼️ Illustrations exceptionnelles:** {len(illustrations)}")

                    illustrations_with_images = [ill for ill in illustrations if ill.get("image_path")]
                    if illustrations_with_images:
                        if query:
                            scored_illustrations = [(ill, score_illustration_relevance(ill, query))
                                                  for ill in illustrations_with_images]
                            scored_illustrations.sort(key=lambda x: x[1], reverse=True)
                            sorted_illustrations = [ill for ill, score in scored_illustrations]
                        else:
                            sorted_illustrations = illustrations_with_images

                        img_cols = st.columns(min(3, len(sorted_illustrations)))
                        for idx, illust in enumerate(sorted_illustrations[:3]):
                            with img_cols[idx]:
                                img = _load_image_from_storage(illust["image_path"])
                                if img:
                                    st.image(img, width=200)
                                    cat = illust.get('category', 'N/A')
                                    st.caption(f"[{cat}] {illust.get('type', 'Illustration')}")

                        if len(illustrations_with_images) > 3:
                            st.caption(f"+ {len(illustrations_with_images) - 3} autre(s) image(s)")

                    first_illust = illustrations[0]
                    conf_emoji = {
                        'high': '🟢', 'medium': '🟡', 'low': '🟠'
                    }.get(first_illust.get('confidence', 'medium'), '⚪')

                    preview_text = f"{conf_emoji} {first_illust.get('type', 'Illustration')}"
                    if first_illust.get('description'):
                        desc = first_illust['description']
                        if len(desc) > 80:
                            desc = desc[:80] + "..."
                        preview_text += f": {desc}"
                    st.caption(preview_text)

                    if len(illustrations) > 1:
                        st.caption(f"+ {len(illustrations) - 1} autre(s) illustration(s)")

            # Expander pour détails complets
            with st.expander("📋 Voir détails complets"):
                st.markdown("### Résumé")
                st.write(doc.get("summary", "Non disponible"))

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Mots-clés:**")
                    st.write(doc.get("keywords", "Non disponible"))
                with col2:
                    st.markdown("**Thèmes:**")
                    st.write(doc.get("themes", "Non disponible"))

                if doc.get("characteristics"):
                    st.markdown("### 📋 Caractéristiques")
                    chars = doc["characteristics"]
                    col1, col2 = st.columns(2)
                    with col1:
                        if chars.get("materials"):
                            st.markdown(f"**Matériaux:** {', '.join(chars['materials'])}")
                        if chars.get("focus_areas"):
                            st.markdown(f"**Domaines:** {', '.join(chars['focus_areas'])}")
                        if chars.get("methodology"):
                            st.markdown(f"**Méthodologie:** {', '.join(chars['methodology'])}")
                        if chars.get("equipment"):
                            st.markdown(f"**🔧 Équipements:** {', '.join(chars['equipment'])}")
                    with col2:
                        if chars.get("structure_types"):
                            st.markdown(f"**Types d'ouvrages:** {', '.join(chars['structure_types'])}")
                        if chars.get("geographical_scope"):
                            st.markdown(f"**Portée:** {chars['geographical_scope']}")
                        if chars.get("project_phase"):
                            st.markdown(f"**Phase:** {chars['project_phase']}")
                        if chars.get("team_members"):
                            st.markdown(f"**👥 Équipe:** {', '.join(chars['team_members'])}")
                        if chars.get("team_roles"):
                            st.markdown(f"**🎓 Compétences:** {', '.join(chars['team_roles'])}")

                    if chars.get("project_references"):
                        st.markdown(f"**🏆 Références projets:** {', '.join(chars['project_references'])}")
                    if chars.get("target_projects"):
                        st.markdown("**🎯 Projets cibles (appel d'offres):**")
                        for project in chars["target_projects"]:
                            st.write(f"• {project}")
                    if chars.get("special_sections"):
                        st.markdown("### 📑 Sections spéciales")
                        for section_name, section_summary in chars["special_sections"].items():
                            st.write(f"**• {section_name}:** {section_summary}")

                if doc.get("distinctions"):
                    st.markdown("### 🎯 Ce qui rend ce document unique")
                    dist = doc["distinctions"]
                    if dist.get("unique_aspects"):
                        st.info(dist["unique_aspects"])
                    if dist.get("differentiators"):
                        st.markdown("**🔍 Différenciateurs:**")
                        for diff in dist["differentiators"]:
                            st.write(f"• {diff}")
                    if dist.get("positioning"):
                        st.success(f"💡 **Positionnement:** {dist['positioning']}")

                # Illustrations complètes
                if doc.get("special_illustrations"):
                    illustrations = doc["special_illustrations"]
                    if illustrations:
                        st.markdown(f"### 🖼️ Illustrations exceptionnelles ({len(illustrations)})")
                        for idx, illust in enumerate(illustrations, 1):
                            with st.container():
                                cat = illust.get('category', '')
                                type_str = illust.get('type', 'Illustration')
                                if cat:
                                    cat_emoji = {
                                        'investigation': '🔍', 'analyse': '📊',
                                        'modélisation': '🧮', 'préconisation': '💡',
                                        'méthodologie': '📋'
                                    }.get(cat.lower(), '📄')
                                    st.markdown(f"**[{idx}] {cat_emoji} [{cat.upper()}] {type_str}**")
                                else:
                                    st.markdown(f"**[{idx}] {type_str}**")

                                if illust.get('image_path'):
                                    img = _load_image_from_storage(illust['image_path'])
                                    if img:
                                        st.image(img, width=400)
                                    else:
                                        st.warning(f"⚠️ Image introuvable: {illust['image_path']}")

                                col1, col2 = st.columns([0.7, 0.3])
                                with col1:
                                    if illust.get('description'):
                                        st.write(f"📝 {illust['description']}")
                                    if illust.get('technical_keywords'):
                                        keywords_str = ", ".join(illust['technical_keywords'])
                                        st.markdown(f"🔑 **Mots-clés:** {keywords_str}")
                                    if illust.get('context'):
                                        context = illust['context']
                                        if len(context) > 200:
                                            context = context[:200] + "..."
                                        st.caption(f"Contexte: {context}")
                                with col2:
                                    if illust.get('detection_method'):
                                        conf = illust.get('confidence', 'unknown')
                                        conf_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}.get(conf, '⚪')
                                        st.caption(f"{conf_emoji} Confiance: {conf}")
                                        st.caption(f"Méthode: {illust['detection_method']}")
                                st.markdown("---")

                # Métadonnées
                st.markdown("### 📊 Métadonnées")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Taille:** {doc.get('file_size', 0) / 1024 / 1024:.2f} MB")
                with col2:
                    st.write(f"**Longueur:** {doc.get('text_length', 0):,} caractères")
                with col3:
                    if doc.get("indexed_at"):
                        st.write(f"**Indexé:** {doc['indexed_at'][:10]}")

            st.markdown("---")


# ============================================================
# TAB: Recherche
# ============================================================
def tab_recherche(index):
    """Onglet de recherche par description texte."""
    query = st.text_area(
        "Décrivez votre projet ou le type de mémoire que vous recherchez:",
        height=100,
        placeholder="Exemple: Diagnostic de pont en béton armé avec instrumentation vibratoire et géoradar"
    )

    col1, col2 = st.columns([0.8, 0.2])
    with col2:
        search_btn = st.button("🔍 Rechercher", type="primary", use_container_width=True)

    if search_btn and query:
        with st.spinner("🔄 Recherche en cours..."):
            try:
                finder = SimilarityFinder()
                results = finder.find_similar(query, is_file=False, max_results=10)

                if results:
                    st.success(f"✅ {len(results)} document(s) similaire(s) trouvé(s)")
                    for i, doc in enumerate(results, 1):
                        display_result(doc, i, query)
                else:
                    st.warning("Aucun document similaire trouvé. Essayez avec une description différente.")
            except Exception as e:
                st.error(f"❌ Erreur lors de la recherche: {str(e)}")


# ============================================================
# TAB: Tableau de bord
# ============================================================
def tab_dashboard(index):
    """Onglet tableau de bord avec métriques et activité."""
    st.markdown("### 📊 Vue d'ensemble")

    counts = get_status_counts(index)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📚 Total documents", len(index.get("documents", [])))
    with col2:
        st.metric("🟡 Non validés", counts.get(STATUS_INDEXED, 0))
    with col3:
        st.metric("✅ Validés", counts.get(STATUS_VALIDATED, 0))
    with col4:
        st.metric("✏️ Enrichis", counts.get(STATUS_ENRICHED, 0))

    st.markdown("---")

    # Activité récente
    st.markdown("### 📝 Activité récente")
    docs = index.get("documents", [])
    recent_docs = sorted(docs, key=lambda d: d.get("indexed_at", ""), reverse=True)[:10]

    if recent_docs:
        for doc in recent_docs:
            status_emoji = {"indexe_non_valide": "🟡", "valide": "✅", "enrichi": "✏️"}.get(
                doc.get("status", STATUS_INDEXED), "⚪"
            )
            indexed_by = doc.get("indexed_by", "?")
            indexed_at = doc.get("indexed_at", "")[:16].replace("T", " ") if doc.get("indexed_at") else ""
            st.caption(f"{status_emoji} **{doc.get('filename', '?')}** — indexé par {indexed_by} le {indexed_at}")
    else:
        st.info("Aucune activité récente.")

    st.markdown("---")

    # Verrous actifs
    st.markdown("### 🔒 Verrous actifs")
    storage = _get_storage()
    lock_info = storage.get_lock_info("indexation")
    if lock_info:
        st.warning(f"🔒 Indexation verrouillée par **{lock_info.get('owner', '?')}** depuis {lock_info.get('acquired_at', '')[:16].replace('T', ' ')}")
    else:
        st.success("Aucun verrou actif")


# ============================================================
# TAB: Validation
# ============================================================
def tab_validation(index):
    """Onglet de validation des documents indexés."""
    st.markdown("### ✅ Valider les documents indexés")

    non_validated = get_documents_by_status(index, STATUS_INDEXED)

    if not non_validated:
        st.success("Tous les documents sont validés !")
        return

    st.info(f"🟡 {len(non_validated)} document(s) en attente de validation")

    # Trier par date d'indexation (plus récent en premier)
    non_validated.sort(key=lambda d: d.get("indexed_at", ""), reverse=True)

    for doc in non_validated:
        with st.expander(f"📄 {doc.get('filename', '?')} — indexé par {doc.get('indexed_by', '?')}"):
            # Résumé
            st.markdown("**Résumé:**")
            st.write(doc.get("summary", "N/A"))

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Mots-clés:** {doc.get('keywords', 'N/A')}")
            with col2:
                st.markdown(f"**Thèmes:** {doc.get('themes', 'N/A')}")

            # Lien vers le document
            _display_document_link(doc)

            st.markdown("---")

            col_v, col_ve, col_r = st.columns(3)
            with col_v:
                if st.button("✅ Valider", key=f"validate_{doc['file_hash']}", use_container_width=True):
                    validate_document(doc, get_current_user())
                    _save_index(index)
                    st.success(f"✅ {doc['filename']} validé")
                    st.rerun()
            with col_ve:
                if st.button("✏️ Valider et enrichir", key=f"val_enrich_{doc['file_hash']}", use_container_width=True):
                    validate_document(doc, get_current_user())
                    _save_index(index)
                    st.success(f"✅ Validé — passez à l'onglet Enrichissement")
                    st.rerun()
            with col_r:
                if st.button("🔄 Ré-indexer", key=f"reindex_{doc['file_hash']}", use_container_width=True):
                    st.session_state["reindex_hash"] = doc["file_hash"]
                    st.info("Lancez la ré-indexation depuis l'onglet Indexation")


# ============================================================
# TAB: Enrichissement
# ============================================================
def tab_enrichissement(index):
    """Onglet d'enrichissement manuel des documents."""
    st.markdown("### ✏️ Enrichir l'indexation d'un document")

    enrichment_mgr = EnrichmentManager()
    stats = enrichment_mgr.get_enrichment_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total enrichissements", stats["total_enrichments"])
    with col2:
        st.metric("Documents enrichis", stats["documents_enriched"])
    with col3:
        if stats["last_enrichment"]:
            st.metric("Dernier enrichissement", stats["last_enrichment"][:10])

    st.markdown("---")

    # Sélection du document
    st.markdown("**1️⃣ Sélectionnez un document à enrichir**")

    docs_list = []
    for doc in index.get("documents", []):
        label = doc.get("filename", "Inconnu")
        status_emoji = {"indexe_non_valide": "🟡", "valide": "✅", "enrichi": "✏️"}.get(
            doc.get("status", STATUS_INDEXED), "⚪"
        )
        if doc.get("manually_enriched"):
            label += " ✅"
        docs_list.append({"label": f"{status_emoji} {label}", "hash": doc.get("file_hash"), "doc": doc})

    if not docs_list:
        st.warning("Aucun document disponible pour enrichissement")
        return

    search_term = st.text_input(
        "🔍 Rechercher un document :",
        placeholder="Tapez pour filtrer la liste...",
        key="enrich_search_term"
    )

    filtered = [d for d in docs_list if search_term.lower() in d["label"].lower()] if search_term else docs_list

    if not filtered:
        st.warning(f"Aucun document trouvé avec '{search_term}'")
        return

    if search_term:
        st.caption(f"📄 {len(filtered)} document(s) trouvé(s)")

    selected_label = st.selectbox("Document:", options=[d["label"] for d in filtered])

    selected_doc = None
    selected_hash = None
    for d in filtered:
        if d["label"] == selected_label:
            selected_doc = d["doc"]
            selected_hash = d["hash"]
            break

    if not selected_doc:
        return

    st.markdown("---")

    # Renommage
    st.markdown("**2️⃣ Renommer le document**")
    current_filename = selected_doc.get("filename", "")
    st.text_input("Nom actuel :", value=current_filename, disabled=True, key=f"rename_current_{selected_hash}")

    rename_new_name = st.text_input("Nouveau nom :", value=current_filename, key=f"rename_new_{selected_hash}")

    if st.button("📝 Renommer", key=f"rename_btn_{selected_hash}"):
        result = enrichment_mgr.rename_document(selected_hash, rename_new_name)
        if result["success"]:
            st.success(result["message"])
            st.rerun()
        else:
            st.error(result["message"])

    st.markdown("---")

    # État actuel
    with st.expander("📋 État actuel de l'indexation", expanded=False):
        doc_format = selected_doc.get('document_format', 'non spécifié')
        if doc_format and doc_format != 'non spécifié':
            st.info(f"📄 **Format du document:** {doc_format}")

        st.markdown("### 📝 Résumé")
        st.write(selected_doc.get('summary', 'N/A'))

        col_kw, col_th = st.columns(2)
        with col_kw:
            st.markdown("### 🔑 Mots-clés")
            st.write(selected_doc.get('keywords', 'N/A'))
        with col_th:
            st.markdown("### 🏷️ Thèmes")
            st.write(selected_doc.get('themes', 'N/A'))

        if selected_doc.get("characteristics"):
            st.markdown("### 📋 Caractéristiques")
            chars = selected_doc["characteristics"]
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Matériaux:** {', '.join(chars['materials']) if chars.get('materials') else '_non spécifié_'}")
                st.markdown(f"**Domaines:** {', '.join(chars['focus_areas']) if chars.get('focus_areas') else '_non spécifié_'}")
                st.markdown(f"**Méthodologie:** {', '.join(chars['methodology']) if chars.get('methodology') else '_non spécifié_'}")
                st.markdown(f"**🔧 Équipements:** {', '.join(chars['equipment']) if chars.get('equipment') else '_non spécifié_'}")
            with col2:
                st.markdown(f"**Portée géographique:** {chars.get('geographical_scope') or '_non spécifié_'}")
                st.markdown(f"**Phase projet:** {chars.get('project_phase') or '_non spécifié_'}")
                st.markdown(f"**👥 Membres équipe:** {', '.join(chars['team_members']) if chars.get('team_members') else '_non spécifié_'}")
                st.markdown(f"**🎓 Rôles équipe:** {', '.join(chars['team_roles']) if chars.get('team_roles') else '_non spécifié_'}")

            if chars.get("special_sections"):
                st.markdown("### 📑 Sections spéciales")
                for section_name, section_summary in chars["special_sections"].items():
                    st.write(f"**• {section_name}:** {section_summary}")

        # Illustrations
        if selected_doc.get("special_illustrations"):
            illustrations = selected_doc["special_illustrations"]
            st.markdown(f"### 🖼️ Illustrations ({len(illustrations)})")
            for idx, illust in enumerate(illustrations, 1):
                col_img, col_info = st.columns([0.3, 0.7])
                with col_img:
                    if illust.get("image_path"):
                        img = _load_image_from_storage(illust["image_path"])
                        if img:
                            st.image(img, width=150)
                        else:
                            st.caption("⚠️ Image manquante")
                    else:
                        st.caption("📄 Pas d'image")
                with col_info:
                    cat = illust.get('category', '')
                    type_str = illust.get('type', 'Illustration')
                    st.markdown(f"**[{idx}] [{cat.upper()}] {type_str}**" if cat else f"**[{idx}] {type_str}**")
                    if illust.get('description'):
                        st.write(f"📝 {illust['description']}")
                    if illust.get('technical_keywords'):
                        st.caption(f"🔑 {', '.join(illust['technical_keywords'])}")

    st.markdown("---")
    st.markdown("**3️⃣ Décrivez vos modifications en langage naturel**")

    enrich_tab1, enrich_tab2, enrich_tab3 = st.tabs([
        "📝 Enrichissement général",
        "🖼️ Illustrations (Visuel)",
        "💬 Illustrations (Langage naturel)"
    ])

    enrichment_text = ""

    with enrich_tab1:
        enrichment_text = st.text_area(
            "Instructions pour enrichissement général:",
            height=120,
            placeholder="Exemples:\n- Ajoute 'béton précontraint' dans les matériaux et retire 'acier'\n- Change le résumé pour mettre en avant l'aspect diagnostic patrimonial",
            key="enrichment_general"
        )

    with enrich_tab2:
        st.markdown("### 🖼️ Enrichissement visuel des illustrations")

        # Illustrations existantes
        illustrations = selected_doc.get("special_illustrations", [])
        if illustrations:
            st.caption(f"{len(illustrations)} illustration(s)")
            for idx, illust in enumerate(illustrations, 1):
                col1, col2, col3 = st.columns([0.25, 0.55, 0.2])
                with col1:
                    if illust.get("image_path"):
                        img = _load_image_from_storage(illust["image_path"])
                        if img:
                            st.image(img, width=150)
                with col2:
                    cat = illust.get("category", "N/A")
                    st.markdown(f"**[{idx}] [{cat.upper()}] {illust.get('type', 'Illustration')}**")
                    st.caption(illust.get("description", "Pas de description"))
                with col3:
                    if st.button("🗑️ Supprimer", key=f"del_illust_{idx}", use_container_width=True):
                        st.session_state[f"confirm_delete_illust_{idx}"] = True
                        st.rerun()
                    if st.session_state.get(f"confirm_delete_illust_{idx}"):
                        st.warning("⚠️ Confirmer ?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Oui", key=f"confirm_yes_{idx}"):
                                selected_doc["special_illustrations"].pop(idx - 1)
                                _save_index(index)
                                del st.session_state[f"confirm_delete_illust_{idx}"]
                                st.success(f"✅ Illustration #{idx} supprimée")
                                st.rerun()
                        with c2:
                            if st.button("❌ Non", key=f"confirm_no_{idx}"):
                                del st.session_state[f"confirm_delete_illust_{idx}"]
                                st.rerun()
                st.markdown("---")
        else:
            st.info("📭 Aucune illustration enrichie pour ce document")

        # Ajouter une illustration
        st.markdown("#### ➕ Ajouter une nouvelle illustration")

        # Collage presse-papiers via streamlit-paste-button
        st.markdown("##### 📋 Option 1: Coller depuis le presse-papiers")
        try:
            from streamlit_paste_button import paste_image_button
            paste_result = paste_image_button("📋 Coller depuis le presse-papiers", key="paste_img_btn")
            if paste_result and paste_result.image_data:
                st.session_state.clipboard_image = paste_result.image_data
                st.image(paste_result.image_data, width=300)
        except ImportError:
            st.info("💡 Le package streamlit-paste-button n'est pas installé. Utilisez l'upload de fichier.")
            if 'clipboard_image' not in st.session_state:
                st.session_state.clipboard_image = None

        st.markdown("##### 📤 Option 2: Uploader un fichier")
        uploaded_file = st.file_uploader(
            "Glissez-déposez une image:",
            type=['png', 'jpg', 'jpeg'],
            key="add_illust_upload"
        )
        if uploaded_file:
            st.image(uploaded_file, width=300, caption="Image uploadée")

        st.markdown("##### 📝 Métadonnées")
        category_choice = st.selectbox(
            "Catégorie :",
            options=["Investigation", "Analyse", "Modélisation", "Préconisation", "Méthodologie", "Références", "Autre..."],
            key="add_illust_category"
        )
        category = category_choice
        if category_choice == "Autre...":
            category = st.text_input("Catégorie personnalisée :", key="add_illust_custom_category")

        illustration_type = st.selectbox(
            "Type :",
            options=["Schéma", "Photo", "Graphique", "Plan", "Diagramme", "Tableau", "Autre"],
            key="add_illust_type"
        )
        description = st.text_area(
            "Description détaillée :",
            height=100,
            placeholder="Décrivez précisément ce que montre l'illustration...",
            key="add_illust_description"
        )
        keywords_input = st.text_input(
            "Mots-clés techniques (séparés par des virgules) :",
            placeholder="plats carbone, renforcement, collage époxy...",
            key="add_illust_keywords"
        )
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        if st.button("➕ Ajouter l'illustration", type="primary", use_container_width=True, key="add_illust_submit"):
            clipboard_image = st.session_state.get('clipboard_image', None)
            errors = []
            if not uploaded_file and not clipboard_image:
                errors.append("⚠️ Veuillez fournir une image (fichier ou presse-papiers)")
            if not category:
                errors.append("⚠️ Veuillez sélectionner une catégorie")
            if not description:
                errors.append("⚠️ Veuillez saisir une description")
            if not keywords:
                errors.append("⚠️ Veuillez ajouter au moins un mot-clé technique")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                if "special_illustrations" not in selected_doc:
                    selected_doc["special_illustrations"] = []

                illust_index = len(selected_doc["special_illustrations"]) + 1
                storage = _get_storage()

                if clipboard_image:
                    buf = BytesIO()
                    clipboard_image.save(buf, format='PNG')
                    filename = f"illust_{illust_index:03d}.png"
                    image_path = storage.save_image(selected_doc["file_hash"], filename, buf.getvalue())
                else:
                    file_ext = Path(uploaded_file.name).suffix.lower()
                    if file_ext not in ['.png', '.jpg', '.jpeg']:
                        file_ext = '.png'
                    filename = f"illust_{illust_index:03d}{file_ext}"
                    image_path = storage.save_image(selected_doc["file_hash"], filename, uploaded_file.getbuffer())

                new_illustration = {
                    "category": category,
                    "type": illustration_type.lower(),
                    "description": description,
                    "technical_keywords": keywords,
                    "image_path": image_path,
                    "detection_method": "enrichissement manuel",
                    "confidence": "high",
                    "context": f"Ajouté par {get_current_user()} le {datetime.now().strftime('%Y-%m-%d')}",
                    "added_at": datetime.now().isoformat()
                }
                selected_doc["special_illustrations"].append(new_illustration)
                _save_index(index)

                if 'clipboard_image' in st.session_state:
                    st.session_state.clipboard_image = None

                st.success(f"✅ Illustration #{illust_index} ajoutée avec succès !")
                st.balloons()
                st.rerun()

    with enrich_tab3:
        st.caption("💡 Enrichissez les illustrations avec du langage naturel")
        if selected_doc.get("special_illustrations"):
            st.markdown("**Illustrations actuelles :**")
            for idx, illust in enumerate(selected_doc["special_illustrations"], 1):
                st.caption(f"[{idx}] {illust.get('description', 'Sans description')[:80]}")

        enrichment_text_illust = st.text_area(
            "Instructions pour les illustrations:",
            height=150,
            placeholder="Exemples:\n- Ajoute une illustration: schéma de carottage vertical, catégorie 'méthodologie'\n- Modifie l'illustration 1: ajoute les mots-clés 'géoradar, détection armatures'",
            key="enrichment_illustrations_nl"
        )
        if enrichment_text_illust:
            enrichment_text = enrichment_text_illust

    # Interprétation et application
    col1, col2 = st.columns([0.7, 0.3])
    with col2:
        interpret_btn = st.button("🔍 Interpréter", type="primary", use_container_width=True)

    if interpret_btn and enrichment_text:
        with st.spinner("🤖 Interprétation en cours..."):
            modifications = enrichment_mgr.interpret_natural_language_changes(selected_doc, enrichment_text)
            st.session_state["pending_modifications"] = modifications
            st.session_state["pending_doc_hash"] = selected_hash

    if "pending_modifications" in st.session_state:
        mods = st.session_state["pending_modifications"]

        if mods.get("error"):
            st.error(f"❌ {mods['error']}")
        else:
            st.markdown("---")
            st.markdown("**4️⃣ Modifications proposées**")
            st.info(f"📝 {mods.get('résumé_modifications', 'Modifications détectées')}")

            for i, modif in enumerate(mods.get("modifications", []), 1):
                col1, col2, col3 = st.columns([0.15, 0.5, 0.35])
                with col1:
                    action_emoji = {"AJOUTER": "➕", "RETIRER": "➖", "MODIFIER": "✏️", "CRÉER": "🆕", "VIDER": "🗑️"}
                    st.markdown(f"### {action_emoji.get(modif['action'], '•')}")
                with col2:
                    st.markdown(f"**{modif['action']}** dans `{modif['champ']}`")
                    valeur_str = modif['valeur']
                    if isinstance(valeur_str, list):
                        valeur_str = ", ".join(str(v) for v in valeur_str)
                    elif isinstance(valeur_str, dict):
                        valeur_str = json.dumps(valeur_str, ensure_ascii=False, indent=2)
                    st.caption(f"Valeur: {valeur_str}")
                with col3:
                    st.caption(f"💡 {modif['raison']}")

            col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
            with col2:
                validate_btn = st.button("✅ Valider et appliquer", type="primary", use_container_width=True)
            with col3:
                cancel_btn = st.button("❌ Annuler", use_container_width=True)

            if validate_btn:
                with st.spinner("💾 Application des modifications..."):
                    success = enrichment_mgr.apply_enrichment(
                        st.session_state["pending_doc_hash"],
                        st.session_state["pending_modifications"],
                        user_validated=True
                    )
                    if success:
                        # Marquer comme enrichi
                        for doc in index.get("documents", []):
                            if doc.get("file_hash") == st.session_state["pending_doc_hash"]:
                                mark_enriched(doc, get_current_user())
                                break
                        _save_index(index)

                        st.success("✅ Enrichissement appliqué avec succès!")
                        del st.session_state["pending_modifications"]
                        del st.session_state["pending_doc_hash"]
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Échec de l'application de l'enrichissement")

            if cancel_btn:
                del st.session_state["pending_modifications"]
                del st.session_state["pending_doc_hash"]
                st.rerun()


# ============================================================
# TAB: Indexation
# ============================================================
def tab_indexation(index):
    """Onglet d'indexation de nouveaux documents."""
    st.markdown("### 📥 Indexation de Documents")
    st.caption("Indexez de nouveaux mémoires techniques ou réindexez des documents existants")

    current_user = get_current_user()

    # Verrou d'indexation
    storage = _get_storage()
    lock_info = storage.get_lock_info("indexation")
    if lock_info and lock_info.get("owner") != current_user:
        st.warning(f"🔒 Indexation verrouillée par **{lock_info.get('owner', '?')}**. Veuillez attendre.")
        return

    # Mode d'indexation
    indexation_mode = st.radio(
        "Que souhaitez-vous indexer ?",
        ["📁 Dossier complet", "📄 Fichier(s) individuel(s)", "🔄 Utiliser le chemin par défaut (.env)"],
    )

    force_reindex = st.checkbox(
        "🔄 Forcer la réindexation (même pour fichiers déjà indexés)",
        value=False,
    )

    st.markdown("---")

    path_to_index = None

    if indexation_mode == "📁 Dossier complet":
        st.markdown("**1️⃣ Spécifiez le chemin du dossier**")
        if "folder_path_input" not in st.session_state:
            st.session_state["folder_path_input"] = config.LOCAL_DOCS_PATH or ""

        folder_path = st.text_input(
            "Chemin du dossier:",
            placeholder="C:\\Users\\David\\Documents\\MTs",
            key="folder_path_input"
        )

        if folder_path:
            folder_path_obj = Path(folder_path)
            if folder_path_obj.exists() and folder_path_obj.is_dir():
                file_count = len([f for f in folder_path_obj.rglob("*")
                                 if f.suffix.lower() in config.SUPPORTED_EXTENSIONS
                                 and not f.name.startswith('~$')])
                st.info(f"📊 {file_count} fichier(s) trouvé(s) dans ce dossier")
                path_to_index = folder_path
            elif folder_path:
                st.error("❌ Ce dossier n'existe pas ou n'est pas accessible")

    elif indexation_mode == "📄 Fichier(s) individuel(s)":
        st.markdown("**1️⃣ Spécifiez le(s) chemin(s) des fichiers**")
        files_input = st.text_area(
            "Chemins des fichiers (un par ligne):",
            height=120,
            placeholder="C:\\MTs\\Document1.docx\nC:\\MTs\\Document2.pdf",
            key="files_input_area"
        )

        if files_input:
            file_paths = [line.strip() for line in files_input.split('\n') if line.strip()]
            valid_files = [fp for fp in file_paths if Path(fp).exists() and Path(fp).is_file()]
            invalid_files = [fp for fp in file_paths if fp not in valid_files]

            if valid_files:
                st.success(f"✅ {len(valid_files)} fichier(s) valide(s)")
                path_to_index = valid_files[0] if len(valid_files) == 1 else None
                if len(valid_files) > 1:
                    st.session_state["files_to_index"] = valid_files
            if invalid_files:
                st.error(f"❌ {len(invalid_files)} fichier(s) invalide(s)")

    else:
        if config.LOCAL_DOCS_PATH:
            st.info(f"📁 Chemin configuré: `{config.LOCAL_DOCS_PATH}`")
            default_path_obj = Path(config.LOCAL_DOCS_PATH)
            if default_path_obj.exists():
                file_count = len([f for f in default_path_obj.rglob("*")
                                 if f.suffix.lower() in config.SUPPORTED_EXTENSIONS
                                 and not f.name.startswith('~$')])
                st.info(f"📊 {file_count} fichier(s) trouvé(s)")
                path_to_index = config.LOCAL_DOCS_PATH
            else:
                st.error("❌ Le chemin par défaut n'existe pas")
        else:
            st.warning("⚠️ Aucun chemin par défaut configuré dans le fichier .env")

    st.markdown("---")

    col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
    with col2:
        index_btn = st.button(
            "🚀 Lancer l'indexation",
            type="primary",
            use_container_width=True,
            disabled=(path_to_index is None and "files_to_index" not in st.session_state)
        )

    if index_btn:
        paths_to_process = []
        if "files_to_index" in st.session_state:
            paths_to_process = st.session_state["files_to_index"]
        elif path_to_index:
            paths_to_process = [path_to_index]

        if paths_to_process:
            # Acquérir le verrou
            if not storage.acquire_lock("indexation", current_user):
                st.error("🔒 Impossible d'acquérir le verrou d'indexation")
                return

            try:
                indexer = DocumentIndexer()

                all_files = []
                for path in paths_to_process:
                    path_obj = Path(path)
                    files = indexer.get_files_to_process(path_obj)
                    all_files.extend(files)

                if not all_files:
                    st.warning("⚠️ Aucun fichier à indexer trouvé")
                else:
                    st.info(f"📁 {len(all_files)} fichier(s) à traiter")

                    log_container = st.container()
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    total_indexed = 0
                    total_skipped = 0
                    total_errors = 0

                    for i, file_path in enumerate(all_files):
                        progress = (i + 1) / len(all_files)
                        progress_bar.progress(progress)
                        status_text.text(f"📄 {file_path.name} ({i+1}/{len(all_files)})")

                        result = indexer.index_single_file(file_path, force_reindex=force_reindex, user=current_user)

                        with log_container:
                            if result["status"] == "indexed":
                                total_indexed += 1
                                st.success(f"✅ {file_path.name}")
                            elif result["status"] == "skipped":
                                total_skipped += 1
                                st.info(f"⏭️ {file_path.name} (déjà indexé)")
                            else:
                                total_errors += 1
                                st.error(f"❌ {file_path.name}: {result.get('message', 'Erreur')}")

                    progress_bar.progress(1.0)
                    status_text.text("✅ Indexation terminée !")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📥 Indexés", total_indexed)
                    with col2:
                        st.metric("⏭️ Ignorés", total_skipped)
                    with col3:
                        st.metric("❌ Erreurs", total_errors)

                    if "files_to_index" in st.session_state:
                        del st.session_state["files_to_index"]

                    st.balloons()

            except Exception as e:
                st.error(f"❌ Erreur lors de l'indexation: {str(e)}")
                st.exception(e)
            finally:
                storage.release_lock("indexation", current_user)


# ============================================================
# TAB: Admin
# ============================================================
def tab_admin(index):
    """Onglet d'administration (protégé par mot de passe)."""
    st.markdown("### 🔒 Administration")

    if not is_admin():
        st.warning("Cette section est réservée aux administrateurs.")
        return

    if not require_admin_password():
        return

    st.success("✅ Authentifié en tant qu'administrateur")

    admin_section = st.radio(
        "Section :",
        ["🎓 Améliorations IA", "📚 Règles apprises", "🔄 Cycle d'apprentissage", "🔧 Migration index"],
        horizontal=True,
    )

    if admin_section == "🎓 Améliorations IA":
        _admin_improvements()
    elif admin_section == "📚 Règles apprises":
        _admin_learned_rules()
    elif admin_section == "🔄 Cycle d'apprentissage":
        _admin_learning_cycle()
    elif admin_section == "🔧 Migration index":
        _admin_migration(index)


def _admin_improvements():
    """Section des améliorations suggérées par le système d'apprentissage."""
    learning_system = LearningSystem()
    latest_improvements = learning_system.get_latest_improvements()

    if not latest_improvements.get("improvements"):
        st.info("🔄 Aucune amélioration disponible pour le moment.")
        if st.button("🔄 Lancer l'analyse maintenant"):
            with st.spinner("🤖 Analyse en cours..."):
                result = learning_system.run_learning_cycle()
                if result.get("success"):
                    st.success("✅ Analyse terminée !")
                    st.rerun()
                else:
                    st.warning("⚠️ Pas assez de données pour générer des améliorations")
        return

    improvements = latest_improvements["improvements"]

    if latest_improvements.get("résumé"):
        st.info(f"📊 {latest_improvements['résumé']}")

    validated_count = sum(1 for imp in improvements if imp.get("validated") == True and not imp.get("committed"))
    if validated_count > 0:
        if st.button(f"✅ Appliquer {validated_count} amélioration(s) validée(s)", type="primary"):
            result = learning_system.commit_improvements()
            if result["success"]:
                st.success(f"✅ {result['message']}")
                st.rerun()

    for i, imp in enumerate(improvements):
        priorité = imp.get("priorité", "moyenne").upper()
        priorité_color = {"HAUTE": "🔴", "MOYENNE": "🟡", "BASSE": "🟢"}.get(priorité, "⚪")

        if imp.get("committed"):
            status_icon = "✅"
            status_text = "Appliquée"
        elif imp.get("validated") == True:
            status_icon = "🟢"
            status_text = "Validée"
        elif imp.get("validated") == False:
            status_icon = "❌"
            status_text = "Rejetée"
        else:
            status_icon = "⏳"
            status_text = "En attente"

        with st.expander(f"{status_icon} {priorité_color} [{priorité}] {imp.get('probleme', '?')}", expanded=(status_text == "En attente" and i < 3)):
            st.markdown(f"**Statut:** {status_text}")
            st.markdown(f"**Champ concerné:** `{imp.get('champ_concerné', 'N/A')}`")
            st.markdown(f"**Suggestion:** {imp.get('suggestion', 'N/A')}")

            if imp.get('exemple_prompt'):
                current_text = imp.get('exemple_prompt_modified') or imp.get('exemple_prompt')
                if not imp.get("committed"):
                    edited_text = st.text_area("Modifiez si nécessaire:", value=current_text, key=f"edit_prompt_{i}", height=150)
                else:
                    st.code(current_text, language="text")

            if not imp.get("committed") and imp.get("validated") is None:
                col_val, col_rej = st.columns(2)
                with col_val:
                    if st.button("✅ Valider", key=f"validate_{i}", type="primary"):
                        modified = edited_text if edited_text != imp.get('exemple_prompt') else None
                        if learning_system.validate_improvement(i, True, modified):
                            st.success("Amélioration validée !")
                            st.rerun()
                with col_rej:
                    if st.button("❌ Rejeter", key=f"reject_{i}"):
                        if learning_system.validate_improvement(i, False):
                            st.info("Amélioration rejetée")
                            st.rerun()


def _admin_learned_rules():
    """Section des règles apprises."""
    learning_system = LearningSystem()
    learned_rules = learning_system.get_learned_rules()

    if learned_rules:
        st.markdown(f"📚 **{len(learned_rules)} règle(s) appliquée(s)**")
        for rule in learned_rules:
            st.markdown(f"- **{rule.get('champ')}**: {rule.get('suggestion', '')[:100]}...")
    else:
        st.info("Aucune règle apprise pour le moment.")


def _admin_learning_cycle():
    """Lance un cycle d'apprentissage."""
    if st.button("🔄 Lancer le cycle d'apprentissage", type="primary"):
        with st.spinner("🤖 Analyse en cours..."):
            learning_system = LearningSystem()
            result = learning_system.run_learning_cycle()
            if result.get("success"):
                st.success("✅ Cycle d'apprentissage terminé !")
                improvements = result.get("improvements", {}).get("improvements", [])
                st.info(f"📊 {len(improvements)} amélioration(s) proposée(s)")
                st.rerun()
            else:
                st.warning("⚠️ Échec du cycle d'apprentissage")


def _admin_migration(index):
    """Migration de l'index vers le nouveau format."""
    st.markdown("### 🔧 Migration de l'index")
    st.caption("Ajoute les champs de traçabilité (status, indexed_by, etc.) aux documents existants")

    docs_without_status = [d for d in index.get("documents", []) if "status" not in d]
    if not docs_without_status:
        st.success("✅ Tous les documents ont déjà été migrés.")
        return

    st.warning(f"⚠️ {len(docs_without_status)} document(s) sans champs de traçabilité")

    if st.button("🔄 Lancer la migration", type="primary"):
        for doc in index.get("documents", []):
            migrate_document(doc)
        index["schema_version"] = "2.0"
        _save_index(index)
        st.success(f"✅ {len(docs_without_status)} document(s) migré(s)")
        st.rerun()


# ============================================================
# MAIN
# ============================================================
def main():
    """Point d'entrée principal de l'application."""

    # Authentification
    if not require_user():
        st.stop()

    # Badge utilisateur dans la sidebar
    show_user_badge()

    # Titre principal
    st.markdown('<p class="main-title">🔍 Recherche de Mémoires Techniques Similaires</p>',
                unsafe_allow_html=True)

    # Charger l'index
    index = _load_index()

    if not index.get("documents"):
        st.warning("⚠️ L'index est vide. Utilisez l'onglet Indexation pour indexer des documents.")

    # Statistiques en haut
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📚 Documents indexés", len(index.get("documents", [])))
    with col2:
        if index.get("last_updated"):
            st.metric("🕐 Dernière mise à jour", index["last_updated"][:10])
    with col3:
        v2_count = sum(1 for doc in index.get("documents", []) if doc.get("analysis_version") == "2.0")
        st.metric("⚡ Documents enrichis (v2.0)", v2_count)
    with col4:
        illust_count = sum(1 for doc in index.get("documents", []) if doc.get("special_illustrations"))
        st.metric("🖼️ Avec illustrations", illust_count)

    st.markdown("---")

    # Onglets
    tabs = st.tabs([
        "🔍 Recherche",
        "📊 Tableau de bord",
        "✅ Validation",
        "✏️ Enrichissement",
        "📥 Indexation",
        "🔒 Admin",
    ])

    with tabs[0]:
        tab_recherche(index)
    with tabs[1]:
        tab_dashboard(index)
    with tabs[2]:
        tab_validation(index)
    with tabs[3]:
        tab_enrichissement(index)
    with tabs[4]:
        tab_indexation(index)
    with tabs[5]:
        tab_admin(index)


if __name__ == "__main__":
    main()
