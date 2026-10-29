# Origem dos dados — de onde vem cada informação do painel

Este documento responde, para **cada aba publicada** em
<https://vitorsimoes-create.github.io/painel_geral/>, a pergunta *"de que tabela saiu esse
número?"*. Tudo aqui foi conferido **contra o código dos geradores em 23/10/2026** (as
consultas SQL de cada `gerar_*.py` e do `atualizar_mapa.py`), não copiado de documento antigo.

- Como e em que ordem os arquivos são gerados: [`06-pipeline-dados.md`](06-pipeline-dados.md).
- Regras de negócio e telas em detalhe: [`01-compras`](01-compras.md), [`02-vendas`](02-vendas.md),
  [`03-financeiro-mc-moto`](03-financeiro-mc-moto.md), [`04-rhs-seven`](04-rhs-seven.md),
  [`07-dashboard`](07-dashboard.md).

> **Regra de manutenção.** Quem mudar a consulta de um gerador, ou criar uma aba nova, atualiza
> a linha correspondente aqui **no mesmo commit**. Este arquivo só serve se estiver certo.

---

## 1. As quatro fontes

| Fonte | O que é | Atualidade | Quem lê |
|---|---|---|---|
| **`mc_moto`** (MySQL 187.127.22.30) | Banco do ERP da **MC MOTO**. Tabelas em minúsculo (`vendas`, `itens`, `produtos`…) | Cargas às 08:05, 12:05, 16:05 e 20:05, com ~1 h de defasagem | Geradores da MC MOTO, `atualizar_mapa.py`, `gerar_dashboard.py`, `gerar_relatorio.py`, `gerar_clientes.py`, `gerar_agenda_compras.py` |
| **`projeto_f7`** (mesmo servidor, usuário só-leitura) | **Espelho** do ERP Proton da SEVEN. Tabelas com prefixo (`VPED_`, `TMER_`, `TPAG_`, `TREC_`, `TENT_`, `TMOV_`, `TCLI_`, `TFOR_`…) | Carga noturna (D-1). Pode parar: o Relatório Gerencial avisa quando o espelho fica dias sem carga | Todos os geradores de RHS/SEVEN |
| **Bling da RHS** (API v3, conta 2 — RHS LOCADORA LTDA) | Fonte da **unidade 4 (Seven Contagem) a partir de 29/09/2026**. Lido só por `gerar_bling_un4.py`, que grava dois arquivos locais | Lido uma vez por dia, na rotina; relê os últimos 45 dias | `_un4.py` (adaptador) → geradores que já fazem a emenda |
| **Digitado no navegador** | Metas, saldo inicial de caixa, feriados, overrides, lançamentos manuais | Na hora, só naquele navegador (`localStorage`) — exceto o que for publicado em `parametros-painel.json` | O próprio `index.html` e as páginas em iframe |

**A conta 1 do Bling (SEVEN MOTOPECAS, banco `bling_rhs_moto`) é proibida para o painel.** O
módulo `_bling_rhs.py` confere o CNPJ da conta e aborta se não for a RHS.

### Arquivos de estado (não são fonte, mas o painel depende deles)

| Arquivo | O que guarda | Pode apagar? |
|---|---|---|
| `bling-un4.json` (versionado) | Venda e CMV da unidade 4 **dia a dia, com o custo congelado** no dia da leitura | **Nunca** — o CMV de mês fechado mudaria sozinho |
| `bling-un4-hoje.json` (local) | Foto do dia do Bling: produtos, estoque, títulos, compras, NF de entrada, contatos, vendedores, categorias | Sim, é regerado todo dia |
| `relatorio-historico.json` (versionado) | Fechamento mensal (posição de estoque, contas e itens de cada mês) | **Nunca** — é a fonte da verdade dos meses fechados |
| `monitor_fechamento\snapshot_AAAA-MM-DD.json` (local) | Foto diária dos meses fechados da MC MOTO | **Nunca** — é o que permite o comparativo do dia seguinte |
| `parametros-painel.json` (versionado) | O que o usuário digita e exporta pelo botão "Exportar parâmetros" (metas, alíquotas, classificação de fornecedor…) | Só sobrescrever com texto novo do próprio usuário |
| `_bling_forn_cache.json` (local) | Fornecedor e código no fornecedor de cada produto do Bling (uma chamada por item) | Sim; só deixa a próxima leitura mais lenta |

---

## 2. Regras que valem para todas as telas

Antes de olhar aba por aba, estas regras se repetem em quase todas as consultas. Se um número
não bate entre duas abas, comece por aqui.

| Regra | MC MOTO (`mc_moto`) | RHS/SEVEN (`projeto_f7`) | Unidade 4 a partir de 29/09 (Bling) |
|---|---|---|---|
| **Venda cancelada fica fora** | `vendas.STATUS <> '3'`; item `itens.CANCELADO <> 'S'` | `VPED_PEDIDO_HISTORICO.TPED_DATA_CANCELAMENTO IS NULL` | Só pedido na situação **Atendido (9)** |
| **Valor da venda** | `vendas.VL_TOTAL` (cabeçalho) ou `itens.VL_TOTAL` (item) | `TPED_VALOR_LIQUIDO_PEDIDO` (cabeçalho) / `TPED_VALOR_TOTAL_ITEM` (item) | `total` do pedido |
| **Devolução** | Tabela `devolucoes` (`VL_TOTAL_LIQ`, custo `QUANTIDADE × produtos.CUSTO`), abatida no **mês da venda original** | `TMOV_EXTRA` + `TMOV_EXTRA_ITEM` com `TMOV_NATUREZA_MOVIMENTACAO='DC'`, no mês do movimento | Não há — pedido cancelado sai pela situação |
| **Custo da venda (CMV)** | `itens.QUANTIDADE × itens.CUSTO` (custo carimbado no dia da venda) | `TPED_QTDE_PEDIDA × TMER_ESTOQUE.TMER_CUSTO_MEDIO_REAL` (custo médio **atual**); sem custo, nas unidades 3 e 4, `0,60 × TPED_VALOR_TOTAL_ITEM`; serviço (grupo `'09'`) = 0 | `precoCusto` do cadastro **congelado no dia da leitura**; sem custo = 60% do preço; serviço (tipo `S`) = 0 |
| **Estoque** | `produtos.SALDO` | `TMER_ESTOQUE.TMER_ESTOQUE_TOTAL` (nunca o `_ATUAL`) | `estoque.saldoVirtualTotal` do produto |
| **Estoque a custo** | `SALDO × COALESCE(CUSTO_MEDIO, CUSTO)` | `TMER_ESTOQUE_TOTAL × TMER_CUSTO_MEDIO_REAL` (ou 60% do `TMER_PRECO_VENDA` nas un. 3/4) | `saldo × precoCusto` (ou 60% do preço) |
| **Nome de cliente** | `clientes.RAZAO` (fallback `NOME`) | `TCLI_CLIENTE.TCLI_NOME_RAZAO` (fallback `TCLI_FANTASIA`) | `contato.nome` do Bling (é a razão social) |
| **Nome de fornecedor** | `_nomes.forn_mc()` escolhe entre `fornecedores.NOME` e `RAZAO` (ver [05](05-formulas-glossario.md)) | `TFOR_FORNECEDOR.TFOR_NOME_RAZAO` (fallback `TFOR_FANTASIA`) | `contato.nome` do Bling |
| **Cartão no a receber** | — | Título com `TREC_TIPO_COBRANCA = 'CA'` **nunca** entra | — |
| **`TPAG_BAIXADO` duplicado** | — | Toda leitura usa `SELECT DISTINCT` / agrupa pela chave do título (a tabela repete ~66×) | — |
| **MC (margem de contribuição)** | `venda × 0,93 − CMV` — desconto **fixo de 7%** desde 23/10/2026, igual em todo o painel e nas três empresas | idem | idem |

**Emenda da unidade 4.** Para a unidade 4 o ERP vale **até 28/09/2026** (`_un4.LIMITE_ERP`) e o
Bling **a partir de 29/09/2026** (`_un4.CORTE`). Os geradores que fazem a emenda cortam o SQL com
`_un4.corte_sql()` e somam o Bling por cima. Os que **não** fazem a emenda estão marcados com ⚠️
nas tabelas abaixo — neles a unidade 4 (e portanto a **RHS**) para em 28/09/2026.

**Empresa × unidade.** Desde 14/10/2026 a tela fala em empresa: **RHS = unidades 3 + 4**,
**SEVEN = unidade 5**. As consultas continuam lendo 3, 4 e 5; a soma por empresa acontece na
saída (`_emp.py`, `_emp_payload.py`). A unidade 3 (Ultra Motos) está encerrada desde 30/07/2026 e
o **estoque** dela não entra na RHS.

---

## 3. Página inicial — DASHBOARD

`index.html` → `const DASHBOARD_DB` · gerador `gerar_dashboard.py` (passo B2d) · detalhes em [07](07-dashboard.md).

| Informação | MC MOTO | RHS / SEVEN |
|---|---|---|
| Venda, pedidos e QC por dia (120 dias) e por mês (24 meses) | `vendas.VL_TOTAL`, `COUNT(*)`; QC = clientes distintos + 1 por venda no cliente genérico (`LIKE '%CONSUMIDOR%'`) | `VPED_PEDIDO_HISTORICO.TPED_VALOR_LIQUIDO_PEDIDO`, mesma regra de QC; un. 4 cortada em 28/09 + Bling (`_un4.dias()`) |
| Custo e itens vendidos | `itens.QUANTIDADE × itens.CUSTO`, `SUM(itens.QUANTIDADE)` | `VPED_PEDIDO_HISTORICO_ITEM` × `TMER_ESTOQUE.TMER_CUSTO_MEDIO_REAL` (regra dos 60%) |
| Devoluções abatidas | `devolucoes` ligada a `vendas` | `TMOV_EXTRA`/`TMOV_EXTRA_ITEM` natureza `'DC'` |
| Quebras por grupo, marca, vendedor (13 meses) | grupo `produtos.GRUPO → grupos.DESCRICAO`; marca `produtos.MARCA → marcas.DESCRICAO`; vendedor `vendas.VENDEDOR → vendedores.DESCRICAO` | grupo `TMER_MERCADORIA.TMER_GRUPO_MERCADORIA_FK → TMER_GRUPO_MERCADORIA`; fornecedor `TFOR_FORNECEDOR`; vendedor `TVND_VENDEDOR`. ⚠️ un. 4 cortada em 28/09 **sem** o Bling por cima |
| Contas a pagar em aberto por vencimento | `contas_pagar`, `SITUACAO='A'`, saldo `VALOR − VALOR_RECEBIDO` | `TPAG_ABERTO.TPAG_SALDO_TITULO` (distinto por `TPAG_CODIGO_PK`). ⚠️ sem os títulos do Bling |
| Contas a receber em aberto | `contas_receber`, `SITUACAO='A'` | `TREC_ABERTO.TREC_SALDO_TITULO`, sem cartão (`'CA'`). ⚠️ sem os títulos do Bling |
| Estoque a custo | `produtos.SALDO × COALESCE(CUSTO_MEDIO, CUSTO)` | `TMER_ESTOQUE` (un. 5); RHS = **só o Bling** (`_un4.posicao().estoque`) |
| Custo fixo por centro de custo | `contas_pagar.CENTRO → centro_custos`, valor `VALOR + JUROS + ACRESCIMO − DESCONTO`, mês do pagamento (ou vencimento) | `TPAG_ABERTO_CCUSTO.TPAG_VALOR → TTES_CENTRO_CUSTO`, mês do pagamento (ou vencimento) do título em `TPAG_ABERTO`/`TPAG_BAIXADO`. ⚠️ sem as despesas do Bling |
| Bloco de caixa (7 dias) | reaproveita `buscar()` de `gerar_posicao_caixa_mcmoto.py` | reaproveita `buscar()` de `gerar_posicao_caixa.py` |
| Estoque parado | lido de `dados-mc.js` (`RAW_DATA`) — por isso roda depois do A3 | lido de `dados-seven.js` (`RAW_DATA_SEVEN`) — depois do B2 |
| Meta do mês | Painel Mensal: `localStorage mapa_meta_<VENDEDOR>_vendas`, senão `parametros-painel.json` | idem, chaves da unidade antiga (U4/U3, U5) |
| Parâmetros publicados | `const PARAMS_PUB` = cópia de `parametros-painel.json` | idem |

---

## 4. MC MOTO › Compras

Dados em `dados-mc.js` (carregado quando uma aba de Compras abre) e em `index.html`.

### 4.1 Montar Pedido, Cotação, Pedidos Salvos, INATIVAR — `RAW_DATA` (`dados-mc.js`)

Gerador `gerar_raw_data_mcmoto.py` (passo A3). Um objeto por produto.

| Campo | Coluna na tela | Origem |
|---|---|---|
| `c` | Código | `produtos.PRODUTO` convertido para inteiro (no banco é texto com zeros à esquerda: `'002275'`) |
| `d` | Descrição | `produtos.DESCRICAO` — gravada quando o item entra na lista; não é reescrita depois |
| `r` | (só busca) | referência legada; não é exibida |
| `p` | Custo | `produtos.CUSTO` no dia em que o item **entrou** na lista; não muda na atualização diária |
| `pa` | Custo atual (INATIVAR) | `produtos.CUSTO` de hoje, gravado só quando difere de `p` |
| `pv` | Preço de venda (INATIVAR) | `produtos.VENDA` |
| `e` | Estoque | `produtos.SALDO` |
| `k` | Pico | **maior** quantidade líquida vendida num único mês dos últimos 12: `itens.QUANTIDADE − QTD_DEVOLVIDA − QTD_ESTORNADA`, agrupado por `PRODUTO` e mês, sem `CANCELADO='S'` |
| `k6` | Pico (janela 6 meses) | o mesmo máximo, só nos últimos 6 meses; gravado quando difere de `k` |
| `s` | Sugestão | `round(k − e)`; recalculada no navegador (e multiplicada pelo seletor "Comprar para") |
| `nc` | Comprar? | `produtos.COMISSAO_AVISTA`: 8% → `1` (Não comprar), 5% → `2` (A avaliar), demais → `0` |
| `cf` | Cód. Fabricante | `produtos.COD_FABRICANTE` |
| `f` | Fornecedor | `produtos.FORNECEDOR → fornecedores`, nome escolhido por `_nomes.forn_mc()` (razão social) |
| `gr` / `sg` | Filtros grupo/subgrupo (Análise de Fornecedor) | `produtos.GRUPO` / `produtos.SUBGRUPO`; nomes em `GRUPO_NOMES_MC` (`grupos`) e `SUBGRUPO_NOMES_MC` (`subgrupos`) |
| `ma` | Filtro de marca | `produtos.MARCA`, só quando o código existe em `marcas`; nomes em `MARCA_NOMES_MC` |
| `ue` | Corte "chegou há N dias" | `produtos.ULT_DATA_ENTRADA` |
| `uv` / `up` | Selo "parado há 3/6/12 meses", "Voltaram a vender" | última e penúltima data de venda em `itens.DATA` (histórico inteiro, quantidade líquida > 0) |
| `g` | Grupo do Montar Pedido | **não vem do banco**: o navegador deduz pela descrição (`getGrupo`, `GRUPO_RULES`) |
| `UV_DESDE_MC` | "desde quando há histórico" | data mais antiga de `itens.DATA` lida |

Produto novo entra sozinho na lista quando tem estoque, venda ou entrada nos 12 meses.
Cotação e Pedidos Salvos **não têm fonte no banco**: vivem no `localStorage` do navegador
(`mc_moto_cotacoes`, `mc_moto_pedidos_salvos`).

### 4.2 Recebimentos — `RECEBIMENTOS_DB`, `CMV_MENSAL`, `RECEB_ITENS_DB` (`dados-mc.js`)

| Informação | Gerador | Origem |
|---|---|---|
| Nota recebida (fornecedor, data, valor, "NF n/série") | `gerar_recebimentos_mcmoto.py` (A3b) | `notas_entrada`, 12 meses pela coluna **`DATA`** (entrada, não emissão); **valor = `TOTAL + OUTRAS_DESP`**; fornecedor `fornecedores` via `_nomes.forn_mc()`; id `db_<forn>_<num>_<série>_<data>` |
| Meta automática (CMV do mês anterior) | idem | `CMV_MENSAL` = `SUM(itens.CUSTO × (QUANTIDADE − QTD_DEVOLVIDA − QTD_ESTORNADA))` por mês, 25 meses, sem cancelados |
| "Ver itens" da nota | `gerar_receb_itens_mcmoto.py` (A7b) | `itens_entrada` (`PRODUTO`, `QUANTIDADE`, `VALOR_TOTAL_LIQ`) ligado a `notas_entrada` por empresa/fornecedor/número/série; descrição `produtos.DESCRICAO`; despesas da nota (`FRETE`, `SEGURO`, `IPI`, `VALOR_ST`, `VALOR_FCPST`, `DESCONTO`…) de `notas_entrada` |
| Lançamento manual, meta manual, "fornecedor não mercadoria" | — | `localStorage` (`mc_moto_recebimentos`, `mc_moto_metas_mensais`, `mc_moto_forn_nao_mercadoria`) |

### 4.3 Análise de Fornecedor e Agenda de Compras

| Informação | Gerador | Origem |
|---|---|---|
| Excesso, estoque total, % parado | — (calculado no navegador) | `RAW_DATA` (`k`, `e`, `p`, `ue`) |
| Fornecedor real de item em "FORNECEDOR DEMONSTRACAO"/cadastro repetido (`FORN_REAL_MC*`, `FORN_JUNTOS_MC`) | `gerar_forn_real_mcmoto.py` (B2g) | `itens_entrada` + `notas_entrada` (último fornecedor que entregou o item) + `fornecedores` |
| Coluna "Comprado" por mês (`COMPRAS_MES_MC`) | `gerar_agenda_compras.py` | `SUM(itens_entrada.VALOR_TOTAL_LIQ)` por fornecedor e mês de `notas_entrada.DATA` |
| Última compra, ritmo, valor típico (`AGENDA_COMPRAS_MC`) | idem | mesma consulta; ritmo = **mediana** dos intervalos entre datas de nota, só fornecedor com compra em 12 meses |
| Ruptura, curva ABC, quantidade da agenda | — (navegador) | `RAW_DATA` |

---

## 5. MC MOTO › Vendas

### 5.1 Abas dentro do Mapa de Vendas (`mapa-vendas.html`, gerado por `atualizar_mapa.py`, passo A6)

| Aba | Informação | Origem (`mc_moto`) |
|---|---|---|
| **Painel Mensal** | Venda, pedidos por vendedor | `vendas.VL_TOTAL`, `COUNT(*)`, `vendas.VENDEDOR → vendedores.DESCRICAO`, menos `devolucoes.VL_TOTAL_LIQ` das vendas do período |
| | Custo, itens | `itens.QUANTIDADE × itens.CUSTO`, menos `devolucoes.QUANTIDADE × produtos.CUSTO` |
| | Metas, feriados | `localStorage` (`mapa_meta_*`, `mapa_feriados`), com `parametros-painel.json` como padrão publicado |
| | Dias úteis | automáticos pelos dias com venda (desde 19/10/2026) |
| **Vendas Diárias** | Por dia e vendedor | `vendas` (+ custo/itens de `itens` agregados por pedido) menos `devolucoes` do dia |
| **Grupo de Produto** | Venda, quantidade, custo por grupo no mês | `itens` × `produtos.GRUPO → grupos.DESCRICAO`; `DIVERSOS`/sem grupo reclassificado por palavra-chave da descrição. **Sem** abater devolução |
| **Consistência por Grupo** | Mês × média histórica | mesmas consultas por grupo + `buscar_hist_grupo` / `buscar_media_grupo` (histórico mensal desde a data-base) |
| **Venda por Fornecedor** | Vendas, CMV 12 meses | `itens` × `produtos.FORNECEDOR` (sem abater devolução) |
| | Estoque a custo, cobertura, giro | `produtos.SALDO × COALESCE(CUSTO_MEDIO, CUSTO)` por `produtos.FORNECEDOR` |
| **Clientes** (ranking e evolução, dentro do Mapa) | Venda, pedidos, custo por cliente | `vendas` + `clientes.RAZAO`; custo de `itens`; menos `devolucoes` |
| **Faixa de comissão** (histórico) | Venda por `COMISSAO_AVISTA` | `itens` × `produtos.COMISSAO_AVISTA` |

### 5.2 Abas com página própria

| Aba | Arquivo · gerador | Origem (`mc_moto`) |
|---|---|---|
| **Vendas Históricas** | `vendas-historicas.html` · `gerar_vendas_historicas_mcmoto.py` (A9) | todo o histórico: `vendas.VL_TOTAL` menos `devolucoes.VL_TOTAL_LIQ` (mês da venda original); custo `itens.QUANTIDADE × itens.CUSTO` menos `devolucoes.QUANTIDADE × produtos.CUSTO` |
| **Vendas por Grupo de Comissão** | `vendas-comissao.html` · `gerar_vendas_comissao_mcmoto.py` (A10) | venda `itens.VL_TOTAL − itens.DESCONTO`; faixa `produtos.COMISSAO_AVISTA` (valor 100 = 1%); vendedor `vendas.VENDEDOR → vendedores.DESCRICAO`; devolução `devolucoes` na faixa do produto devolvido |
| **Gráficos** | `graficos-mcmoto.html` · `gerar_graficos_mcmoto.py` (A11) | série mensal = mesma base de Vendas Históricas; grupo (`produtos.GRUPO → grupos`) e comissão (`produtos.COMISSAO_AVISTA`) pela linha do item (`itens.VL_UNIT × qtd líquida`); cidade `clientes.CIDADE → ibge.NOME/UF` (sem o cliente consumidor) |
| **Clientes** | `clientes-mcmoto.html` · `gerar_clientes.py` (B2e) | compras: `vendas` + `clientes.RAZAO`, `vendedores.DESCRICAO`, cidade `ibge`; produtos comprados `itens` (`VL_TOTAL − DESCONTO`) + `produtos.DESCRICAO`; comportamento de pagamento `contas_receber` (36 meses: vencido em aberto, atraso médio) |
| **Monitor de Fechamento** | `monitor-fechamento-mcmoto.html` · `gerar_monitor_fechamento_mcmoto.py` (A12) | venda `vendas.VL_TOTAL` por mês; devolução `devolucoes` (inclusive a que chegou em mês posterior); CMV `itens.CUSTO × qtd líquida`; detalhe por produto dos 3 últimos meses fechados; comparação com `monitor_fechamento\snapshot_*.json` |
| **Comparativo** | `comparativo-mcmoto.html` · `gerar_comparativo_mcmoto.py` (A12b) | por item e mês: `itens.VL_TOTAL − itens.DESCONTO` (vendas `STATUS<>'3'`, item não cancelado) menos `devolucoes.VL_TOTAL_LIQ` no mês da venda original; qtd e custo idem; estoque `produtos.SALDO` × `CUSTO_MEDIO` (`CUSTO` se zerado); tipo/família da `produtos.DESCRICAO`; cliente `vendas.CLIENTE` (sem o `000001` consumidor); vendedor `vendas.VENDEDOR` |
| **Premiação** | `premiacao-mcmoto.html` · `gerar_premiacao_mcmoto.py` (B2j) | venda diária por vendedor `vendas.VL_TOTAL` menos `devolucoes`; meta do Painel Mensal (`localStorage`, senão `parametros-painel.json`) |

---

## 6. MC MOTO › Financeiro

| Aba | Arquivo · gerador | Origem (`mc_moto`) |
|---|---|---|
| **Contas a Pagar** (em aberto) | dentro de `mapa-vendas.html` · `atualizar_mapa.py` | `contas_pagar`, `SITUACAO='A'`, saldo `VALOR − VALOR_RECEBIDO`, sem corte de data; fornecedor `fornecedores` (`_nomes.forn_mc()`) |
| **Contas a Pagar** (já pagos, 12 meses) | idem | `contas_pagar`, `SITUACAO='Q'`, `DATA_PAGAMENTO` em 12 meses; valor `VALOR + JUROS + ACRESCIMO − DESCONTO` |
| **Painel de Caixa** (embutido em Contas a Pagar) | `painel-caixa.html` | **Não vem do banco**: é a cópia do arquivo local `painel_caixa feito.html`, um snapshot gerado à parte (passo A7). Só muda quando esse arquivo muda |
| **Contas a Receber** | `contas-receber-mcmoto.html` · `gerar_contas_receber_mcmoto.py` (A8) | em aberto: `contas_receber`, `SITUACAO='A'`, saldo `VALOR − VALOR_RECEBIDO > 0`; recebidas: `SITUACAO='Q'`, `DATA_PAGAMENTO` em 12 meses, valor `VALOR_RECEBIDO` (ou `VALOR`); cliente `clientes` |
| **Posição de Caixa** | `posicao-caixa-mcmoto.html` · `gerar_posicao_caixa_mcmoto.py` (A13) | a receber e a pagar por vencimento (`contas_receber`/`contas_pagar`, `SITUACAO='A'`); venda prevista = média por dia da semana dos últimos 60 dias de `vendas.VL_TOTAL`; mix de pagamento por **`vendas.FORMA_PAGAMENTO`** (código, nunca o texto); cartão cai em D+1 útil; saldo inicial digitado (`localStorage`) |
| **Relatório Gerencial** | `relatorio-mcmoto.html` · `gerar_relatorio.py` (B2f) | ver seção 9 |

---

## 7. RHS / SEVEN › Compras

Dados em `dados-seven.js` e em `index.html`.

### 7.1 Montar Pedido, INATIVAR — `RAW_DATA_SEVEN` (`dados-seven.js`)

Gerador `gerar_raw_data_seven.py` (passo B2). Um objeto por **produto + unidade**.

| Campo | Coluna na tela | Unidades 3 e 5 (`projeto_f7`) | Unidade 4 (RHS Contagem) |
|---|---|---|---|
| `c`, `u` | Código, unidade | `TMER_ESTOQUE.TMER_CODIGO_PRI_FK_PK`, `TMER_UNIDADE_FK_PK` | `codigo` do produto no Bling (= código do Proton) |
| `d` | Descrição | `TMER_MERCADORIA.TMER_NOME` | a do ERP quando o código já existia; `nome` do Bling só para produto novo |
| `p` | Custo | **custo real da última compra** `TENT_ENTRADA_ITEM.TENT_CUSTO_REAL_COMPRA` (entrada `L`, tipo `CO`); sem entrada, `TMER_ESTOQUE.TMER_CUSTO_MEDIO_REAL`; sem nenhum, 60% do `TMER_PRECO_VENDA` (un. 3) | `precoCusto` do Bling; sem custo, 60% do preço; serviço = 0 |
| `pc` | Custo real (Análise de Fornecedor) | `TENT_CUSTO_REAL_COMPRA`, só quando há entrada | — |
| `ce` | selo custo estimado | 1 quando o custo saiu da regra dos 60% | idem |
| `pv` | Preço de venda (INATIVAR) | `TMER_ESTOQUE.TMER_PRECO_VENDA` | `preco` do Bling |
| `e` | Estoque | `TMER_ESTOQUE.TMER_ESTOQUE_TOTAL` | `estoque.saldoVirtualTotal` do Bling |
| `k` / `k6` | Pico 12 / 6 meses | máximo mensal de `vendas_para_ponto_de_pedido_12m` (`TPED_QTDE_PEDIDA` por `UNIDADE_NEGOCIOS`, produto e mês) | soma do mês do ERP (até 28/09) **com** o mês do Bling (`_un4.qtd_mensal_por_item()`) **antes** de tirar o máximo |
| `cf` | Cód. Fabricante | `TMER_MERCADORIA.TMER_CODIGO_ORIGINAL` | do cache de fornecedor do Bling |
| `f` | Fornecedor | `TMER_ESTOQUE.TMER_FORNECEDOR_PRINCIPAL_FK → TFOR_FORNECEDOR` (fornecedor 9999 "DEMONSTRACAO" fica fora) | fornecedor do detalhe do produto (`_bling_forn_cache.json`) |
| `gr` / `sg` | Filtros grupo/subgrupo | `TMER_MERCADORIA.TMER_GRUPO_MERCADORIA_FK` / `TMER_SUBGRUPO_MERCADORIA_FK`; nomes em `TMER_GRUPO_MERCADORIA` / `TMER_SUBGRUPO_MERCADORIA` | os do ERP (o Bling não substitui) |
| `ia` | selo INATIVO NO ERP | `TMER_ESTOQUE.TMER_ATIVO_COMPRA = 'N'` (inativo sem venda e sem estoque fica fora) | — |
| `ue` | Corte "chegou há N dias" | `TMER_ESTOQUE.TMER_DATA_ULT_ENTRADA` | — |
| `uv` / `up` | Última / penúltima venda | `VPED_PEDIDO_HISTORICO(_ITEM)`, histórico inteiro | idem + Bling |
| `UV_DESDE_SEVEN` | início do histórico | `MIN(TPED_DATA_EMISSAO)` por unidade | — |

Na unidade 4 o Bling **substitui** `e`, `p`, `ce`, `pv`, `f` e `cf` do registro do ERP; código
que não existe no catálogo do Bling fica com **estoque zero** (Contagem não o tem), e produto que
só existe no Bling é acrescentado.

Sugestão editada à mão, pedidos salvos e cotações: `localStorage` (`seven_sugestao_override`,
`seven_pedidos_salvos`, `seven_cotacoes`).

### 7.2 Recebimentos — `RECEBIMENTOS_SEVEN`, `CMV_MENSAL_SEVEN`, `RECEB_ITENS_SEVEN_DB`

| Informação | Gerador | Origem |
|---|---|---|
| Nota recebida (un. 3 e 5, e un. 4 até 28/09) | `gerar_recebimentos_seven.py` (B2b) | **entrada de mercadoria** `TENT_ENTRADA`, só `TENT_STATUS_ENTRADA='L'`; data `TENT_DATA_LIBERACAO` (fallback lançamento, emissão); valor `TENT_VALOR_TOTAL_PEDIDO`; fornecedor `TENT_FORNECEDOR_FKN_UK → TFOR_FORNECEDOR`; id `sv_ent_<un>_<chave>`. Títulos a pagar (`TPAG_ABERTO`/`TPAG_BAIXADO`, `TPAG_VALOR_FATURA`) continuam sendo lidos para a nota **sem mercadoria**, que o painel esconde |
| Nota recebida da RHS a partir de 29/09 | idem, via `_un4.recebimentos()` | Bling: **pedido de compra na situação Atendido (31)** — data prevista se já passou, senão data do pedido — e **NF de entrada Registrada (7)** — `dataOperacao`; fornecedor pela razão social de `/contatos`; ids `bl_pedido_<id>` / `bl_nf_<id>` |
| Meta automática (CMV do mês anterior, por empresa) | idem | `VPED_PEDIDO_HISTORICO_ITEM × TMER_CUSTO_MEDIO_REAL` (regra dos 60%) menos devolução `TMOV_EXTRA 'DC'`, 25 meses; un. 4 cortada em 28/09 + CMV congelado do Bling |
| "Ver itens" da nota | `gerar_receb_itens_seven.py` (B2c) | `TENT_ENTRADA_ITEM` (quantidade `COALESCE(NULLIF(TENT_QTDE_ENTRADA1,0), TENT_QTDE_ENTRADA2)`, valor `TENT_CUSTO_ENTRADA_TOT`) + `TMER_MERCADORIA.TMER_NOME`; RHS pós-corte: itens do pedido/NF do Bling |

### 7.3 Análise de Fornecedor, Agenda, Transferência

| Aba | Gerador | Origem |
|---|---|---|
| Análise de Fornecedor | — (navegador) | `RAW_DATA_SEVEN` (custo = `pc`; sem ele, `p`) |
| Fornecedor real (`FORN_REAL_SEVEN*`, `FORN_JUNTOS_SEVEN`) | `gerar_forn_real_seven.py` | `TENT_ENTRADA_ITEM` + `TENT_ENTRADA` (último fornecedor que entregou, tipo `CO`, status `L`) + `TFOR_FORNECEDOR`. ⚠️ Unidade 4 só até 28/09 (não lê o Bling) |
| Agenda de Compras / "Comprado" (`AGENDA_COMPRAS_SEVEN`, `COMPRAS_MES_SEVEN`) | `gerar_agenda_compras.py` | `TENT_ENTRADA` + `TENT_ENTRADA_ITEM.TENT_PRECO_REAL_TOTAL` (tipo `CO`, status `L`), data `TENT_DATA_LANCAMENTO` (ou emissão). ⚠️ **RHS sem as compras do Bling após 28/09** |
| Transferência (`TRANSF_EXTRA_SEVEN`) | `gerar_transferencia_seven.py` | itens das un. 4 e 5 que faltam no `RAW_DATA_SEVEN`: `TMER_ESTOQUE` + `TMER_MERCADORIA`, pico de `vendas_para_ponto_de_pedido_12m`. ⚠️ Para a un. 4, esse complemento traz o **estoque do ERP**, não o do Bling |

---

## 8. RHS / SEVEN › Vendas

### 8.1 Abas dentro do Mapa de Vendas (`atualizar_mapa.py`)

Todas leem `VPED_PEDIDO_HISTORICO` (cabeçalho) e `VPED_PEDIDO_HISTORICO_ITEM` (itens). A emenda
da unidade 4 **não é igual em todas as consultas** do `atualizar_mapa.py`:

| Consulta (função) | Usada em | Unidade 4 depois de 28/09 |
|---|---|---|
| `buscar_unidades_seven` | Painel Mensal (totais do mês) | ERP cortado + Bling (`mapa_un4_no_periodo`) ✅ |
| `buscar_unidades_vendedores` + `vendedores_rhs` | Painel Mensal › detalhe por vendedor | ERP cortado + Bling por vendedor ✅ |
| `buscar_unidades_fornecedor` + `estoque_forn_rhs` | Vendas por Fornecedor | estoque **do Bling** ✅; venda e CMV: ERP cortado, **sem** Bling ⚠️ |
| `buscar_unidades_hist_mensal` | Vendas Históricas | Bling somado ✅ (o SQL do ERP **não tem corte** — só não dobra enquanto o ERP não tiver movimento da un. 4 depois de 28/09) |
| `buscar_unidades_diarias` | Vendas Diárias | Bling somado ✅ (mesma observação: SQL sem corte) |
| `buscar_unidades_historico` | Painel Mensal › acompanhamento mensal | ERP cortado, **sem** Bling ⚠️ |
| `buscar_unidades_grupos`, `buscar_unidades_hist_grupo` | Gráficos › grupo de produto | ERP cortado, **sem** Bling ⚠️ |
| `buscar_unidades_hist_vendedor` | histórico por vendedor | ERP sem corte, **sem** Bling ⚠️ |
| `buscar_unidades_cidade`, `buscar_unidades_fornecedor_mensal` | quebras por cidade e por fornecedor/mês | ERP sem corte, **sem** Bling ⚠️ |
| `buscar_unidades_ranking_clientes`, `buscar_unidades_clientes_historico` | ranking e evolução de clientes | ERP cortado, **sem** Bling ⚠️ |

| Aba | Informação | Origem |
|---|---|---|
| **Painel Mensal** | Venda e pedidos por empresa | `TPED_VALOR_LIQUIDO_PEDIDO`, `COUNT(*)` |
| | Custo, itens | `TPED_QTDE_PEDIDA × TMER_ESTOQUE.TMER_CUSTO_MEDIO_REAL` (regra dos 60%) |
| | Devolução | `TMOV_EXTRA`/`TMOV_EXTRA_ITEM` `'DC'` (`TMOV_VALOR_TOTAL_ITEM`) |
| | Detalhe por vendedor | `TPED_VENDEDOR_FK → TVND_VENDEDOR.TVND_NOME_ABREVIADO`; RHS pós-corte: vendedor do pedido no Bling |
| | Ranking de clientes | `TPED_CLIENTE_FK → TCLI_CLIENTE.TCLI_NOME_RAZAO` |
| | Badge de atraso de sincronização | `MAX(TPED_DATA_EMISSAO)` por unidade |
| **Gráficos** | Evolução e grupo de produto | histórico mensal acima; grupo `TMER_MERCADORIA.TMER_GRUPO_MERCADORIA_FK → TMER_GRUPO_MERCADORIA.TMER_DESCRICAO`, venda `TPED_VALOR_LIQUIDO_ITEM` |
| **Vendas por Fornecedor** | Vendas, CMV 12 meses | `TPED_VALOR_TOTAL_ITEM` por `TMER_ESTOQUE.TMER_FORNECEDOR_PRINCIPAL_FK → TFOR_FORNECEDOR` |
| | Estoque a custo, cobertura, giro | `TMER_ESTOQUE_TOTAL × TMER_CUSTO_MEDIO_REAL` (regra dos 60%) por fornecedor |
| **Vendas Históricas** | Mês a mês, todo o histórico | `VPED_PEDIDO_HISTORICO` + itens + `TMOV_EXTRA 'DC'` |
| **Vendas Diárias** | Por dia e vendedor | idem, por `DATE(TPED_DATA_EMISSAO)` e `TPED_VENDEDOR_FK`; devolução por `TMOV_VENDEDOR_FKN` |
| | Cidade | `TCLI_CLIENTE.TCLI_CIDADE_CEP_FK → TLOC_CIDADE_CEP` (`TLOC_NOME`/`TLOC_UF_FK`) |

### 8.2 Abas com página própria

| Aba | Arquivo · gerador | Origem |
|---|---|---|
| **Clientes** | `clientes-seven.html` · `gerar_clientes.py` (B2e) | compras `VPED_PEDIDO_HISTORICO` + `TCLI_CLIENTE` + `TVND_VENDEDOR` + `TLOC_CIDADE_CEP`; produtos `VPED_PEDIDO_HISTORICO_ITEM` (`TPED_NOME_MERCADORIA`, `TPED_VALOR_TOTAL_ITEM`); vencido `TREC_ABERTO`, atraso `TREC_BAIXADO` (sem cartão). ⚠️ **Não lê o Bling: a RHS para em 28/09/2026** |
| **Premiação** (só RHS) | `premiacao-seven.html` · `gerar_premiacao.py` (B2h) | **só a unidade 4**: `VPED_PEDIDO_HISTORICO.TPED_VALOR_LIQUIDO_PEDIDO` até 28/09 menos `TMOV_EXTRA 'DC'`, e o Bling (`_un4.dias()`) depois. Meta, dias úteis e prêmios: `localStorage` |
| **Relatório Gerencial** | `relatorio-seven.html` · `gerar_relatorio.py` (B2f) | ver seção 9 |

---

## 9. Relatório Gerencial (MC MOTO e RHS/SEVEN)

`relatorio-mcmoto.html`, `relatorio-seven.html`, `relatorio-historico.json` e `const DRE_DESPESAS`
no `index.html` · gerador `gerar_relatorio.py` (B2f).

| Linha / bloco | MC MOTO | RHS / SEVEN |
|---|---|---|
| Venda por forma de pagamento, comissão, frete | `vendas.VL_TOTAL`, `VL_COMISSAO`, `VL_FRETE` por `DESCRICAO_FORMA` | `TPED_VALOR_LIQUIDO_PEDIDO`, `TPED_COMISSAO_VALOR_GERAL`, `TPED_VALOR_FRETE` por `TPED_TIPO_PAGAMENTO`; un. 4 cortada + Bling (à vista × a prazo pelas parcelas) |
| Devolução | `devolucoes` | `TMOV_EXTRA 'DC'` |
| CMV | `itens.QUANTIDADE × itens.CUSTO` | `VPED_PEDIDO_HISTORICO_ITEM × TMER_CUSTO_MEDIO_REAL` (regra dos 60%) + CMV congelado do Bling |
| Compras do mês | `notas_entrada.TOTAL` (sem `OUTRAS_DESP` — difere de Recebimentos) | `TPAG_*.TPAG_VALOR_FATURA` por data de chegada (`TPAG_DATA_CHEG_EXECUCAO`); RHS pós-corte: **todo** pedido de compra do Bling pela data do pedido, em qualquer situação (difere de Recebimentos, que só conta Atendido e NF registrada) |
| Despesas por centro de custo (custo fixo) | `contas_pagar`, **título a título**, mês do **vencimento**, sem `SITUACAO='C'`; `CENTRO → centro_custos` | `TPAG_ABERTO_CCUSTO` linha a linha, mês do vencimento; título baixado com `TPAG_VALOR_PAGO = 0` fica fora; `TTES_CENTRO_CUSTO`; RHS pós-corte: categoria do Bling |
| Juros pagos / recebidos | `contas_pagar.JUROS`, `contas_receber.JUROS` pelo mês do pagamento | `TPAG_BAIXADO.TPAG_JURO_PAGO`, `TREC_BAIXADO.TREC_JURO_RECEBIDO` (sem cartão) |
| Posição (estoque, a pagar, a receber) | `produtos` (estoque a custo), `contas_pagar`/`contas_receber` `SITUACAO='A'` | `TMER_ESTOQUE`, `TPAG_ABERTO`, `TREC_ABERTO` (sem cartão); estoque da RHS só do Bling |
| Dias com faturamento | `COUNT(DISTINCT vendas.DATA)` | `COUNT(DISTINCT TPED_DATA_EMISSAO)`; RHS = o **maior** entre as unidades |
| Meses fechados | `relatorio-historico.json` (gravado no dia 1; por **unidade**) | idem |
| Lançamentos manuais, alíquotas, classificação | `localStorage` / `parametros-painel.json` | idem |

---

## 10. RHS / SEVEN › Financeiro

| Aba | Arquivo · gerador | Origem |
|---|---|---|
| **Contas a Pagar** | `contas-pagar-seven.html` · `gerar_contas_seven.py` (B3) | em aberto `TPAG_ABERTO.TPAG_SALDO_TITULO > 0`; pagas `TPAG_BAIXADO`, situação `LQ`, `TPAG_DATA_ULTIMO_PAGAMENTO` em 12 meses, **agrupada pela chave do título** (dedup obrigatório); fornecedor `TFOR_FORNECEDOR`. **RHS:** soma os títulos do ERP (antigos) com os **títulos nativos do Bling** em aberto (situação 1), sem os que vieram da carga Proton → Bling. ⚠️ No modo "Quitadas" a RHS só tem o ERP (até 28/09) |
| **Contas a Receber** | `contas-receber-seven.html` · idem | em aberto `TREC_ABERTO` (`TREC_RECEBER_PAGAR_FK='R'`, sem cartão); recebidas `TREC_BAIXADO`, situação `LQ`, 12 meses; cliente `TCLI_CLIENTE`. **RHS:** + títulos nativos do Bling em aberto. ⚠️ "Recebidas" da RHS só até 28/09 |
| **Posição de Caixa** | `posicao-caixa-seven.html` · `gerar_posicao_caixa.py` (B3b) | a receber `TREC_ABERTO` por vencimento (cartão tipos 10/12 = emissão + 1 dia; cobrança `'CA'` só no aviso); a pagar `TPAG_ABERTO`; venda média `VPED_PEDIDO_HISTORICO`. ⚠️ **Não lê o Bling: os títulos da RHS emitidos depois de 28/09 não entram na projeção** |
| **Risco/Cliente** | `risco-cliente.html` · `gerar_risco_cliente.py` (B1) | saldo e vencido `TREC_ABERTO`; atraso `TREC_BAIXADO`; limite de crédito `TLNK_CLIENTE_UNIDADE.TLNK_LIMITE_CREDITO`; frequência `VPED_PEDIDO_HISTORICO`; nome `TCLI_CLIENTE` (sem cartão, sem clientes internos). ⚠️ **Não lê o Bling: a RHS para em 28/09/2026** |
| **Relatório Gerencial** | `relatorio-seven.html` | seção 9 |

---

## 11. RHS / SEVEN › CRM

| Aba | Arquivo · gerador | Origem |
|---|---|---|
| **Cadastro de Cliente** | `cadastro-clientes-seven.html` · `gerar_cadastro_clientes.py` (B2i) | cadastro `TCLI_CLIENTE.TCLI_DATA_CADASTRAMENTO`, `TCLI_NOME_RAZAO`, `TCLI_TIPO_PESSOA`, grupo `TCLI_GRUPO`; conversão = pedido não cancelado em qualquer unidade (`VPED_PEDIDO_HISTORICO`). ⚠️ **Não lê o Bling: cliente cadastrado ou convertido na RHS depois de 28/09 não aparece** |
| **CRM** | `crm-seven.html` | **Arquivo estático, sem gerador.** Os dados estão embutidos no HTML (de 24/07/2026) e **não são atualizados** pela rotina |

---

## 12. Pendências de origem encontradas nesta revisão (23/10/2026)

São telas em que **a fonte publicada não é a que o painel declara**. Ficam registradas aqui até
alguém corrigir o gerador; quando corrigir, apague a linha e o ⚠️ da seção correspondente.

| # | Tela | O que acontece | Por quê |
|---|---|---|---|
| 1 | RHS › Vendas › Clientes | Compras da RHS param em 28/09/2026 | `gerar_clientes.py` não usa `_un4` |
| 2 | RHS › CRM › Cadastro de Cliente | Conversões da RHS param em 28/09/2026 | `gerar_cadastro_clientes.py` não usa `_un4` |
| 3 | RHS › Financeiro › Risco/Cliente | Saldo, atraso e frequência da unidade 4 param em 28/09/2026 | `gerar_risco_cliente.py` não usa `_un4` |
| 4 | RHS › Financeiro › Posição de Caixa | Títulos do Bling (emitidos após 28/09) ficam fora da projeção, enquanto Contas a Pagar/Receber já os mostram | `gerar_posicao_caixa.py` não usa `_un4.titulos()` |
| 5 | RHS › Compras › Agenda de Compras | Última compra e ritmo da RHS ignoram as compras do Bling | `gerar_agenda_compras.py` não usa `_un4.recebimentos()` |
| 6 | RHS › Compras › Transferência | O complemento da unidade 4 traz estoque do ERP congelado em 28/09 | `gerar_transferencia_seven.py` lê `TMER_ESTOQUE` para a un. 4 |
| 7 | RHS › Compras › Análise de Fornecedor (fornecedor real) | Fornecedor real da unidade 4 só pelas entradas do ERP | `gerar_forn_real_seven.py` não usa o Bling (impacto pequeno: é histórico) |
| 8 | RHS/SEVEN › CRM › CRM | Dados de 24/07/2026, nunca atualizados | `crm-seven.html` não tem gerador |
| 9 | MC MOTO › Financeiro › Painel de Caixa | Snapshot de 14/07/2026 | `painel_caixa feito.html` não é regerado por nenhum processo da rotina |
| 10 | DASHBOARD (RHS) — contas a pagar/receber, custo fixo | Títulos e despesas do Bling ficam fora; os mesmos títulos aparecem em Financeiro › Contas a Pagar/Receber | `gerar_dashboard.py` só soma do Bling a venda (`_un4.dias()`) e o estoque (`_un4.posicao()`) |
| 11 | DASHBOARD (RHS) — gráficos de grupo, fornecedor e vendedor | A unidade 4 some dessas quebras a partir de 29/09 | as consultas cortam a un. 4 em 28/09 e não há Bling por cima |
| 12 | Relatório Gerencial — linha "Compras" | MC MOTO usa `notas_entrada.TOTAL` (Recebimentos usa `TOTAL + OUTRAS_DESP`); RHS conta pedido de compra do Bling em qualquer situação (Recebimentos só Atendido/NF registrada) | regras escritas em momentos diferentes; nenhuma das duas foi decidida como divergência |
| 13 | RHS › Vendas (Mapa) — grupo de produto, fornecedor (venda/CMV), cidade, ranking e histórico de clientes, histórico por vendedor, acompanhamento mensal | A unidade 4 some dessas visões a partir de 29/09 | as funções listadas na seção 8.1 com ⚠️ não somam o Bling |
| 14 | RHS › Vendas (Mapa) — Vendas Históricas e Vendas Diárias | **Risco** de contar duas vezes, se o ERP voltar a ter movimento da un. 4 depois de 28/09 | o SQL do ERP dessas duas funções não usa `_un4.corte_sql()` e o Bling é somado por cima |
| 15 | RHS › Financeiro › Contas a Pagar/Receber — modo "Quitadas (12 meses)" | Pagamentos e recebimentos da RHS feitos no Bling depois de 28/09 não aparecem | `gerar_contas_seven.py` só soma do Bling os títulos **em aberto** (situação 1) |
