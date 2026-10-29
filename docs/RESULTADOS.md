# Resultados completos

> Gerado automaticamente a partir de `train.csv`: 45.593 registros brutos, 41.559 pedidos analisados (91,2%), prazo de entrega de 30 min, sem filtros.

**Visão Executiva**

- ⚠️ **30,5% das entregas passam de 30 min; 1 em 10 leva mais de 40 min**
  - A etapa de entrega leva 26,5 min em média (mediana 26,0 min). Somando o preparo (10,0 min), o cliente espera 36,5 min no total, e 1 em 10 espera mais de 51 min. Medir só a entrega esconde 27% da espera real.
  - *Ação sugerida:* Acompanhar o tempo TOTAL (pedido até a porta) como indicador principal, não só a entrega.
- 💡 **Maior alavanca de tempo: Trânsito: Congestionado**
  - Responde por 31,7% dos pedidos, mas por 53,5% dos atrasos. A entrega aqui é 7,1 min mais lenta que no restante da base (31,3 min contra 24,2 min). Se esse segmento operasse como o restante, a média geral cairia 2,3 min.
  - *Ação sugerida:* Ajustar roteirização e janelas de saída nos horários de trânsito pesado e escalar os entregadores mais rápidos para essas janelas.
- 💡 **Maior alavanca sob gestão direta: Entregas simultâneas: 2 simultâneas**
  - Fatores como trânsito e clima não se controlam; este sim. São 4,5% dos pedidos, 14,6 min mais lentos que o restante, o que vale 0,7 min na média geral e 14,9% dos atrasos.
  - *Ação sugerida:* Limitar entregas simultâneas por entregador e agrupar rotas por proximidade.
- 💡 **O preparo é 27% da espera do cliente**
  - Enquanto a logística concentra atenção na entrega, a cozinha consome 10,0 min por pedido. Para o cliente, 2 min a menos de preparo valem o mesmo que 2 min a menos de entrega.
  - *Ação sugerida:* Definir metas de preparo para a rede e, antes de cobrar restaurantes individualmente, registrar horários em minutos exatos: a base atual só tem poucos valores de preparo (veja a nota na página Restaurantes).
- 🔎 **Últimos 7 dias da base: tempo de entrega ficou estável (+0,8 min) com volume -2%**
  - Semana mais recente: 26,7 min em 6.692 pedidos; semana anterior: 26,0 min em 6.832.

**Operação**

- 🔎 **O pico é mais lento (+6,9 min), mas o motivo é o trânsito, não falta de entregador**
  - No pico (19h, 20h, 21h, 32% dos pedidos) a entrega leva 31,2 min contra 24,3 min fora dele (+6,9 min). 97% dos pedidos do pico pegam trânsito alto ou congestionado, contra 16% fora dele. Igualando o trânsito, a diferença cai para -0,2 min.
  - *Ação sugerida:* Contratar para o pico resolveria pouco; priorize roteirização e janelas de saída nos horários de trânsito pesado.
- 🔎 **A taxa de atraso vai de 2% (9h) a 51% (20h)**
  - Quase todo atraso se concentra nas horas de pior desempenho: pedidos das 20h atrasam em 51% dos casos. Use o mapa de calor para ver quais dias agravam o quadro.
  - *Ação sugerida:* Planejar escala e prazo prometido por faixa horária, começando pelas 20h.
- 💡 **5% dos pedidos saem com 2+ entregas simultâneas e levam 16,0 min a mais**
  - Tempo médio de entrega por nº de entregas simultâneas (min): 0: 23,0 → 1: 27,0 → 2: 40,5 → 3: 47,8. Com 2+ simultâneas, 100% passam do prazo, contra 27% nos demais. Igualando o trânsito, a diferença é de +13,4 min. Limitar a 1 entrega por vez tiraria cerca de 0,9 min da média geral (3,2%). É um dos poucos fatores diretamente controláveis pela operação.
  - *Ação sugerida:* Definir teto de entregas simultâneas e agrupar pedidos só quando o desvio de rota for pequeno.
- 🔎 **As cidades têm tempos de entrega praticamente iguais**
  - Entre 22 cidades, a mais lenta (Allahabad, 27,3 min) está só 1,1 min acima da mais rápida (Mumbai, 26,2 min), e as 3 maiores somam 22% dos pedidos. O problema não é local: ações por cidade teriam pouco retorno.
  - *Ação sugerida:* Tratar a operação como rede única e priorizar as alavancas globais (trânsito, entregas simultâneas).

**Fatores Externos**

- ⚠️ **Dias de festival atrasam a entrega em 19,4 min**
  - 45,5 min em festival contra 26,2 min em dias normais (IC95% da diferença: 19,1 a 19,6 min). Atinge 2,0% dos pedidos (833): pouco na média geral, mas é a maior penalidade individual da base. Mantendo trânsito, clima e demais fatores iguais, o efeito do festival é de +10,1 min (IC95%: 9,6 a 10,5): a diferença para o valor bruto vem de trânsito e clima que acompanham esses dias.
  - *Ação sugerida:* Calendário de festivais entra no planejamento de escala e na promessa de prazo.
- 🔎 **Trânsito congestionado adiciona +9,9 min (+46%) à entrega**
  - Média de 31,3 min contra 21,4 min em trânsito baixo (IC95%: 9,7 a 10,1 min). 42% dos pedidos já são feitos em trânsito alto ou congestionado, e o trânsito inteiro responde por 19% de todos os minutos de entrega.
  - *Ação sugerida:* Incluir o trânsito previsto na promessa de prazo e na distribuição de pedidos por entregador.
- 🔎 **O trânsito só pesa de verdade em certos climas: +14,4 min com neblina contra +1,7 min com ensolarado**
  - Custo do trânsito congestionado em relação ao baixo, por clima (tempo médio de entrega). Por isso as médias isoladas de trânsito e de clima subestimam a combinação ruim e superestimam as demais.
  - *Ação sugerida:* Definir o prazo prometido pela COMBINAÇÃO clima × trânsito, e não por cada fator separadamente.
- 🔎 **Isolando os demais fatores, o congestionamento soma +7,1 min; ir do pedido mais perto ao mais longe soma +6,7 min**
  - Mantendo clima, carga e veículo iguais: congestionamento +7,1 min (IC95%: 6,9 a 7,3); percorrer de 1,5 a 19,9 km (do 5º ao 95º percentil) soma +6,7 min. Trânsito e distância pesam de forma parecida. Em distância, o congestionamento equivale a 19,6 km a mais.
  - *Ação sugerida:* Considerar distância e trânsito juntos na promessa de prazo e na alocação de pedidos.
- 🔎 **Neblina é o clima mais custoso: +6,1 min por entrega, em média**
  - Em relação à referência (Ensolarado), com IC95% de 5,9 a 6,4 min (6.518 pedidos nesse clima). É uma média entre todos os níveis de trânsito: veja o cruzamento clima × trânsito.
  - *Ação sugerida:* Ativar prazo dinâmico por clima apenas para os climas com efeito claro.
- 💡 **Fator categórico de maior peso: Trânsito: Congestionado (+2,3 min na média geral)**
  - Efeito isolado de +7,1 min em 31,9% dos pedidos. Entre 17 termos testados (R² = 0,54, 38.064 pedidos), é o que mais empurra a média para cima. O modelo mede associação, não causalidade.
- ℹ️ **Efeito grande, mas raro: Tipo de área: Semiurbana (+10,2 min em 0,4% dos pedidos)**
  - São 138 pedidos: dói para quem recebe, mas move pouco a média geral. Trate como caso específico (cobertura, prazo diferenciado), não como prioridade da operação.
- 🔎 **Pior combinação: neblina + trânsito congestionado (36,9 min)**
  - A melhor combinação (ensolarado + trânsito médio) leva 20,4 min, uma diferença de 16,5 min. A pior tem 2.306 pedidos na base filtrada.

**Entregadores**

- 🔎 **Desempenho individual é homogêneo: quase ninguém foge do esperado para o contexto**
  - Entre 720 entregadores, só 3 diferem de forma clara (mais de 3 erros-padrão e 1 min); por puro acaso esperaríamos cerca de 2. Os 10% melhores e os 10% piores ficam entre -1,3 e +1,2 min do esperado. O 'esperado' já desconta trânsito, clima, período, carga, idade e condição do veículo: o que sobra é o desempenho próprio de cada pessoa.
  - *Ação sugerida:* Não gastar energia em ranking individual; atuar nos fatores de contexto (carga simultânea, rotas, trânsito).
- ℹ️ **Mais pedidos anda junto com um leve atraso, mas o efeito é pequeno (0,2 min)**
  - Há correlação (Spearman 0,23), mas os 10% mais ocupados, que fazem 18% dos pedidos, ficam em média só 0,2 min mais lentos que os demais (contra o esperado). Não justifica mexer na distribuição de volume.
- 🔎 **Idade: cada 10 anos a mais está associado a +4,3 min na entrega, com o resto igual**
  - Efeito isolado de +4,3 min (IC95%: 4,2 a 4,4). Pode refletir veículo, jornada ou treino que acompanham a idade.
  - *Ação sugerida:* Investigar a causa (carga, veículo, treinamento) e nunca usar idade como critério individual de contratação ou alocação.
- ℹ️ **O tipo de veículo não muda o tempo de entrega de forma clara**
  - Após isolar distância e contexto, nenhum veículo difere do de referência com segurança.
- 🔎 **Condição do veículo: +1 nível está associado a -2,3 min na entrega**
  - IC95%: -2,4 a -2,2. A base não documenta o sentido da escala (0–3); confirme com a fonte antes de agir.
  - *Ação sugerida:* Se a escala indicar que nível maior é melhor estado, priorizar a renovação dos veículos de nível baixo.
- ℹ️ **Cuidado com amostras pequenas por entregador**
  - A mediana é de 50 pedidos por entregador. Com poucos pedidos, o desempenho oscila ao acaso; por isso a classificação exige diferença de mais de 3 erros-padrão E de pelo menos 1 minuto.

**Restaurantes**

- ℹ️ **Restaurantes identificados por proxy em 92% dos pedidos**
  - A base não traz ID de restaurante: ele é aproximado por cidade + coordenada. Pedidos com localização inválida (coordenadas zeradas ou fora da Índia) ficam fora desta página, mas contam nas demais. Se dois restaurantes compartilham o mesmo ponto, aparecem como um só.
- ℹ️ **Limite da base: o preparo só aparece em 3 valores (5 min (34%), 10 min (33%) e 15 min (33%))**
  - O registro de horário da fonte não tem resolução de minutos, então diferenças entre restaurantes ficam achatadas. Resultados como 'preparo uniforme na rede' refletem essa resolução e não devem ser lidos como prova de que as cozinhas são iguais.
  - *Ação sugerida:* Se o objetivo é gerir a cozinha, passar a registrar horários de preparo em minutos exatos.
- 🔎 **Demanda pulverizada: 20% dos restaurantes fazem 31% dos pedidos**
  - São 388 restaurantes; uma distribuição uniforme daria 20%. Não há dependência relevante de poucos parceiros, mas também não há 'grandes contas' para negociar prazo.
  - *Ação sugerida:* Padronizar metas de preparo para toda a rede, em vez de tratar por exceção.
- 🔎 **Preparo médio de 10,0 min: 27% da espera total do cliente**
  - Mediana de 10,0 min; 9 em 10 pedidos levam até 15 min. Esta etapa não aparece em métricas de entrega, mas pesa na experiência.
- 🔎 **Poucos restaurantes preparam mais devagar, e o ganho de corrigi-los é irrelevante**
  - 1 restaurante fica claramente acima da média; mesmo trazendo ele para a média, o preparo geral cairia só 0,00 min. O preparo é, na prática, uniforme na rede.
  - *Ação sugerida:* Não abrir frentes por restaurante; se quiser reduzir a espera, mude o padrão da rede inteira.
- ℹ️ **O tipo de pedido não altera o preparo de forma relevante**
  - Não use o tipo de pedido para prometer prazos diferentes.
- 🔎 **Preparo lento não é compensado nem agravado na entrega**
  - A correlação entre preparo e entrega é de -0,01: são etapas independentes. Reduzir um não resolve o outro; o tempo total é a soma das duas.
  - *Ação sugerida:* Atacar as duas etapas com metas separadas.

**Experiência do Cliente**

- ℹ️ **A nota varia entre pedidos do mesmo entregador: é avaliação de cada entrega**
  - Nenhum entregador com 2+ pedidos tem nota única. Isso permite ligar a nota à experiência de cada entrega (tempo, trânsito, clima), e não só ao perfil do entregador.
- 🔎 **Nota média 4,63: 81% dos pedidos com 4,5 ou mais e 3% abaixo de 4,0**
  - O patamar de partida é alto. O que interessa operacionalmente é a cauda abaixo de 4,0, onde está o risco de perda de cliente.
- 💡 **Atrasar custa nota: -0,32 ponto**
  - Pedidos acima de 30 min têm nota 4,41 contra 4,73 no prazo (-0,32; IC95%: -0,32 a -0,31). Como 30% das entregas atrasam, os atrasos custam 0,10 ponto na nota média geral. Todas as notas abaixo de 4,0 vêm de entregas atrasadas, que são 30% do total (padrão muito regular, típico de base pública).
  - *Ação sugerida:* Tratar o cumprimento do prazo como alavanca direta de satisfação.
- 🔎 **Correlação entre tempo de entrega e nota: -0,30 (Spearman)**
  - Quanto mais demorada a entrega, menor tende a ser a nota; é a relação mais forte desta página.
- 🔎 **Fora o tempo, a maior diferença de nota está em entregas simultâneas (0,24 ponto)**
  - 0 tem a melhor nota (4,67) e 2 a pior (4,43). Foram comparadas 10 dimensões; esta é a de maior amplitude com diferença estatisticamente clara. Parte disso pode ser o próprio efeito do tempo (ex.: trânsito pesado atrasa e, por isso, derruba a nota).
  - *Ação sugerida:* Priorizar melhorias onde a nota é menor, começando por essa dimensão.
