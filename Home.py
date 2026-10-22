"""Página inicial: contexto do projeto e qualidade dos dados. Execute com: streamlit run Home.py"""
import streamlit as st

from src.config import APP_TITLE, DATA_NAME, VERSION
from src.ui.components import card, show_table
from src.ui.layout import setup_home
from src.utils.formatting import fmt_int, fmt_pct

# a home: carrega os dados (sem filtros) e mostra o contexto do projeto e a qualidade dos dados
df, report = setup_home()

# titulo e as 3 perguntas que o painel responde pro ceo
st.title("🛵 Inteligência de Entregas")
st.caption(f"{APP_TITLE} · painel executivo para decidir onde agir na operação de delivery · v{VERSION}")

st.markdown(
    """
Este painel responde, para a diretoria, **três perguntas**:

1. **Quanto tempo o cliente realmente espera** (preparo + entrega) e quantas entregas fogem do prazo?
2. **O que mais pesa** nesse tempo: trânsito, clima, distância, carga do entregador ou a cozinha?
3. **Onde agir primeiro**, e quanto cada ação vale em minutos?

Cada página termina em **insights calculados sobre os filtros atuais**: achados, oportunidades com ganho
estimado, riscos e ressalvas de leitura.
"""
)

st.divider()
# bloco de qualidade dos dados: o funil de limpeza fica aqui, bem transparente
st.header("📋 Qualidade dos dados")
st.caption(f"Fonte: `{report.source}` (base pública `{DATA_NAME}`). Todo o tratamento é auditável abaixo.")

# 4 numeros principais: bruto, analisado, aproveitamento e % sem localizacao valida
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros originais", fmt_int(report.raw_rows))
c2.metric("Pedidos analisados", fmt_int(report.final_rows), help="Após remover duplicados, incompletos e valores impossíveis.")
c3.metric("Aproveitamento", fmt_pct(report.retention))
c4.metric("Sem localização válida", fmt_pct(report.invalid_location_share),
          help="Coordenadas zeradas ou fora da Índia. O pedido é mantido, mas sem distância e fora do mapa/restaurantes.")

# o funil etapa por etapa, mais as correcoes que nao tiraram nenhuma linha
with st.expander("Ver o funil de tratamento, etapa por etapa", expanded=False):
    import pandas as pd

    steps = pd.DataFrame(report.steps).rename(columns={
        "label": "Etapa", "removed": "Linhas removidas", "remaining": "Linhas restantes", "detail": "Observação"})
    show_table(steps)
    st.markdown(
        f"""
**Correções feitas sem perder linhas**

- {fmt_int(report.coords_sign_fixed)} pedidos tinham coordenada com **sinal invertido** (a Índia fica no hemisfério Norte/Leste); corrigidos.
- {fmt_int(report.invalid_location_rows)} pedidos têm localização inválida (coordenada zerada ou fora da Índia): mantidos, com distância ausente.
- {fmt_int(report.festival_unknown)} pedidos sem informação de festival: mantidos, e excluídos só da comparação de festivais.
- Textos padronizados (espaços, `NaN `, prefixo `conditions `, `Metropolitian` → `Metropolitan`) e tempos convertidos para minutos.
"""
    )

st.divider()
# guia de navegacao entre as paginas
st.header("🧭 Como navegar")
with card():
    st.markdown(
        """
| Página | Pergunta que responde |
|---|---|
| **Visão Executiva** | Qual o tempo real de espera, quantos atrasam e qual é a maior alavanca de ganho? |
| **Operação** | Quando e onde a demanda se concentra, e quando a entrega piora? |
| **Fatores Externos** | Quanto custam trânsito, clima e festivais, isolando um do outro? |
| **Entregadores** | Quem foge do esperado para o seu contexto, e quanto isso vale? |
| **Restaurantes** | A cozinha é um gargalo? A demanda depende de poucos parceiros? |
| **Experiência do Cliente** | O que está associado a notas menores? |
"""
    )

st.markdown(
    """
**Filtros** (barra lateral, valem para todas as páginas): período, trânsito, clima e **prazo (SLA)** da entrega.
O prazo é ajustável porque a pergunta "o que é atraso?" é uma decisão de negócio.
"""
)

st.divider()
# avisos de leitura: ic, associacao x causalidade, proxy de restaurante, preparo com poucos valores e base didatica
st.header("⚠️ Como ler os números")
st.markdown(
    """
- **Tempo de entrega** é o tempo da retirada até o cliente. **Tempo total** = preparo + entrega.
- **Médias vêm com intervalo de confiança de 95%** (barras de erro). Diferenças dentro da barra não são conclusões.
- **Efeitos isolados** vêm de uma regressão linear (erros robustos HC1): descrevem **associação**, não causalidade.
- **Restaurante** é um ID aproximado (cidade + coordenada), pois a base não tem identificador.
- **O tempo de preparo é registrado em poucos valores** (5, 10 e 15 min na base original): é um limite de resolução da fonte. Diferenças entre restaurantes ficam achatadas, e o painel avisa disso na página Restaurantes.
- A base é pública e de uso didático: padrões muito regulares podem refletir a origem dos dados, então as conclusões demonstram o método e não devem ser extrapoladas para uma operação real.
"""
)

st.divider()
st.caption("Python · pandas · NumPy · Plotly · Streamlit")
