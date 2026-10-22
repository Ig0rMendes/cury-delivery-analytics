"""Paleta e layout comuns. O tema (claro/escuro) é herdado do Streamlit."""
from __future__ import annotations

# paleta de cores do painel. mexeu aqui, muda em todos os graficos
PRIMARY = "#2563EB"
SECONDARY = "#0EA5E9"
ACCENT = "#F59E0B"
GOOD = "#16A34A"
BAD = "#DC2626"
NEUTRAL = "#94A3B8"

# cor de cada nivel de transito (verde -> vermelho)
TRAFFIC_COLORS = {"Low": GOOD, "Medium": "#EAB308", "High": "#F97316", "Jam": BAD}
STATUS_COLORS = {
    "Mais lento que o esperado": BAD,
    "Dentro do esperado": NEUTRAL,
    "Mais rápido que o esperado": GOOD,
    "Indefinido": "#CBD5E1",
}
# escalas de cor dos mapas de calor
HEAT_SCALE = [[0.0, "#DCFCE7"], [0.5, "#FDE68A"], [1.0, "#DC2626"]]
DEMAND_SCALE = "Blues"


# acabamento padrao de todo grafico: margens, titulo e eixos
# o titulo vazio e explicito pra nao aparecer 'undefined' no plotly 6
def apply_layout(fig, title: str | None = None, height: int = 360, ytitle: str | None = None,
                 xtitle: str | None = None, legend: bool = False):
    """Margens enxutas, título e eixos. Não define `template` (mantém o tema do Streamlit)."""
    fig.update_layout(
        # texto vazio explícito evita o "undefined" que o Plotly 6 mostra quando há título sem texto
        title=dict(text=title or "", x=0.0, xanchor="left"),
        height=height,
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        showlegend=legend,
    )
    if ytitle is not None:
        fig.update_yaxes(title_text=ytitle)
    if xtitle is not None:
        fig.update_xaxes(title_text=xtitle)
    return fig
