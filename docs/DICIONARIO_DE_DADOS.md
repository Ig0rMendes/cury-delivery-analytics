# Dicionário de dados

Fonte: base pública **`train`** (`data/train.csv`), com 20 colunas por pedido. A tabela abaixo mostra como cada coluna
bruta vira uma coluna limpa, e quais colunas são derivadas pelo projeto.

## 1. Colunas originais → colunas limpas

| Coluna original (`train`) | Coluna limpa | Tipo final | Tratamento |
|---|---|---|---|
| `ID` | `order_id` | texto | Chave do pedido; duplicados removidos (fica o primeiro). |
| `Delivery_person_ID` | `courier_id` | texto | Maiúsculas. Contém o código da cidade (ver `city`). |
| `Delivery_person_Age` | `courier_age` | inteiro | Válido entre 18 e 60 anos; fora disso a linha é removida. |
| `Delivery_person_Ratings` | `rating` | decimal | Escala 1 a 5; fora disso a linha é removida. |
| `Restaurant_latitude` / `Restaurant_longitude` | `rest_lat` / `rest_lon` | decimal | Valor absoluto (sinal invertido corrigido). Zero ou fora da Índia = localização inválida. |
| `Delivery_location_latitude` / `Delivery_location_longitude` | `dest_lat` / `dest_lon` | decimal | Mesmo tratamento. |
| `Order_Date` | `order_date` | data | Formato `dd-mm-aaaa`. |
| `Time_Orderd` | `time_ordered` → `order_hour`, `order_datetime` | hora | Hora do pedido (a coluna original tem esse erro de grafia). |
| `Time_Order_picked` | usada para `prep_time_min` | hora | Retirada pelo entregador. |
| `Weatherconditions` | `weather` | categoria | Remove o prefixo `conditions `. Valores: Sunny, Cloudy, Fog, Stormy, Sandstorms, Windy. |
| `Road_traffic_density` | `traffic` | categoria | Remove espaços. Valores: Low, Medium, High, Jam. |
| `Vehicle_condition` | `vehicle_condition` | inteiro 0–3 | Escala sem sentido documentado na base. |
| `Type_of_order` | `order_type` | categoria | Snack, Meal, Drinks, Buffet. |
| `Type_of_vehicle` | `vehicle_type` | categoria | motorcycle, scooter, electric_scooter, bicycle. |
| `multiple_deliveries` | `multiple_deliveries` | inteiro 0–3 | Entregas simultâneas do entregador. |
| `Festival` | `festival` | Yes / No / ausente | Ausente é **mantido** e excluído só da comparação de festivais. |
| `City` | `area_type` | categoria | **Tipo de área** (Metropolitan, Urban, Semi-Urban), não cidade. Corrige `Metropolitian`. |
| `Time_taken(min)` | `delivery_time_min` | inteiro | Remove o prefixo `(min) `. Válido entre 1 e 180. |

Textos `NaN `, `nan`, `None`, vazio e variações viram ausência real antes de qualquer contagem.

## 2. Colunas derivadas

| Coluna | Definição |
|---|---|
| `prep_time_min` | Retirada − pedido, em minutos, com módulo de 24 h (pedidos próximos da meia-noite). Válido entre 0 e 90. **Atenção:** na base original assume poucos valores (5, 10 e 15 min); é um limite de resolução da fonte. |
| `total_time_min` | `prep_time_min + delivery_time_min`. Premissa confirmada: o tempo de entrega **não** inclui o preparo. |
| `order_hour` | Hora cheia do pedido (0–23). |
| `order_datetime` | Data + hora do pedido. |
| `weekday_num`, `weekday` | Dia da semana (0 = segunda; rótulos Seg…Dom). |
| `daypart` | Manhã (6–10 h), Almoço (11–14 h), Tarde (15–17 h), Jantar (18–21 h), Noite (22–5 h). |
| `age_band` | 18–24, 25–29, 30–34, 35–39, 40+. |
| `time_band` | Até 20 min, 21–30 min, 31–40 min, Mais de 40 min (tempo de entrega). |
| `city_code`, `city` | Código e nome da cidade extraídos do `courier_id` (padrão `CIDADE` + `RES` + nn + `DEL` + nn), com mapa em `src/config.py`. Código desconhecido mantém o próprio código; sem padrão = `Outras`. |
| `has_valid_location` | Verdadeiro se as quatro coordenadas são diferentes de zero e estão na caixa da Índia (lat 6–37,5; lon 68–98). |
| `coords_fixed` | Verdadeiro se alguma coordenada chegou com sinal negativo. |
| `distance_km` | Distância em linha reta (haversine) restaurante → cliente. Ausente se a localização é inválida ou passa de 50 km. |
| `speed_kmh` | `distance_km / (delivery_time_min / 60)`; ausente acima de 80 km/h. |
| `restaurant_id` | **Proxy**: `cidade-código` + número sequencial por coordenada única (4 casas). A base não traz ID de restaurante. Ausente se a localização é inválida. |

## 3. Colunas calculadas nas análises (não persistidas)

| Nome | Onde | Significado |
|---|---|---|
| `expected_time_min` | Entregadores | Tempo previsto pelo modelo de regressão para o contexto daquele pedido. |
| `excess_min` | Entregadores | `delivery_time_min − expected_time_min`. Positivo = mais lento que o esperado. |
| `late` | Todas | Entrega acima do prazo (SLA) escolhido na barra lateral. |
