# DASHBOARD (página inicial)

Aba nativa de `index.html` (`app-tab-dashboard`), criada em **01/08/2026**. É a **página inicial**: `irParaPrimeiraAbaPermitida()` chama `switchGrupo('dashboard')` logo após o login.

## Permissão — regra própria

O **DASHBOARD não é permissionável**: não está no `ABAS_CATALOGO`, não aparece na tela de gestão de usuários e todo usuário logado o vê. O que respeita permissão é o **conteúdo**:

- o seletor de empresa (`dashEmpresasPermitidas()`) só oferece MC MOTO se `podeGrupo('mcmoto')` e RHS/SEVEN se `podeGrupo('rhsseven')`;
- na SEVEN, `dashDados()` soma **apenas as unidades liberadas** para o usuário (`unidadesPermitidas()`).

`switchGrupo('dashboard')` também **não pede senha de grupo** — é o único grupo assim.

## Fonte de dados

`const DASHBOARD_DB` em `index.html`, gerado por `gerar_dashboard.py` (rotina diária, passo **B2d**, depois de A3 e B2 para bater com as demais abas). Consulta os **dois** bancos. Estrutura:

```js
{ geradoEm, hoje,
  mc:    { pagar:{"YYYY-MM-DD":saldo}, diario:{"YYYY-MM-DD":[venda,custo,QC,itens,pedidos]},
           mensal:{"YYYY-MM":[...]}, estoque, centros:{cod:nome}, fixo:{"YYYY-MM":{cod:valor}} },
  seven: { unidades:{ "3":{…mesmo formato…}, "4":{…}, "5":{…} }, centros:{cod:nome} } }
```

Série **diária de 120 dias** (cobre a semana corrente) e **mensal de 24 meses** (histórico). Todo o cálculo é feito no navegador — trocar de empresa, de mês ou de centros de custo não precisa de novo acesso ao banco.

**As regras de venda/custo são as mesmas das outras telas** (senão o dashboard divergiria): MC MOTO líquida de devolução pela tabela `devolucoes` (regra do Painel Mensal); SEVEN por `VPED_PEDIDO_HISTORICO` líquida de `'DC'`, **já com a regra dos 60%** nas unidades 3 e 4. Conferido: o CMV da SEVEN bate com o da aba Recebimentos **até o centavo**.

## Layout — tela de gráficos (01/08/2026)

A tela foi refeita no estilo BI: **faixa escura de KPIs** no topo (vendas do mês, realização da meta, variação vs. mês anterior, margem de contribuição, QC/pedidos/ticket e estoque/giro) e, abaixo, uma **grade de gráficos**. Todos os gráficos são **SVG inline**, escritos à mão em `charts` dentro do próprio `index.html` — sem biblioteca externa, então não há nada para carregar nem conflito de CSP.

| Gráfico | Tipo | Conteúdo |
|---|---|---|
| Vendas por mês × meta | barras + linha | 12 meses; barra verde quando bate a meta, mês selecionado em escuro; linha laranja = meta |
| Venda dia a dia | linha com área | dias do mês selecionado (série diária cobre 120 dias) |
| Para onde vai a venda | rosca | CMV + custo fixo + sobra |
| Venda por grupo de produto | barras horizontais | top 8, com a margem % de cada grupo |
| Venda por vendedor | barras horizontais | top 8, com margem % |
| Top marcas / fornecedores | barras horizontais | top 8, com margem % |
| Venda por unidade de negócio | barras horizontais | **só na SEVEN**; respeita as unidades permitidas |
| Contas a pagar | barras horizontais | vencido + próximas 5 semanas |
| Custo fixo por centro de custo | barras horizontais | top 8 dos centros marcados |
| Mês a mês | tabela | 12 meses com vendas, QC, pedidos, ticket, MC, MC%, custo fixo, **sobra** e realização, com cor condicional |

Entre a faixa de KPIs e os gráficos há a **faixa de indicadores** (`renderIndicadores()`, `#dash-indicadores`), em 4 blocos — Contas a pagar · Vendas · Atendimento · Rentabilidade e estoque. Ela existe porque a migração para gráficos **derrubou o número explícito de 17 dos 22 indicadores** da versão em cards (e deixou o giro ideal sem onde ser editado); a faixa devolve todos, cada um com o histórico de 12 meses ao lado. **Ao mexer no layout, conferir que esses 22 continuam na tela.**

As quebras (grupo / marca / vendedor) vêm do gerador em `quebras: {grupo|marca|vendedor: {"YYYY-MM": {chave: [venda, custo]}}}`, cobrindo **13 meses** (`MESES_QUEBRA`) — não os 24, porque são consultas pesadas. Na SEVEN, `dashDados()` soma as quebras **chave a chave** entre as unidades permitidas.

⚠️ **Marca da MC MOTO:** `produtos.MARCA` é **código**; o nome está em `marcas.DESCRICAO`. Sem esse join o gráfico sai com "000019", "000015".

⚠️ O grupo de produto da MC MOTO usa `produtos.GRUPO` → `grupos.DESCRICAO` **sem** a reclassificação por palavra-chave que o Mapa de Vendas faz em `DIVERSOS` (ver [`02-vendas.md`](02-vendas.md)). Por isso "DIVERSOS" aparece grande aqui e menor lá.

## Indicadores da faixa (os mesmos da versão em cards)

| Bloco | Cards |
|---|---|
| **Contas a pagar** | Vence hoje · Vence nesta semana (seg–dom) · Vence neste mês · Já vencido |
| **Vendas** | Vendas do mês vs meta (com barra) · Vendas da semana · Venda média por dia útil · Projeção do mês |
| **Atendimento** | QC (clientes atendidos) · Pedidos · Ticket médio · Ticket por cliente · Itens vendidos · Itens por cliente |
| **Rentabilidade** | Margem de contribuição · Margem % · CMV do mês (e % da venda) · CMV 12 meses |
| **Estoque e custo fixo** | Estoque a custo · Giro de estoque vs ideal (e cobertura em meses) · Custo fixo do mês (e do anterior) · Custo fixo médio (e % da venda) |

Quase todo card traz o **histórico de 12 meses fechados** ao lado do valor do mês — era o pedido de "ticket médio histórico", "margem histórica", "CMV histórico" e "custo fixo histórico".

## QC (clientes atendidos) × Pedidos — não são a mesma coisa

Decisão do usuário em **01/08/2026**: `QC` = **clientes atendidos**; a quantidade de vendas é um card separado (**Pedidos**).

⚠️ **`COUNT(DISTINCT cliente)` puro daria um número errado.** O balcão inteiro é lançado num **cliente genérico** — `000001 CLIENTE CONSUMIDOR` na MC MOTO e `31161 CONSUMIDOR FINAL` na SEVEN. Em jul/2026 a MC MOTO teve **2.734 vendas mas só 126 códigos de cliente distintos**, porque 2.510 delas caíram nesse código único. A regra usada:

```
QC = clientes identificados distintos  +  1 por venda no cliente genérico
```

...porque cada venda de balcão é uma pessoa diferente, mesmo o ERP usando um código só. Resultado jul/2026: **QC 2.635 × 2.734 pedidos** (MC MOTO) e **QC 534 × 1.232 pedidos** (SEVEN). Os genéricos são descobertos por nome (`LIKE '%CONSUMIDOR%'`), não por código fixo.

**QC é consultado por período, nunca somado.** Um cliente que compra 3× no mês conta 1 no mês e 1 em cada dia — por isso o gerador roda a consulta separadamente para a série diária e a mensal. *(Ressalva: na SEVEN o QC das unidades é somado, então um cliente que compra em duas unidades conta duas vezes no consolidado.)*

Daí saem **dois tickets diferentes**: `Ticket médio` = venda ÷ **pedidos** (valor de cada venda) e `Ticket por cliente` = venda ÷ **QC** (quanto cada cliente gastou). Na SEVEN a diferença é grande — R$ 265,40 contra R$ 612,32 —, porque lá o mesmo cliente de atacado faz vários pedidos no mês.

## Margem de contribuição — deduções sobre a venda (01/08/2026)

Segue a **mesma regra do Painel Mensal**:

```
MC = Vendas × (1 − deduções%) − CMV
```

O Mapa usa **um** percentual global (`localStorage['mapa_descontoPct']`, campo "% Desconto (para cálculo da MC)"). No dashboard esse percentual é **aberto em quatro componentes** — **impostos, comissão, prêmio e frete de venda** — editáveis no botão **"% Deduções"**; o que entra na conta é a **soma** deles (`dash_deducoes`).

- **Enquanto os quatro não forem preenchidos, o dashboard herda o percentual do Mapa** (`dashDeducoes().herdado`), para as duas telas não divergirem no primeiro acesso. O botão "Herdar do Mapa" volta a esse estado.
- A regra vale em **todos** os lugares onde aparece margem: faixa de KPIs, gráficos de grupo/vendedor/marca, tabela mensal (MC, MC% e a coluna **Sobra** = `venda × (1 − ded) − CMV − custo fixo`) e a rosca "Para onde vai a venda", onde as deduções viraram **fatia própria**.
- Helpers: `dashDeducoes()`, `dashVendaLiq(v)` e `dashMC(v,custo)` — usar sempre esses, nunca `venda − custo` cru.

Exemplo (MC MOTO, jul/2026): sem deduções a MC é R$ 92.888,97 (38,0%); com 10% de imposto + 2% de comissão + 1% de prêmio + 1% de frete (14%), cai para **R$ 58.632,25 (24,0%)** e a sobra do mês vira **negativa em R$ 31.070,19**.

## Filtro de unidade de negócio (03/08/2026)

Ao lado do seletor de empresa, na faixa escura, há botões de **unidade** (multi-seleção) que valem para **a tela inteira** — KPIs, faixa de indicadores, todos os gráficos e a tabela mensal. `dashUnidades()` devolve as unidades em foco e `dashDados()` agrega só elas.

- **Só aparece na SEVEN** (a MC MOTO não tem unidades) e **só com 2+ unidades permitidas**.
- **Sempre intersectado com `unidadesPermitidas()`** — o filtro nunca amplia acesso. O usuário "RHS/SEVEN CONTAGEM", restrito às unidades 3 e 4, só recebe esses dois botões.
- **Nunca fica sem nenhuma** unidade marcada (desmarcar a última é ignorado).
- Persistido em `dash_unidades`; o recorte ativo aparece no cabeçalho e no rodapé (`rotuloDashUnidades()`).

Conferência (jul/2026): todas R$ 326.976,62 · só Ipatinga R$ 206.322,67 · Contagem+Ipatinga R$ 319.235,86 — a diferença de R$ 7.740,76 é exatamente Ultra Motos.

## Parâmetros e regras

- **Contas a pagar sempre olham HOJE**, independentemente do seletor de mês. Só títulos **em aberto**, pelo saldo devedor.
- **Meta do mês:** soma das metas por vendedor do Painel Mensal (`localStorage`, chaves `mapa_meta_<vendedor>_vendas`) — mesma origem, então o `index.html` lê direto. A **SEVEN não tem meta por vendedor**, então ali a meta é digitada (`dash_meta_seven`).
- **Dias úteis:** mesma regra do Painel Mensal — exclui domingos e os feriados de `localStorage['mapa_feriados']` (uma data ISO por linha); "decorridos" vai **até ontem**, porque o dia corrente pode estar incompleto.
- **Giro de estoque** = CMV dos últimos 12 meses ÷ estoque atual (vezes/ano). O **ideal é editável** (`dash_giro_ideal`, padrão 4×). Mostra também a cobertura em meses (12 ÷ giro).
- **Custo fixo:** vem do **centro de custo**, e o usuário escolhe quais entram (⚙️, `dash_centros_fixo` por empresa). O padrão desmarca o que casa com `DASH_CENTRO_FORA` — fornecedor/mercadoria, empréstimo, financiamento, transferência, cartão, caixa, imobilizado etc. Fontes: `contas_pagar.CENTRO` → `centro_custos` (MC MOTO, 2.741 de 2.742 títulos têm centro) e `TPAG_ABERTO_CCUSTO` → `TTES_CENTRO_CUSTO` (SEVEN; apesar do nome, o rateio cobre também títulos baixados — 5.839 dos 7.776).
- **Seletor de mês:** o padrão é o mês corrente, mas **se ele ainda não tiver venda cai no último mês com movimento** (`dashMesRef()`) — senão, no dia 1º, a tela abriria toda zerada. O histórico comparado é sempre dos meses anteriores ao mês selecionado.

## Chaves de `localStorage`

`dash_empresa` · `dash_centros_fixo` · `dash_giro_ideal` · `dash_meta_seven` · `dash_deducoes` · `dash_unidades`. Lê (sem escrever) `mapa_meta_*_vendas`, `mapa_feriados` e `mapa_descontoPct`, do Mapa de Vendas.
