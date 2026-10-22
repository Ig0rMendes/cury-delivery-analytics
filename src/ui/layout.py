"""Preparação comum de página: configuração, logo, dados e filtros."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.config import APP_ICON, APP_TITLE, DATA_NAME
from src.processing.cleaning import CleaningReport
from src.processing.loader import DataNotFoundError, SchemaError, expected_location
from src.processing.filtering import Filters
from src.ui.branding import show_logo
from src.ui.data_access import get_data
from src.ui.filters import apply_sidebar


# pacotinho com tudo que a pagina precisa: base completa, base filtrada, filtros, SLA e relatorio
@dataclass
class PageContext:
    df: pd.DataFrame            # base completa (sem filtros)
    df_f: pd.DataFrame          # base filtrada
    flt: Filters
    sla: int
    report: CleaningReport

    @property
    def filtered(self) -> bool:
        return len(self.df_f) < len(self.df)


# carrega os dados. se faltar o arquivo ou o formato estiver errado, mostra mensagem amigavel e para
def _load_or_stop():
    try:
        return get_data()
    except DataNotFoundError:
        st.error(
            f"Base **{DATA_NAME}** não encontrada. Copie o arquivo **{DATA_NAME}.csv** para a pasta:\n\n"
            f"`{expected_location().parent}`\n\nDepois recarregue esta página."
        )
        st.stop()
    except SchemaError as exc:
        st.error(f"O arquivo encontrado não parece ser o `{DATA_NAME}` esperado.\n\n{exc}")
        st.stop()


# chamar na primeira linha de cada pagina de analise: configura, carrega, filtra e poe o titulo
def setup_page(title: str, icon: str) -> PageContext:
    """Chamar na primeira linha de cada página de análise."""
    st.set_page_config(page_title=f"{title} · {APP_TITLE}", page_icon=icon, layout="wide")
    show_logo()
    df, report = _load_or_stop()
    df_f, flt, sla = apply_sidebar(df)
    st.title(f"{icon} {title}")
    return PageContext(df=df, df_f=df_f, flt=flt, sla=sla, report=report)


# a home nao tem filtros, so apresenta o projeto e a qualidade dos dados
def setup_home():
    """Home: sem filtros (apresenta o projeto e a qualidade dos dados)."""
    st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
    show_logo()
    return _load_or_stop()
