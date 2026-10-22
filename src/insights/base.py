"""Estrutura comum dos insights."""
from __future__ import annotations

from dataclasses import dataclass

# os 4 tipos de insight: achado, oportunidade, risco e ressalva (info)
KINDS = ("finding", "opportunity", "risk", "info")
ICONS = {"finding": "🔎", "opportunity": "💡", "risk": "⚠️", "info": "ℹ️"}
KIND_LABEL = {"finding": "Achado", "opportunity": "Oportunidade", "risk": "Risco", "info": "Atenção à leitura"}


# um insight = tipo + titulo + detalhe + acao sugerida. imutavel (frozen) pra ninguem mexer depois de criado
@dataclass(frozen=True)
class Insight:
    """kind: finding | opportunity | risk | info. `action` é a ação sugerida (opcional)."""

    kind: str
    headline: str
    detail: str = ""
    action: str = ""

    @property
    def icon(self) -> str:
        return ICONS.get(self.kind, "ℹ️")

    # usado no README e no RESULTADOS.md
    def as_markdown(self) -> str:
        parts = [f"**{self.icon} {self.headline}**"]
        if self.detail:
            parts.append(self.detail)
        if self.action:
            parts.append(f"**Ação sugerida:** {self.action}")
        return "\n\n".join(parts)


# com menos de 100 pedidos nao vale tirar conclusao, entao os insights viram so um aviso
MIN_ORDERS_FOR_INSIGHTS = 100


# devolve o aviso padrao quando o recorte ta pequeno demais (ou None se ta tudo certo)
def too_small(df, minimum: int = MIN_ORDERS_FOR_INSIGHTS) -> list[Insight] | None:
    """Aviso padrão quando o recorte é pequeno demais para conclusões."""
    if len(df) < minimum:
        return [Insight("info", "Recorte pequeno demais para conclusões",
                        f"Há apenas {len(df)} pedidos nos filtros atuais. Amplie o período ou as condições "
                        f"para que os indicadores sejam estatisticamente confiáveis (mínimo recomendado: {minimum}).")]
    return None
