# Metodologia

Este documento explica **por que** cada métrica existe e como os insights são calculados, para que qualquer pessoa possa
auditar o raciocínio.

## 1. Métricas escolhidas e por quê

| Métrica | Definição | Por que importa |
|---|---|---|
| **Espera total** | preparo + entrega | É o que o cliente sente. Medir só a entrega esconde a cozinha. |
| **% no prazo** | entregas com `delivery_time_min ≤ SLA` | Indicador de promessa cumprida. O SLA é um controle da barra lateral porque "o que é atraso" é decisão de negócio. |
| **P90 da entrega** | percentil 90 | A média esconde a cauda; 1 em 10 clientes vive o P90. |
| **Minutos perdidos / ganho potencial** | veja seção 4 | Converte diferenças em "quanto a média cairia", permitindo priorizar ações. |
| **Excesso vs. esperado** | realizado − previsto pelo modelo | Compara entregadores no mesmo contexto (distância, trânsito, clima, carga). |
| **Concentração (Pareto)** | % dos pedidos nos 20% maiores restaurantes | Mede dependência de poucos parceiros. |
| **Nota média e cauda < 4,0** | média e proporção | A média é alta e estável; o risco está na cauda. |

## 2. Estatística usada

- **Intervalo de confiança de 95%** da média: `média ± 1,96 · desvio / √n`. Todo gráfico de barras de tempo traz o intervalo.
- **Comparação de dois grupos** (teste de Welch): diferença de médias, erro-padrão `√(s₁²/n₁ + s₂²/n₂)` e p-valor pela
  aproximação normal. Considera-se "diferença clara" com p < 0,05. Textos de insight só afirmam efeitos quando há diferença
  clara **e** relevante (geralmente ≥ 1 minuto).
- **Correlação de Spearman**: correlação de Pearson dos postos; robusta a valores extremos e não exige linearidade.
- **Regressão linear (OLS) com erros-padrão robustos HC1**: estima o efeito de cada fator **mantendo os demais constantes**.
  - Variável-alvo: `delivery_time_min`.
  - Categóricas (referência): trânsito (Low), clima (Sunny), festival (No), veículo e tipo de área (mais frequentes).
  - Numéricas: distância (efeito reportado a cada +5 km), entregas simultâneas (+1), idade (+10 anos), condição do veículo (+1).
  - Níveis com menos de 30 pedidos são descartados. Se a amostra for pequena (< 200), o modelo não é ajustado.
  - É **associação**, não causalidade: fatores omitidos (rota, cozinha, demanda local) podem estar correlacionados.

## 3. Modelo de "tempo esperado" para entregadores

Ranquear entregadores pelo tempo bruto é injusto: quem pega rotas longas ou trânsito pesado parece pior. O projeto ajusta, na
**base completa** (estável, independe dos filtros), uma versão **estendida** do modelo acima: trânsito e clima entram
**combinados** (na base real o efeito de um depende do outro) e o período do dia também entra (para não confundir turno de
pico com desempenho individual). Para cada pedido, `excesso = realizado − esperado`. Por entregador:

- `excesso médio` e `erro-padrão = desvio do excesso / √n`;
- classe **"Mais lento/rápido que o esperado"** apenas se `|excesso| > max(3 · erro-padrão, 1 min)`: diferença clara
  **e** com relevância prática; caso contrário, "Dentro do esperado";
- só entram entregadores com o mínimo de pedidos escolhido (padrão: 20).

**Por que 3 erros-padrão e não 1,96?** Com centenas de entregadores, o limiar clássico (1,96) aponta cerca de 2,5% de cada ponta
**por puro acaso**; com 3, cerca de 0,1%. Os insights comparam o número de apontados com o que o acaso explicaria e, se for
quase igual, dizem que o desempenho individual é homogêneo e que o ganho está no contexto, não nas pessoas.

## 3.1 Comparações que precisam "igualar o contexto"

Um período do dia pode parecer "gargalo de capacidade" só porque coincide com trânsito pesado. Por isso o insight do pico
compara a diferença **dentro de cada nível de trânsito** (diferença estratificada, ponderada pelo tamanho do grupo) e só fala em
capacidade se a diferença persistir. O mesmo cálculo qualifica o efeito das entregas simultâneas.

O efeito do **festival** é mostrado em duas leituras: a diferença **bruta** de médias (festival x dia normal) e o efeito
**isolado** da regressão, que mantém trânsito, clima e demais fatores iguais. Na base real a diferença bruta é bem maior que a
isolada, porque dias de festival trazem trânsito pesado junto.

## 4. Dimensionamento de oportunidades

Para cada segmento *S* (ex.: "Trânsito: Congestionado") comparado ao restante da base *R*:

```
diferença        = média(S) − média(R)
extra_minutos    = diferença · n(S)
ganho_potencial  = max(diferença, 0) · n(S) / n(total)      # queda da média geral se S operasse como R
parcela_atrasos  = atrasos(S) / atrasos(total)
```

A varredura cobre trânsito, clima, tipo de área, entregas simultâneas, veículo, período do dia, festival e cidade. Segmentos que
são **a maioria** dos pedidos (mais de 50%) não entram como alavanca: comparar "maioria x resto" não indica onde agir. O painel
mostra a maior alavanca geral e a maior **sob gestão direta** (entregas simultâneas 2+, veículo, cidade), porque trânsito e clima
não se controlam. O **período do dia** aparece na tabela de segmentos, mas **não é candidato a alavanca**: coincide com trânsito
pesado (veja 3.1), e apontá-lo levaria a contratar sem resolver a causa.

Para entregadores, o ganho é a soma dos excessos dos "mais lentos que o esperado" dividida pelo total de pedidos.

## 5. Restaurantes

A base não tem identificador. O ID é um **proxy** (cidade + coordenada com 4 casas decimais ≈ 11 m). Limitações: dois
restaurantes no mesmo ponto viram um; o mesmo restaurante com coordenadas ligeiramente diferentes vira dois. Pedidos com
localização inválida ficam fora da página. "Preparo lento" = média de preparo acima da média da rede por mais que
`max(3 · erro-padrão, 1 min)`; se o ganho de corrigir os apontados for desprezível (< 0,05 min), o insight diz que o preparo é uniforme na rede.

### 5.1 Limite de resolução do tempo de preparo

Na base, o preparo (`Time_Order_picked − Time_Orderd`) assume só alguns valores (5, 10 e 15 min na base original), porque os
horários não vêm com resolução de minutos. Consequências: (i) a média por restaurante varia pouco, (ii) o desvio-padrão dentro de
cada restaurante é grande frente ao desvio entre restaurantes, e (iii) o resultado "preparo uniforme na rede" reflete a
resolução da fonte e não prova que as cozinhas são iguais. O painel detecta o padrão (`prep_granularity`: no máximo 6 valores
distintos) e exibe uma nota na página Restaurantes e um insight informativo. Para gerir cozinhas de verdade, é preciso registrar
horários em minutos exatos.

## 6. Nota (avaliação)

O painel testa se a nota **varia entre pedidos do mesmo entregador**. Se ≥ 90% dos entregadores com 2+ pedidos têm nota única,
a nota é tratada como **atributo do entregador** (média histórica), não como reação do cliente a cada entrega, e os insights
da página trazem essa ressalva. A faixa de tempo de entrega fica de fora do ranking de "dimensões que separam a nota": ela é o
próprio atraso, não uma causa independente. O custo do atraso é expresso na nota média geral (`parcela de atrasos × diferença de nota`).

## 7. Decisões de tratamento (e alternativas descartadas)

| Decisão | Motivo |
|---|---|
| Corrigir o sinal das coordenadas (`abs`) | A Índia está no hemisfério Norte/Leste; sinal negativo é erro de registro. |
| Manter pedidos com localização inválida, sem distância | O pedido tem tempo, nota e contexto válidos; só a geografia é inutilizável. Calcular distância a partir de (0, 0) geraria valores absurdos. |
| Remover linhas com campos essenciais ausentes | Imputar trânsito/clima/idade distorceria justamente os efeitos que o painel mede. O funil mostra quanto foi removido. |
| Não imputar festival ausente | Preferível excluir da comparação a assumir "não". |
| Limite de 50 km e 80 km/h | Barreira de sanidade para coordenadas quebradas; não corta dados normais da base. |
| Funil auditável (`CleaningReport`) | Cada remoção tem motivo e contagem, exibidos na Home. |
