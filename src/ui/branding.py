"""Logo na barra lateral (assets/Logo.png). Se o arquivo não existir, o app segue sem logo."""
from __future__ import annotations

import base64
from functools import lru_cache
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


# converte a imagem em texto (data URI) pra ela ir embutida na pagina.
# assim nao depende do armazenamento de arquivos do streamlit, que na nuvem as vezes perde a imagem
@lru_cache(maxsize=4)
def _data_uri(path: str, mtime: float) -> str:
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    raw = Path(path).read_bytes()
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


# mostra o logo com fallback pra versoes antigas do streamlit
def show_logo() -> bool:
    logo = find_logo()
    if logo is None:
        return False
    try:
        src = _data_uri(str(logo), logo.stat().st_mtime)
    except OSError:
        src = str(logo)        # se nao deu pra ler, tenta o caminho normal
    try:
        st.logo(src, size="large")
    except TypeError:          # Streamlit sem o parâmetro `size`
        st.logo(src)
    except AttributeError:     # Streamlit < 1.35 (sem st.logo)
        st.sidebar.image(str(logo), width=140)
    return True