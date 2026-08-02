# RHS/SEVEN

Grupo de navegação separado da MC MOTO, cobrindo as unidades de negócio do grupo SEVEN. Fonte de dados principal: banco **`projeto_f7`** (espelho read-only do ERP da SEVEN, tabelas com prefixos `TCLI_`, `TVND_`, `TPED_`/`VPED_`, `TREC_`, `TPAG_`, `TMER_`, `TENT_`, etc.).

> **O espelho não é estável — confira antes de assumir que algo não existe.** Em 31/07/2026 apareceram **`TENT_ENTRADA_ITEM`** e, poucas horas depois, **`TENT_ENTRADA`** (entradas de compra, desde mar/2023) — o espelho foi de **33 → 34 → 35 tabelas** no mesmo dia. Numa varredura feita de manhã a conclusão registrada foi "não existe fonte de itens de compra"; à tarde já existia. **Sempre rodar `SHOW TABLES` antes de afirmar que algo não está lá.** Essas tabelas alimentam o custo real de compra da Análise de Fornecedor e o detalhe de itens por nota em Recebimentos.

### Custo estimado nas unidades 3 e 4 (31/07/2026)

Nas unidades **3 (Ultra Motos)** e **4 (Seven Contagem)** a maior parte do cadastro **não tem custo no ERP** — 65% e 44% dos itens. Isso inflava a margem e subestimava o valor de estoque. Regra do usuário:

```
custo = custo do ERP,           quando > 0
      = 0,                      quando o item é SERVIÇO
      = 0,60 × preço de venda,  nos demais casos (só unidades 3 e 4)
```

- **SERVIÇO = grupo de mercadoria `'09'`** (SERVICOS: retífica, sangria, reboque, "trocar …"). ⚠️ **Não usar a coluna `TMER_MERCADORIA_SERVICO`** — ela vale `'A'` em 14.573 dos 14.574 itens do cadastro (e `'C'` em 1); não marca nada.
- **Unidade 5 não entra na regra** — lá só 15% dos itens estão sem custo.
- "Preço de venda" é o do contexto: no **catálogo** é `TMER_PRECO_VENDA`; nas **vendas/CMV** é o valor efetivamente vendido do item (`TPED_VALOR_TOTAL_ITEM`), e nas devoluções o `TMOV_VALOR_TOTAL_ITEM`.
- **Aplicada em todos os lugares que calculam custo da SEVEN**, para as telas não divergirem:
  - `gerar_raw_data_seven.py` → `p` (Montar Pedido e Análise de Fornecedor);
  - `gerar_recebimentos_seven.py` → `CMV_MENSAL_SEVEN` (meta de recebimento), venda e devolução;
  - `atualizar_mapa.py` → aba **Vendas / Unidades de Negócio** (7 pontos: 6 de venda + 1 de devolução). Ali a regra é uma **subconsulta correlacionada**, de propósito: entra nas 6 consultas sem mexer nos joins/aliases de cada uma nem arriscar multiplicar linhas.
- **Efeito medido:** itens com custo zero no catálogo caem de 65% → **1,3%** (un 3) e 44% → **1,7%** (un 4); o que sobra são os serviços e itens que também não têm preço de venda (60% de zero é zero). CMV de jun/2026: un 3 **+7,8%**, un 4 **+0,9%**, un 5 inalterado. Margem de jun/2026 da un 3: **47,6% → 43,5%**.

### Ver itens da nota (31/07/2026)

Na aba **Compras > Recebimentos** da SEVEN, cada nota de **mercadoria** é clicável e expande os itens que chegaram (código, produto, quantidade, valor), igual à MC MOTO. Dados em `const RECEB_ITENS_SEVEN_DB = { "<id da nota>": [{c,d,q,v}], … }`, gerado por `gerar_receb_itens_seven.py` (rotina diária, passo **B2c**, sempre **depois** do B2b porque reusa os ids `sv_<unidade>_<tipo>_<numero>_<fornecedor>`).

- **Como amarra item → nota:** o título a pagar carrega **`TPAG_ENTRADA_FKN`**, que liga direto em `TENT_ENTRADA_ITEM.TENT_CHAVE_FK_PK` (+ unidade). Validado: número da nota e fornecedor do título batem com o cabeçalho `TENT_ENTRADA` em **850/850** casos, e 100% das chaves referenciadas têm itens.
- **Cobertura ~58% (757 de 1.309 notas) — é o esperado, não é falha.** As 42% sem itens são exatamente os títulos que **não são mercadoria**: banco, aluguel, salários, INSS/FGTS/CSLL, transportadora. Nota de mercadoria tem entrada; despesa não tem. Por isso essas linhas ficam não-clicáveis por design.
- **Colunas escolhidas por medição:** quantidade = `COALESCE(NULLIF(TENT_QTDE_ENTRADA1,0), TENT_QTDE_ENTRADA2)` — as duas são **estritamente complementares** (dos 14.882 itens, nenhum tem as duas preenchidas nem as duas zeradas); valor = **`TENT_CUSTO_ENTRADA_TOT`**, que somado por entrada dá **99,2%** do `TENT_VALOR_NOTA` do cabeçalho, contra 90,5% (`TENT_PRECO_REAL_TOTAL`) e 63,1% (`TENT_PRECO_COMPRA_TOTAL`). Filtra `TENT_STATUS_ENTRADA='L'`.
- ⚠️ **A reconstrução das notas continua vindo dos títulos a pagar**, não de `TENT_ENTRADA`. Os valores e a meta da aba estão calibrados nessa fonte — não trocar sem o usuário pedir. Credenciais não reproduzidas aqui — ver `conexaomc.md` (arquivo local, não versionado).

## Unidades de Negócio

Sub-aba padrão do grupo RHS/SEVEN. **Não é conteúdo próprio de `index.html`** — é o mesmo iframe `mapa-vendas.html` usado pela aba Vendas da MC MOTO, apenas trocado para sua sub-aba interna `unidades` (`trocarAba('unidades')`), agora mostrando dados agregados por unidade de negócio em vez de por vendedor/grupo de produto MC MOTO.

Mecânica compartilhada com o restante do Mapa de Vendas: mesmo cálculo de MC (`vendas*f - custo`), e uma marcação de **atraso de sincronização** — se a última nota fiscal de uma unidade estiver mais de **2 dias** (`LIMITE_ATRASO`) atrasada em relação à data de referência, a unidade recebe um badge âmbar de "atraso" na interface.

### Sub-abas de VENDAS (02/08/2026)

A aba **VENDAS** deixou de ser uma tela só e ganhou uma segunda linha de sub-abas (`#subtabs-sevenvendas`), todas **deep-link** para abas do Mapa de Vendas (mesmo padrão da MC MOTO), cada uma **permissionável em separado**:

| Sub-aba | Aba do Mapa | Conteúdo |
|---|---|---|
| **Painel Mensal** | `unidades` | Painel do mês por unidade · Detalhe por vendedor · Acompanhamento mensal (histórico) · Ranking de clientes |
| **Gráficos** | `unigraf` | Evolução das unidades (6 gráficos) · Vendas por grupo de produto |
| **Vendas por Fornecedor** | `unifor` | **Novo.** 12 meses: vendas, CMV, MC, MC%, estoque a custo, cobertura em meses e giro. Cobertura > 6 meses marca **estoque parado** (66 fornecedores hoje). Busca + filtro "só estoque parado". |
| **Vendas Históricas** | `unihist` | **Novo.** Todo o histórico (41 meses): gráfico de faturamento, tabela mês a mês com MC/MC%/pedidos/ticket e comparação com o mesmo mês do ano anterior. Filtro 12/24/tudo. |

O bloco de controles (unidades, % desconto, dias úteis) foi movido para **fora** dos painéis (`#uni-controles`), acima deles, e `trocarAba()` o exibe apenas nas 4 abas da SEVEN — assim as quatro compartilham o mesmo filtro.

### Filtro de unidades — múltipla escolha (02/08/2026)

O `<select>` de unidade virou **checkboxes** (`#uni-checks`), então dá para combinar **duas ou mais** unidades. Helpers no Mapa: `uniSel()` (marcadas; vazio = todas as visíveis), **`uniOk(cod)`** (o teste que todas as seções usam) e `rotuloUnidades()` (ex.: "Seven Contagem + Seven Ipatinga"). Persistido em `mapa_uni_sel`; migra do formato antigo `mapa_uni_filtro`.

⚠️ **`aplicarUnidadesPermitidas()` no `index.html` teve de ser adaptado** — ele manipulava as `<option>` do select e agora marca/desmarca checkboxes. Usuário restrito continua vendo só as unidades liberadas; se a restrição desmarcar tudo, as permitidas são remarcadas automaticamente.

## CRM

Iframe separado, `crm-seven.html`, escopo declarado "Unidades 3 e 4". Painel próprio, independente do sistema de navegação por senha/categoria do restante do painel. Não detalhado nesta documentação (arquivo autocontido, fora do escopo revisado).

**Grupos de cliente pelo nome** (24/07/2026): o filtro "Grupo de cliente" exibia os códigos crus (`001`, `002`, `07`, `A`…). Passou a exibir o **nome** via o mapa `GRUPO_NOMES` + helper `nomeGrupo()`, com os valores de `projeto_f7.TCLI_GRUPO` (`TCLI_GRUPO_PK` → `TCLI_GRUPO_NOME`): GRUPO PADRAO, CARTAO, LEADS ATACADO, LEADS VAREJO, FUNCIONARIOS, AMBEV, GRUPO UNIFORT, INSTAGRAM/FACE, GOOGLE, A–D, CLIENTE FECHOU. Código desconhecido cai no fallback `Grupo <cod>`; vazio vira "Sem grupo". ⚠️ `crm-seven.html` **não tem script gerador** no projeto — o mapa está embutido no HTML, então se a página for regerada de outra fonte é preciso reaplicá-lo.

## Compras

Réplica da aba **MC MOTO → Compras** (mesmo fluxo, mesmas regras de interface), mas alimentada pelo banco **`projeto_f7`** da SEVEN, unidades **3, 4 e 5**. Conteúdo nativo de `index.html` (`app-tab-comprasseven`), com 3 sub-abas: Montar Pedido, Cotação, Pedidos Salvos. **Recebimentos ficou de fora por decisão explícita** — não existe fonte confiável de notas de entrada no espelho da SEVEN (a candidata `TMOV_EXTRA` filtrada por fornecedor tem só ~1 registro por unidade em ~3 anos).

### Fonte de dados: `RAW_DATA_SEVEN`

Array JS embutido em `index.html` (~21.800 itens), gerado pelo script local `gerar_raw_data_seven.py` (não versionado; roda diariamente na rotina `atualizacao-diaria-painel`, Parte B). Um item por **produto + unidade** (o mesmo código de produto pode aparecer nas 3 unidades com estoque/custo próprios; a chave composta usada no JS é `codigo_unidade`).

| Campo | Significado | Origem |
|---|---|---|
| `c` | Código do produto | `TMER_ESTOQUE.TMER_CODIGO_PRI_FK_PK` |
| `u` | Unidade de negócio (3, 4 ou 5) | `TMER_ESTOQUE.TMER_UNIDADE_FK_PK` |
| `d` | Descrição | `TMER_MERCADORIA.TMER_NOME` |
| `p` | Custo médio | `TMER_ESTOQUE.TMER_CUSTO_MEDIO_REAL` — **sempre o `_REAL`, nunca o `TMER_CUSTO_MEDIO`** (decisão do usuário 24/07/2026): o `_REAL` está preenchido em mais itens (18.765 vs 17.386 nas unidades 3/4/5) e corrigiu 4.980 itens, vários que apareciam com custo 0 |
| `k` | Pico de vendas mensal (máximo por mês nos últimos 12m, **nunca soma** — mesma regra da MC MOTO) | `vendas_para_ponto_de_pedido_12m` |
| `e` | Estoque total | `TMER_ESTOQUE.TMER_ESTOQUE_TOTAL` — **sempre o TOTAL, nunca o `TMER_ESTOQUE_ATUAL`** (decisão do usuário 21/07/2026): o `ATUAL` fica muito negativo e não reflete o estoque real; `TOTAL = ATUAL + HIST` |
| `s` | Sugestão de compra = **`pico − estoque` (`k − e`)**, recalculada ao vivo (igual à MC MOTO) e **editável na interface** — ver diferenças abaixo | calculada no navegador a partir de `k`/`e`; a rotina diária também grava `s = k − e` |
| `cf` | Código original/fabricante | `TMER_MERCADORIA.TMER_CODIGO_ORIGINAL` |
| `f` | Fornecedor principal (fantasia, ou razão social) | `TFOR_FORNECEDOR` via `TMER_FORNECEDOR_PRINCIPAL_FK` |
| `g` | Grupo de produto — **vem classificado do próprio banco** (`TMER_GRUPO_MERCADORIA`), sem reclassificação por palavra-chave como na MC MOTO | mapeamento fixo código→nome |

Filtros aplicados na geração: só itens com `TMER_ATIVO_COMPRA='S'` e fornecedor principal ≠ 9999 (cadastro "DEMONSTRACAO"). Grupos `001`–`004` ("ERRO") caem em `DIVERSOS`.

### Diferenças em relação ao Compras da MC MOTO

1. **Filtro de Unidade** (checkboxes 3/4/5, todas marcadas por padrão) — não existe na MC MOTO.
2. **Sem badge "Comprar?"/regra de comissão** — o banco da SEVEN não tem o campo de comissão que alimenta essa regra na MC MOTO; a coluna foi removida por decisão explícita.
3. **Sugestão de compra editável** — a coluna "Sugestão" mostra `pico − estoque` por padrão, mas é um **campo editável por item**. A edição manual sobrepõe o padrão e é persistida em `localStorage` (chave `seven_sugestao_override`, por `código_unidade`); a célula editada fica destacada em roxo. A sugestão (editada ou padrão) vira a **quantidade default** ao adicionar o item ao pedido ou à cotação — `sug > 0 ? sug : 1` (igual à MC MOTO). Como a chave é por produto+unidade, a mesma peça pode ter sugestões diferentes em cada unidade. O filtro padrão continua "Todos os itens".
   Desde 24/07/2026 a sugestão também alimenta os controles de filtro/ordem (paridade com a MC MOTO): **"Mostrar apenas" → "Com sugestão de compra"** (mantém só `sugestão > 0`) e **"Ordenar por" → "Sugestão (maior)" / "Sugestão (menor)"**. Todos usam `sugestaoSeven()`, ou seja, **respeitam as edições manuais** — um item cuja sugestão foi editada para 0 sai do filtro, e a ordenação usa o valor editado.
4. Armazenamento separado em `localStorage`: `seven_pedidos_salvos` e `seven_cotacoes` (não se misturam com os da MC MOTO).
5. O modal de exportação é **compartilhado** entre MC MOTO e SEVEN — a variável `_pedidoAtivoFonte` decide título, builders de CSV/PDF (com coluna Unidade, sem Sugestão/Comprar?) e qual pedido o botão "Salvar" grava.
6. Na cotação, o preço respondido pelo fornecedor é **por código de produto** (não por unidade) — se o mesmo produto estiver na cotação para duas unidades, o preço importado vale para as duas linhas.

Todo o resto (busca E/OU, multi-seleção de fornecedor, "adicionar todos" com confirmação acima de 200 itens, exportações texto/CSV/PDF, fluxo completo de cotação com link HTML/planilha e "comprar pelo menor preço") segue as mesmas regras documentadas em [01-compras](01-compras.md).

### Recebimentos (sub-aba de Compras)

Criada em 30/07/2026 seguindo **as mesmas regras da aba Recebimentos da MC MOTO** (ver [`01-compras.md`](01-compras.md) / [`03-financeiro-mc-moto.md`](03-financeiro-mc-moto.md)): lista dos recebimentos do mês (sistema + lançamentos manuais), filtro de **fornecedores de mercadoria**, **meta do mês** (automática = CMV do mês anterior, ou manual pelo ✏️) com barra de progresso (85% âmbar / 100% vermelho) e **quadro anual** Recebido × Meta × Desvio. Chave de permissão: `sv.recebimentos`.

**⚠️ Diferença estrutural importante — de onde vêm os dados.** O espelho `projeto_f7` **não tem tabela de notas de entrada** (a MC MOTO usa `notas_entrada`). A única fonte de compras de fornecedor no espelho são os **títulos a pagar**. Então `gerar_recebimentos_seven.py` **reconstrói a nota** agrupando `TPAG_ABERTO` + `TPAG_BAIXADO` por `(unidade, tipo, número, fornecedor)` e usando **`TPAG_VALOR_FATURA`** — que é o valor da **nota**, não da parcela; assim uma NF em 5× conta **uma vez**. `SELECT DISTINCT` é obrigatório (o `TPAG_BAIXADO` do espelho tem duplicação ~66×). Consequências a ter em mente:
- entram também títulos que **não são mercadoria** (serviços, impostos…) — por isso o filtro de "fornecedores de mercadoria" existe aqui também, com lista **própria da SEVEN** (`seven_forn_nao_mercadoria`, separada da MC MOTO);
- **a data do recebimento é a DATA DE LIBERAÇÃO DA NOTA** (decisão do usuário 30/07/2026) = `TPAG_DATA_CHEG_EXECUCAO` (chegada/execução, quando a loja libera a NF), **não** a emissão. Motivos: a emissão é a data do fornecedor e tem registros com ano inválido (ex. 0024, 0206); a liberação está 100% preenchida e é sempre ≥ emissão. Fallback para emissão só se a liberação vier nula. Efeito: notas emitidas no fim de um mês e liberadas no mês seguinte contam no mês da liberação (ex. jul/26 passou de R$ 129.204,00 por emissão para R$ 153.865,86 por liberação);
- se `VALOR_FATURA` vier zerado, o script cai para a soma das parcelas.

**Meta por unidade + CMV (decisão do usuário 30/07/2026):** a meta é **por unidade de negócio** — antes o "Recebido" mudava com o filtro de unidade mas a meta seguia sendo o total das três, o que invalidava a comparação. Agora `CMV_MENSAL_SEVEN` é **por unidade**: `{"3":{"YYYY-MM":v,…},"4":{…},"5":{…}}`. A **meta automática** de um mês = **CMV do mês anterior** da(s) unidade(s) em foco (a selecionada, ou a soma das permitidas em "Todas"). O CMV continua sendo uma **aproximação** — `Σ(qtd vendida × TMER_CUSTO_MEDIO_REAL)`, a mesma que o painel usa para a margem da SEVEN, porque o espelho não guarda o custo da venda. Como o custo médio é o **atual** (muda a cada compra nova), o mesmo mês recalculado em dias diferentes varia um pouco — é esperado.

> ⚠️ **Fonte do CMV — corrigido em 31/07/2026 (não regredir).** O CMV vinha de **`mv_resumo_vendas`**, que **subestima a venda em ~24%** (jun/2026, unidade 5: R$ 161.439 na view vs R$ 210.411 reais) e não abatia devolução. Resultado: a **meta de recebimento saía ~24% baixa** nas três unidades — jul/2026 mostrava R$ 171.346,39 quando o correto é **R$ 225.304,13**. Detectado pelo usuário ao conferir contra os números do ERP.
>
> A fonte correta é **`VPED_PEDIDO_HISTORICO(_ITEM)`**, com a **mesma regra da aba Unidades de Negócio** (`atualizar_mapa.py > buscar_unidades_seven`), para as duas telas baterem: mês pela **data de emissão**, pedidos cancelados fora (`TPED_DATA_CANCELAMENTO IS NULL`), custo = `TPED_QTDE_PEDIDA × TMER_CUSTO_MEDIO_REAL` da unidade, **menos** o custo das devoluções de cliente (`TMOV_EXTRA` natureza `'DC'`). Conferência jun/2026: un 3 R$ 26.479,06 · un 4 R$ 62.394,38 · un 5 R$ 136.430,69.
>
> **`mv_resumo_vendas` não é fonte confiável de venda/CMV da SEVEN** — usar sempre `VPED_PEDIDO_HISTORICO`.
- **Meta manual** também é por unidade: gravada em `seven_metas_mensais` na chave `"mes|unidade"` (ex. `"2026-07|4"`). Só pode ser editada com **uma unidade selecionada** (em "Todas" o ✏️ avisa e não deixa). Em "Todas", se alguma unidade tem meta manual, ela substitui só a parcela daquela unidade e o restante segue no automático (a etiqueta "(CMV)" some por ser meta mista).

**Diferenças de interface em relação à MC MOTO:** tem um **filtro de unidade** (Todas / 3 / 4 / 5) que respeita a permissão de unidade do usuário e vale também para o quadro anual, e o lançamento manual pede a unidade. Armazenamento próprio em `localStorage`: `seven_recebimentos` e `seven_metas_mensais`.

Volume atual (30/07/2026): 1.294 notas nos últimos 12 meses, R$ 3.531.928,42.

## Financeiro

Painel nativo de `index.html` (não iframe), com 3 sub-categorias via `switchCategoriaFinanceiroSeven`:

### Contas a Pagar e Contas a Receber

Duas páginas geradas pelo script local `gerar_contas_seven.py` (não versionado; roda diariamente na rotina `atualizacao-diaria-painel`, Parte B), embutidas via iframe: `contas-pagar-seven.html` e `contas-receber-seven.html`. Ambas cobrem as **unidades 3, 4 e 5** e compartilham a mesma estrutura:

- **Dois modos**, alternados por botões: **"Em aberto"** e **"Quitadas (últimos 12 meses)"**.
- **Filtro de unidade de negócio** (checkboxes 3/4/5, todas marcadas por padrão) — todos os KPIs, gráfico e detalhe são recalculados no navegador conforme a seleção.
- **Aging dos títulos em aberto** (mesma regra do Contas a Pagar do Mapa de Vendas): **vencida** (`vencimento < hoje`), **até 30 dias** (`vencimento < hoje+30`), **futura** (demais). O aging é recalculado contra a data em que a página está sendo vista — a classificação "envelhece" sozinha entre gerações; só os saldos exigem reexecução do script.
- KPIs (Total em aberto / Vencidas / Vencem em 30 dias / Futuras) + gráfico de barras por mês de vencimento, com bucket "Após 12m" para qualquer vencimento além de 12 meses (o que também absorve datas digitadas erradas no ERP, ex. um título com vencimento no ano 2502).
- Fontes e regras específicas:
  - **Pagar em aberto**: `TPAG_ABERTO` com `TPAG_SALDO_TITULO > 0` (saldo líquido de pagamentos parciais — situações `AB` e `PP`). Detalhe: lista de títulos agrupada por mês de vencimento (accordion), mês vencido/atual auto-expandidos, cabeçalho vermelho para mês com título vencido.
  - **Pagar quitadas (12m)**: `TPAG_BAIXADO`, situação `LQ`, pagamento (`TPAG_DATA_ULTIMO_PAGAMENTO`) nos últimos 12 meses. ⚠️ **Essa tabela-espelho tem duplicação massiva (~66x)** — verificado em 18/07/2026: 103.675 linhas correspondiam a apenas 1.575 títulos reais. A geração **deduplica obrigatoriamente** por chave natural (unidade, tipo, número, parcela, fornecedor). Detalhe: tabela agregada por fornecedor (títulos pagos, último pagamento, total pago), ordenada por total.
  - **Receber em aberto**: `TREC_ABERTO` com `TREC_RECEBER_PAGAR_FK='R'` e `TREC_SALDO_TITULO > 0`. Detalhe: tabela agregada **por cliente** (títulos, vencido, maior atraso em dias, vence em 30d, futuro, total), ordenada pelo maior valor vencido, linha vermelha para quem tem saldo vencido.
  - **Receber quitadas (12m)**: `TREC_BAIXADO`, situação `LQ`, baixa nos últimos 12 meses (essa tabela **não** tem a duplicação da TPAG — verificado; ainda assim a geração deduplica por segurança). Detalhe: tabela agregada por cliente (títulos recebidos, último recebimento, total recebido).

Nota: **MC MOTO → Financeiro → Contas a Pagar** continua existindo em separado (deep-link para dentro do Mapa de Vendas, banco `mc_moto`) — são painéis distintos com fontes distintas.

### Risco/Cliente
Embutido via iframe (`risco-cliente.html`), gerado diariamente pelo script `gerar_risco_cliente.py`. Ver metodologia completa abaixo.

## Metodologia — Risco de Inadimplência por Cliente

Objetivo: identificar, toda semana, clientes cujo saldo devedor (títulos a receber em aberto) está crescendo rápido demais dia a dia, como sinal de possível inadimplência.

**Escopo**: unidades de negócio 3, 4 e 5 (constante `UNIDADES = (3, 4, 5)`). O relatório publicado tem um **filtro de unidade de negócio** (checkboxes "Unidade 3" / "Unidade 4" / "Unidade 5", todas marcadas por padrão) que recalcula tudo no navegador — saldo diário combinado, crescimento médio, flag de risco e KPIs — considerando apenas as unidades selecionadas naquele momento. O script Python busca e envia ao HTML o saldo diário **separado por unidade** para cada cliente (mais a média de compra semanal por unidade); a agregação/soma das unidades escolhidas e todo o recálculo do critério de risco acontecem 100% em JavaScript, sem nova consulta ao banco.

### Passo 1 — janela da semana atual
```python
segunda = hoje - timedelta(days=hoje.weekday())   # segunda-feira da semana corrente
dias = [segunda, segunda+1, ..., hoje]             # inclusive, de segunda até hoje
```

### Passo 2 — reconstrução do saldo devedor dia a dia, por unidade
Para cada cliente **e cada unidade** (3, 4, 5 separadamente), junta dois conjuntos de títulos a receber (`TREC_RECEBER_PAGAR_FK = 'R'`):
- **`TREC_ABERTO`**: todos os títulos ainda em aberto hoje (sem data de baixa). Usa `TREC_SALDO_TITULO` (saldo já líquido de eventuais pagamentos parciais em títulos com situação `PP`), não `TREC_VALOR_TITULO` — usar o valor cheio nesse caso supervaloriza o saldo de títulos parcialmente pagos.
- **`TREC_BAIXADO`**: títulos já pagos, mas apenas os baixados nos últimos ~95 dias antes da segunda-feira da semana analisada (janela de performance — títulos pagos há mais tempo não poderiam estar em aberto em nenhum dia da semana atual de qualquer forma).

Saldo de um cliente/unidade em uma data de referência `d`:
```python
saldo_em(titulos, d) = soma do valor de cada título onde:
    data_emissao <= d  E  (nunca_foi_pago OU data_baixa > d)
```
Ou seja: título conta como "em aberto naquele dia" se já tinha sido emitido e, ou nunca foi pago, ou só foi pago **depois** daquela data (estava aberto naquele momento, mesmo que hoje já esteja quitado). O script grava, para cada cliente, um array de saldo diário por unidade (`unidades: {"3": [...], "4": [...], "5": [...]}`) — é esse array bruto que o HTML publicado usa para recalcular tudo conforme o filtro de unidade escolhido.

### Passo 3 — crescimento diário (recalculado no navegador conforme o filtro)
No JavaScript do relatório, para as unidades atualmente marcadas no filtro, soma-se o saldo diário de cada unidade selecionada em um único array de "saldo combinado" do cliente, dia a dia. Depois, para cada par de dias consecutivos da semana:
```
base = saldoCombinado(dia anterior)
if base > 50.00:   # SALDO_MINIMO_BASE — ignora bases pequenas para não gerar % explosivos por ruído
    crescimento = (saldoCombinado(dia) - base) / base
```
`crescimentoMedio` = média aritmética simples de todos os crescimentos diários válidos da semana, **para a combinação de unidades atualmente selecionada**. Se nenhum dia teve base > R$50 (ou o cliente não tem nenhum título nas unidades selecionadas), o cliente **não tem `crescimentoMedio` válido e é excluído da tabela** — não aparece como 0% nem como não-risco, simplesmente não é listado enquanto aquele filtro estiver ativo. Trocar o filtro pode fazer clientes aparecerem/desaparecerem e o "risco" de um cliente mudar, já que a base de cálculo muda.

### Passo 4 — critério de risco
```python
risco = crescimentoMedio > 0.20   # estritamente maior que 20%, não "maior ou igual"
```

### Contexto adicional — média de compras semanais (não entra no critério de risco)
Para cada cliente **e cada unidade**, calcula a média de valor de pedidos por semana nas últimas 13 semanas (`YEARWEEK(..., modo ISO)`, excluindo pedidos cancelados), **dividido sempre por 13** (não pelo número de semanas com pedido de fato — clientes novos ou com poucas semanas ativas terão essa média artificialmente reduzida). Ao aplicar o filtro de unidade, o valor exibido é a soma da média das unidades selecionadas. Serve apenas como referência de porte do cliente na tabela, não afeta se ele é marcado como risco.

### Filtro de unidade de negócio
Checkboxes "Unidade 3 / 4 / 5" no topo do relatório, todas marcadas por padrão. Cada mudança de seleção dispara uma nova renderização completa (`renderizar()`): recombina os saldos diários das unidades marcadas por cliente, recalcula `crescimentoMedio`/`saldoAtual`/`mediaCompraSemanal`/`risco` para cada um, reordena e reconstrói KPIs + tabela — tudo client-side, sem nova consulta ao banco. Desmarcar todas as unidades mostra uma mensagem pedindo para selecionar ao menos uma, sem tentar renderizar uma tabela vazia.

### Saída publicada (`risco-cliente.html`)
- Cabeçalho com data/hora de geração, semana analisada e as unidades atualmente selecionadas no filtro.
- Caixa de metodologia (versão resumida, em português simples, visível a qualquer usuário do painel).
- Filtro de unidade de negócio (3/4/5).
- 3 KPIs: nº de clientes em risco, nº de clientes analisados, soma do saldo devedor dos clientes em risco — todos recalculados conforme o filtro ativo.
- Tabela com **todos** os clientes analisáveis da semana para o filtro ativo (risco e não-risco), ordenados por `crescimentoMedio` decrescente — clientes em risco destacados em vermelho com tag "⚠️ RISCO". Colunas: cliente, saldo devedor atual, crescimento médio diário, evolução do saldo dia a dia (segunda → hoje), média de compra semanal (13 semanas).
- O relatório só reflete a última execução da tarefa agendada (a busca no banco e a montagem dos dados brutos por unidade) — o filtro em si é interativo e roda inteiramente no navegador, sem consulta ao vivo.
