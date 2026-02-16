"""Module d'authentification utilisateur."""
import streamlit as st
import config

USERS = {
    "David": {"role": "admin"},
    "Robin": {"role": "user"},
    "Emmanuelle": {"role": "user"},
}


def require_user():
    """Affiche un sélecteur 'Qui êtes-vous ?' au démarrage.

    Bloque le rendu de l'application tant qu'un utilisateur n'est pas sélectionné.
    Le choix est stocké dans st.session_state["current_user"].

    Returns:
        True si un utilisateur est sélectionné, False sinon
    """
    if "current_user" in st.session_state and st.session_state["current_user"]:
        return True

    st.markdown("## Bienvenue")
    st.markdown("Veuillez vous identifier pour continuer.")

    user = st.selectbox(
        "Qui êtes-vous ?",
        options=[""] + list(USERS.keys()),
        index=0,
        key="_user_selector",
    )

    if user:
        st.session_state["current_user"] = user
        st.rerun()

    return False


def get_current_user() -> str:
    """Retourne le nom de l'utilisateur courant.

    Returns:
        Nom de l'utilisateur ou chaîne vide
    """
    return st.session_state.get("current_user", "")


def get_current_role() -> str:
    """Retourne le rôle de l'utilisateur courant.

    Returns:
        'admin', 'user', ou ''
    """
    user = get_current_user()
    return USERS.get(user, {}).get("role", "")


def is_admin() -> bool:
    """Vérifie si l'utilisateur courant est admin.

    Returns:
        True si admin
    """
    return get_current_role() == "admin"


def require_admin_password() -> bool:
    """Prompt mot de passe pour fonctions admin.

    Returns:
        True si le mot de passe est correct
    """
    if not is_admin():
        st.warning("Cette section est réservée aux administrateurs.")
        return False

    if st.session_state.get("admin_authenticated"):
        return True

    password = st.text_input(
        "Mot de passe admin :",
        type="password",
        key="_admin_password_input",
    )

    if password:
        if password == config.ADMIN_PASSWORD:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")

    return False


def show_user_badge():
    """Affiche l'utilisateur courant dans la sidebar."""
    user = get_current_user()
    if not user:
        return

    role = get_current_role()
    role_emoji = "🔒" if role == "admin" else "👤"

    with st.sidebar:
        st.markdown(f"### {role_emoji} {user}")
        st.caption(f"Rôle : {role}")

        if st.button("Se déconnecter", key="_logout_btn"):
            for key in ["current_user", "admin_authenticated"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
