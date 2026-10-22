"""Logo na barra lateral (assets/Logo.png). Se o arquivo não existir, o app segue sem logo."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.config import ASSETS_DIR, LOGO_NAME


# acha o logo na pasta assets. se nao tiver logo o app roda do mesmo jeito
def find_logo() -> Path | None:
    """Procura o logo ignorando maiúsculas/minúsculas (Windows aceita; Linux não)."""
    if not ASSETS_DIR.is_dir():
        return None
    for f in ASSETS_DIR.iterdir():
        if f.is_file() and f.name.lower() == LOGO_NAME:
            return f
    return None


# mostra o logo com fallback pra versoes antigas do streamlit
def show_logo() -> bool:
    logo = find_logo()
    if logo is None:
        return False
    try:
        st.logo(str(logo), size="large")
    except TypeError:          # Streamlit sem o parâmetro `size`
        st.logo(str(logo))
    except AttributeError:     # Streamlit < 1.35 (sem st.logo)
        st.sidebar.image(str(logo), width=140)
    return True
