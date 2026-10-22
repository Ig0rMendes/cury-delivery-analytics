"""Construtores de gráficos Plotly (graph_objects). Cada função devolve um go.Figure."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.visuals import theme


# converte pra array de float, assim o plotly nao se perde com tipos do pandas
def _f(series) -> np.ndarray:
    return np.asarray(series, dtype=float)


# barras com intervalo de confianca de 95% (a barrinha de erro)
def bar_ci(labels, mean, ci_low, ci_high, colors=None, title=None, ytitle="Minutos", height=340,
           fmt="%{y:.1f}", hline: float | None = None, hline_label: str | None = None):
    """Barras com intervalo de confiança de 95%."""
    mean, lo, hi = _f(mean), _f(ci_low), _f(ci_high)
    fig = go.Figure(go.Bar(
        x=[str(x) for x in labels], y=mean,
        marker_color=colors if colors is not None else theme.PRIMARY,
        error_y=dict(type="data", symmetric=False, array=np.nan_to_num(hi - mean), arrayminus=np.nan_to_num(mean - lo)),
        texttemplate=fmt, textposition="outside", cliponaxis=False,
        hovertemplate="%{x}<br>%{y:.2f}<extra></extra>",
    ))
    if hline is not None:
        fig.add_hline(y=hline, line_dash="dash", line_color=theme.NEUTRAL,
                      annotation_text=hline_label or "", annotation_position="top left")
    return theme.apply_layout(fig, title, height, ytitle)


# barras simples, vertical ou horizontal
def bar_simple(labels, values, color=None, title=None, ytitle=None, height=340, fmt="%{y:,.0f}", horizontal=False):
    vals = _f(values)
    labels = [str(x) for x in labels]
    if horizontal:
        fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker_color=color or theme.PRIMARY,
                               texttemplate=fmt.replace("{y", "{x"), textposition="outside", cliponaxis=False))
        fig.update_yaxes(autorange="reversed")
    else:
        fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=color or theme.PRIMARY,
                               texttemplate=fmt, textposition="outside", cliponaxis=False))
    return theme.apply_layout(fig, title, height, ytitle)


# barras + linha em eixos diferentes (volume x tempo, por exemplo)
def dual_axis(x, bars, line, bar_name, line_name, title=None, height=360, bar_color=None, line_color=None,
              y1_title=None, y2_title=None, hline: float | None = None, hline_label: str | None = None):
    """Barras (eixo esquerdo) + linha (eixo direito)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=list(x), y=_f(bars), name=bar_name, marker_color=bar_color or theme.NEUTRAL, opacity=0.55),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=list(x), y=_f(line), name=line_name, mode="lines+markers",
                             line=dict(color=line_color or theme.PRIMARY, width=3)), secondary_y=True)
    if hline is not None and len(list(x)) > 0:
        xs = list(x)
        fig.add_trace(go.Scatter(x=[xs[0], xs[-1]], y=[hline, hline], mode="lines", name=hline_label or "Meta",
                                 line=dict(dash="dash", color=theme.BAD, width=1.5)), secondary_y=True)
    fig.update_yaxes(title_text=y1_title or bar_name, secondary_y=False)
    fig.update_yaxes(title_text=y2_title or line_name, secondary_y=True, showgrid=False)
    theme.apply_layout(fig, title, height, legend=True)
    fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
    return fig


# varias linhas no mesmo grafico
def line_series(x, ys: dict, title=None, height=340, ytitle=None):
    fig = go.Figure()
    for i, (name, y) in enumerate(ys.items()):
        fig.add_trace(go.Scatter(x=list(x), y=_f(y), name=name, mode="lines",
                                 line=dict(width=2.5, color=[theme.PRIMARY, theme.ACCENT, theme.GOOD][i % 3])))
    return theme.apply_layout(fig, title, height, ytitle, legend=len(ys) > 1)


# mapa de calor. eixos como categoria pra hora nao virar escala numerica com buraco
def heatmap(z, x, y, title=None, colorscale=None, height=360, texttemplate="%{z:.0f}", zlabel="", xtitle=None, ytitle=None):
    z = np.asarray(z, dtype=float)
    fig = go.Figure(go.Heatmap(
        z=z, x=[str(i) for i in x], y=[str(i) for i in y], colorscale=colorscale or theme.DEMAND_SCALE,
        texttemplate=texttemplate, hovertemplate="%{y} · %{x}<br>" + (zlabel or "valor") + ": %{z:.1f}<extra></extra>",
        colorbar=dict(title=zlabel) if zlabel else None,
    ))
    fig.update_xaxes(type="category")  # horas como categorias: sem colunas largas onde não há pedidos
    fig.update_yaxes(type="category")
    return theme.apply_layout(fig, title, height, ytitle, xtitle)


# barras empilhadas: preparo + entrega = espera total
def stacked_composition(labels, prep, delivery, title=None, height=320, xtitle="Minutos"):
    """Barras horizontais empilhadas: preparo + entrega."""
    labels = [str(x) for x in labels]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=_f(prep), name="Preparo", orientation="h", marker_color=theme.ACCENT,
                         texttemplate="%{x:.1f}"))
    fig.add_trace(go.Bar(y=labels, x=_f(delivery), name="Entrega", orientation="h", marker_color=theme.PRIMARY,
                         texttemplate="%{x:.1f}"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed")
    theme.apply_layout(fig, title, height, xtitle=xtitle, legend=True)
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0))
    return fig


# histograma, com linha vertical opcional (tipo o SLA)
def histogram(values, title=None, xtitle="Minutos", height=320, vline: float | None = None, vline_label: str | None = None,
              nbins: int | None = None, color=None):
    v = pd.Series(values).dropna().astype(float)
    fig = go.Figure(go.Histogram(x=v.to_numpy(), nbinsx=nbins, marker_color=color or theme.PRIMARY))
    if vline is not None:
        fig.add_vline(x=vline, line_dash="dash", line_color=theme.BAD,
                      annotation_text=vline_label or "", annotation_position="top right")
    return theme.apply_layout(fig, title, height, "Pedidos", xtitle)


# efeitos isolados com IC: vermelho = piora com certeza, verde = melhora, cinza = nao da pra afirmar
def effects_chart(table: pd.DataFrame, title="Efeito isolado no tempo de entrega (min)", height=None):
    """Pontos com IC95% (horizontal). Esperado: colunas label, effect, ci_low, ci_high."""
    t = table.sort_values("effect")
    colors = [theme.BAD if lo > 0 else (theme.GOOD if hi < 0 else theme.NEUTRAL)
              for lo, hi in zip(t["ci_low"], t["ci_high"])]
    fig = go.Figure(go.Scatter(
        x=_f(t["effect"]), y=t["label"].astype(str).tolist(), mode="markers",
        marker=dict(size=10, color=colors),
        error_x=dict(type="data", symmetric=False, array=_f(t["ci_high"] - t["effect"]), arrayminus=_f(t["effect"] - t["ci_low"])),
        hovertemplate="%{y}<br>%{x:+.2f} min<extra></extra>",
    ))
    fig.add_vline(x=0, line_color=theme.NEUTRAL)
    return theme.apply_layout(fig, title, height or max(320, 26 * len(t) + 90), xtitle="Minutos a mais (+) ou a menos (-) vs. referência")


# mapa de bolhas: tamanho = pedidos, cor = tempo medio de entrega
def city_map(table: pd.DataFrame, title=None, height=460):
    """Bolhas por cidade: tamanho = pedidos, cor = tempo médio de entrega."""
    t = table.dropna(subset=["lat", "lon"])
    fig = go.Figure(go.Scattergeo(
        lat=_f(t["lat"]), lon=_f(t["lon"]), mode="markers",
        text=[f"{c}<br>{int(n):,} pedidos<br>{m:.1f} min" for c, n, m in zip(t["city"], t["n"], t["mean_delivery"])],
        hoverinfo="text",
        marker=dict(size=np.clip(np.sqrt(_f(t["n"])) * 1.1, 8, 60), color=_f(t["mean_delivery"]),
                    colorscale=theme.HEAT_SCALE, showscale=True, colorbar=dict(title="min"),
                    line=dict(width=1, color="white"), opacity=0.85),
    ))
    fig.update_geos(
        fitbounds="locations", showcountries=True, countrycolor="#94A3B8", showland=True,
        landcolor="rgba(148,163,184,0.18)", showocean=False, showframe=False, projection_type="mercator",
    )
    return theme.apply_layout(fig, title, height)


# curva de concentracao dos restaurantes contra a linha de distribuicao uniforme
def pareto_chart(par: pd.DataFrame, title="Concentração de pedidos por restaurante", height=340):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Distribuição uniforme",
                             line=dict(dash="dash", color=theme.NEUTRAL)))
    fig.add_trace(go.Scatter(x=_f(par["rank_pct"]), y=_f(par["cum_orders_pct"]), mode="lines", name="Real",
                             line=dict(color=theme.PRIMARY, width=3)))
    fig.update_xaxes(tickformat=".0%", title_text="% dos restaurantes (do maior para o menor)")
    fig.update_yaxes(tickformat=".0%", title_text="% acumulado dos pedidos")
    return theme.apply_layout(fig, title, height, legend=True)


# cada ponto e um entregador: pedidos x excesso vs esperado. acima de zero = mais lento
def courier_scatter(table: pd.DataFrame, title=None, height=400):
    """Volume (x) x desempenho vs. esperado (y). Acima de 0 = mais lento que o esperado."""
    fig = go.Figure()
    for status, color in theme.STATUS_COLORS.items():
        sub = table[table["status"] == status]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=_f(sub["orders"]), y=_f(sub["excess"]), mode="markers", name=status,
            marker=dict(color=color, size=8, opacity=0.8),
            text=sub["courier_id"].astype(str).tolist(),
            hovertemplate="%{text}<br>%{x} pedidos<br>%{y:+.1f} min vs. esperado<extra></extra>",
        ))
    fig.add_hline(y=0, line_color=theme.NEUTRAL)
    theme.apply_layout(fig, title, height, "Minutos vs. esperado (+ = mais lento)", "Pedidos do entregador", legend=True)
    fig.update_layout(legend=dict(orientation="h", y=1.12, x=0))
    return fig
