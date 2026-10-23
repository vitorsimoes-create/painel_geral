# Pipeline de dados — como o painel é atualizado

O painel é **100% estático**: o navegador não consulta banco nenhum. Todo número exibido é um
**snapshot** gravado dentro dos arquivos publicados (`index.html`, `dados-*.js` e as páginas em
iframe), regerado pela rotina diária e publicado no GitHub Pages.

```
 mc_moto (ERP MC MOTO) ─┐
 projeto_f7 (Proton) ───┼──► geradores Python locais ──► index.html / dados-*.js / *.html / *.json ──► git push ──► GitHub Pages
 Bling RHS (API) ───────┘      (gerar_*.py, atualizar_mapa.py)        (pasta MC MOTO)                             (vitorsimoes-create.github.io/painel_geral)
```

De onde vem cada campo de cada aba: [`08-origem-dos-dados.md`](08-origem-dos-dados.md).

---

## 1. Quem dispara a atualização

### 1.1 Rotina diária `atualizacao-diaria-painel` (a única)

| Item | Valor |
|---|---|
| Onde está | Tarefa agendada do Claude (app desktop). Prompt em `C:\Users\Vitor\.claude\scheduled-tasks\atualizacao-diaria-painel\SKILL.md` |
| Quando | Todo dia às **09:00**, com até ~13 min de atraso aleatório (cron `0 9 * * *`) |
| Condição | **Só roda com o app do Claude aberto** na máquina do Vitor. Dia sem app aberto = dia sem atualização (aparece como dia sem commit no GitHub) |
| O que faz | Roda os geradores dos três bancos na ordem da seção 2, valida o JavaScript de cada arquivo e publica **um único commit** |
| Mensagem do commit | `Atualização diária automática do painel (MC MOTO + SEVEN)` |

**Regra estrutural (decisão do usuário de 20/07/2026):** existe **exatamente uma** rotina diária.
Toda aba nova alimentada por qualquer banco entra **nesta** rotina — edita-se o `SKILL.md` e este
documento; nunca se cria uma segunda rotina.

O `SKILL.md` é o roteiro que a rotina executa. **Este documento e o `SKILL.md` têm de descrever a
mesma coisa**: quem mudar um, muda o outro.

### 1.2 Rotina semanal `novidades-semanais-painel`

| Item | Valor |
|---|---|
| Quando | Toda **sexta-feira às 08:00** (cron `0 8 * * 5`) |
| O que faz | Lê os commits da semana (sexta a quinta), escreve a edição em linguagem de usuário no topo do array `EDICOES` de `novidades.html`, commita só esse arquivo e grava o texto pronto para WhatsApp em `novidades_whatsapp.txt` (não versionado) |
| Regra | Commits "Atualização diária automática" não são novidade; servem para achar dia sem atualização ou aba com problema, que vira item de **aviso** |
| Não faz | Não envia mensagem a ninguém — quem envia é o usuário |

### 1.3 Tarefas do Windows ligadas ao painel

| Tarefa | Estado | Observação |
|---|---|---|
| `MapaVendasMCMoto_Atualizacao19h` | **Desativada** | Rodava `atualizar_mapa.py` às 19h. Ficou travada ~3 dias em jul/2026 (erro 0x800710E0, dependia de logon) e foi substituída pelo passo A6 da rotina diária. Não religar |
| `DiagCargaContasReceber_0750` / `_1550` | Execução única (15/10/2026) | Diagnóstico da carga de `contas_receber` da MC MOTO (`_diag_1054.cmd`). Não têm próxima execução |

---

## 2. Ordem de execução

A ordem **importa**: vários geradores leem o que o anterior acabou de gravar. A coluna
"Depende de" diz o porquê. Todos rodam com `C:\Python314\python.exe`, na pasta `MC MOTO`.

| Passo | Script | Banco | Grava | Depende de | Aborta sem gravar se… |
|---|---|---|---|---|---|
| **A0 / B0** | `gerar_bling_un4.py` | Bling RHS (+ `projeto_f7` para descartar o que já está no ERP) | `bling-un4.json` (congelado), `bling-un4-hoje.json` (foto), `_bling_forn_cache.json` | — | a conta do Bling não for a da RHS (CNPJ conferido) |
| A3 | `gerar_raw_data_mcmoto.py` | `mc_moto` | `dados-mc.js`: `RAW_DATA`, `GRUPO_NOMES_MC`, `SUBGRUPO_NOMES_MC`, `MARCA_NOMES_MC`, `UV_DESDE_MC`; `index.html`: data do cabeçalho | — | < 90% dos itens casados, < 80% com fornecedor, ou nenhum item com pico/estoque |
| A3b | `gerar_recebimentos_mcmoto.py` | `mc_moto` | `dados-mc.js`: `RECEBIMENTOS_DB`, `CMV_MENSAL` | — | < 50 notas ou < 12 meses de CMV |
| A4 | (checagem manual) | — | — | A3 | `k` de 3 itens sorteados não for o de **um** mês só |
| A6 | `atualizar_mapa.py` | `mc_moto` + `projeto_f7` + `bling-un4*.json` | `Mapa de Vendas.html` → cópia em `mapa-vendas.html` com `.tabs{display:none!important}` | **A0** (senão Seven Contagem sai um dia atrasada) | — (erro vai para `atualizar_mapa.log`) |
| A7 | cópia de `painel_caixa feito.html` | — | `painel-caixa.html` | só se o arquivo local mudou | — |
| A7b | `gerar_receb_itens_mcmoto.py` | `mc_moto` | `dados-mc.js`: `RECEB_ITENS_DB` | A3b (mesmos ids) | < 20 notas com itens |
| A8 | `gerar_contas_receber_mcmoto.py` | `mc_moto` | `contas-receber-mcmoto.html` | — | — |
| A9 | `gerar_vendas_historicas_mcmoto.py` | `mc_moto` | `vendas-historicas.html` | — | — |
| A10 | `gerar_vendas_comissao_mcmoto.py` | `mc_moto` | `vendas-comissao.html` | — | — |
| A11 | `gerar_graficos_mcmoto.py` | `mc_moto` | `graficos-mcmoto.html` | — | — |
| A12 | `gerar_monitor_fechamento_mcmoto.py` | `mc_moto` | `monitor-fechamento-mcmoto.html` + `monitor_fechamento\snapshot_AAAA-MM-DD.json` | snapshot do dia anterior | — |
| A13 | `gerar_posicao_caixa_mcmoto.py` | `mc_moto` | `posicao-caixa-mcmoto.html` | — | — |
| B1 | `gerar_risco_cliente.py` | `projeto_f7` | `risco-cliente.html`, `atualizar_risco.log` | — | — (segunda-feira com "0 clientes" é esperado) |
| B2 | `gerar_raw_data_seven.py` | `projeto_f7` + `bling-un4*.json` | `dados-seven.js`: `RAW_DATA_SEVEN`, `GRUPO_NOMES_SEVEN`, `SUBGRUPO_NOMES_SEVEN`, `UV_DESDE_SEVEN` | A0 | — (se o total cair para ~18.600 itens, o filtro de inativo voltou por engano) |
| B2b | `gerar_recebimentos_seven.py` | `projeto_f7` + Bling | `dados-seven.js`: `RECEBIMENTOS_SEVEN`, `CMV_MENSAL_SEVEN` (por empresa) | A0 | < 50 notas |
| B2c | `gerar_receb_itens_seven.py` | `projeto_f7` + Bling | `dados-seven.js`: `RECEB_ITENS_SEVEN_DB` | **B2b** (mesmos ids) | < 100 notas com itens |
| B2d | `gerar_dashboard.py` | `mc_moto` + `projeto_f7` + Bling | `index.html`: `DASHBOARD_DB`, `PARAMS_PUB` (cópia de `parametros-painel.json`) | **A3 e B2** (estoque parado lê `dados-*.js`) | histórico < 6 meses |
| B2e | `gerar_clientes.py` | `mc_moto` + `projeto_f7` | `clientes-mcmoto.html`, `clientes-seven.html` | — | < 50 clientes em qualquer empresa |
| B2f | `gerar_relatorio.py` | `mc_moto` + `projeto_f7` + Bling | `relatorio-mcmoto.html`, `relatorio-seven.html`, `relatorio-historico.json`, `index.html`: `DRE_DESPESAS` | **B2d** | — |
| B2g | `gerar_forn_real_mcmoto.py` e `gerar_forn_real_seven.py` | `mc_moto` / `projeto_f7` | `index.html`: `FORN_REAL_*`, `FORN_JUNTOS_*` | **A3 e B2** (reescrevem o campo `f`) | nenhum item resolvido |
| B2h | `gerar_premiacao.py` | `projeto_f7` + Bling | `premiacao-seven.html` | A0 | — |
| B2h' | `gerar_agenda_compras.py` | `mc_moto` + `projeto_f7` | `index.html`: `AGENDA_COMPRAS_MC/SEVEN`, `COMPRAS_MES_MC/SEVEN` | — | histórico vazio em qualquer empresa |
| B2i | `gerar_cadastro_clientes.py` | `projeto_f7` | `cadastro-clientes-seven.html` | — | — |
| B2i' | `gerar_transferencia_seven.py` | `projeto_f7` | `dados-seven.js`: `TRANSF_EXTRA_SEVEN` | **B2** (só grava o que falta no `RAW_DATA_SEVEN`) | complemento vazio |
| B2j | `gerar_premiacao_mcmoto.py` | `mc_moto` | `premiacao-mcmoto.html` | — | — |
| B3 | `gerar_contas_seven.py` | `projeto_f7` + Bling | `contas-pagar-seven.html`, `contas-receber-seven.html` | A0 | — |
| B3b | `gerar_posicao_caixa.py` | `projeto_f7` | `posicao-caixa-seven.html` | — | — |
| A5 / B4 | validação de sintaxe | — | — | todos | qualquer arquivo com JS inválido **não é publicado** |
| F1–F3 | publicação (seção 4) | — | commit + push | A5/B4 | — |

> Os nomes B2h' e B2i' não existem no `SKILL.md`: lá os dois passos aparecem repetidos como
> "B2h" e "B2i" (Agenda e Transferência). A ordem acima é a que a rotina executa.

### 2.1 O coletor do Bling (passo A0)

`gerar_bling_un4.py` é o único programa que fala com o Bling. Ele roda **antes de tudo** porque
oito geradores leem os arquivos que ele grava, através do adaptador `_un4.py`.

- **Sem argumento**, relê os **últimos 45 dias até ontem**. Isso pega pedido que virou
  *Atendido* depois, lançamento retroativo, cancelamento e dia em que a rotina não rodou. Os
  dias relidos são **substituídos** em `bling-un4.json`.
- **Custo congelado:** o Bling só guarda o custo de hoje (`precoCusto` do cadastro). Pedido já
  lido mantém o custo da primeira leitura; só item novo pega o custo do dia. Para recalcular de
  propósito: `gerar_bling_un4.py --refazer AAAA-MM-DD`.
- **Faturado = só pedido na situação Atendido (9).** O script imprime quanto ficou de fora por
  situação.
- **Fica de fora o que veio das cargas Proton → Bling** (pedido com `numeroPedidoCompra` U3-/U4-,
  título com "Proton" ou "[F7-U4-" no histórico, título a receber sem `idOrigem` emitido antes do
  corte) — senão o movimento que o ERP já tem seria contado duas vezes.
- **Reprocessar um período:** `gerar_bling_un4.py 2026-09-29 2026-09-30`.
- **Conferência de sanidade:** o estoque a custo do Bling tem de ficar perto do estoque da
  unidade 4 no ERP (em 30/09/2026: 2,0% de diferença).

### 2.2 Regras de execução que não podem ser quebradas

1. **Nunca reescrever a lógica de um gerador em script temporário.** Em 23/07/2026 um script
   escrito à mão gravou fornecedor nulo, estoque 0 e pico 0 nos 18.945 itens e a aba Montar Pedido
   ficou vazia em produção. Se um gerador falhar, leia o erro e corrija **o gerador**.
2. **Se um gerador abortar por sanidade, não publique** os arquivos dele: investigue conexão e
   consulta primeiro.
3. **Pico é o máximo mensal, nunca a soma.** Para a unidade 4, o mês de setembro/2026 está partido
   entre ERP (1 a 28) e Bling (29 e 30): os dois são **somados antes** de tirar o máximo.
4. **`TPAG_BAIXADO` sempre deduplicado** (a tabela do espelho repete cada título ~66×).
5. **Nenhum gerador inventa número da unidade 4 depois de 28/09:** ou soma o Bling, ou corta o
   ERP. Os que ainda não somam o Bling estão listados na seção 12 do
   [`08-origem-dos-dados.md`](08-origem-dos-dados.md).

---

## 3. Validação antes de publicar

Cada arquivo alterado tem a sintaxe do JavaScript conferida com Node:

```bash
node -e "new Function(require('fs').readFileSync('index.html','utf-8').match(/<script>([\s\S]*?)<\/script>/)[1])"
```

```bash
node -e "new Function(require('fs').readFileSync('dados-mc.js','utf-8'))"
```

O mesmo vale para `dados-seven.js`, `mapa-vendas.html` e cada página gerada. Arquivo com erro de
sintaxe **não entra no commit**.

---

## 4. Publicação (F1–F3)

1. `git status` e conferir que **só** estes arquivos mudaram: `index.html`, `dados-mc.js`,
   `dados-seven.js`, `mapa-vendas.html`, `painel-caixa.html`, `contas-receber-mcmoto.html`,
   `vendas-historicas.html`, `vendas-comissao.html`, `graficos-mcmoto.html`,
   `monitor-fechamento-mcmoto.html`, `risco-cliente.html`, `contas-pagar-seven.html`,
   `contas-receber-seven.html`, `posicao-caixa-seven.html`, `posicao-caixa-mcmoto.html`,
   `clientes-mcmoto.html`, `clientes-seven.html`, `relatorio-mcmoto.html`, `relatorio-seven.html`,
   `relatorio-historico.json`, `premiacao-seven.html`, `premiacao-mcmoto.html`,
   `cadastro-clientes-seven.html`, `bling-un4.json`.
2. `git add` **arquivo por arquivo**, nunca `git add -A` nem `git add .`.
3. Um commit único com a mensagem padrão e `git push`.
4. Sem mudança nenhuma: não cria commit vazio.

**Nunca vão para o git:** `conexaomc.md` (credenciais), `gerar_*.py`, `atualizar_mapa.py`,
`_*.py`, `*.log`, `Mapa de Vendas.html` (o original, com espaço), `painel_caixa feito.html`,
`bling-un4-hoje.json`, `_bling_forn_cache.json`, `monitor_fechamento\`, `.env.email`,
planilhas `.xlsx`. O `.gitignore` já barra todos.

---

## 5. Arquivos de estado — nunca apagar

| Arquivo | Por quê |
|---|---|
| `bling-un4.json` | CMV da unidade 4 com custo congelado; apagar faz o CMV dos meses fechados mudar sozinho |
| `relatorio-historico.json` | Fechamento mensal gravado no dia 1; o histórico se perde |
| `monitor_fechamento\snapshot_*.json` | O comparativo de cada dia depende do snapshot do dia anterior |
| `parametros-painel.json` | Único lugar publicado do que o usuário digita; só se atualiza com o texto do botão "Exportar parâmetros" enviado pelo usuário |

---

## 6. Quando algo dá errado

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `Can't connect to MySQL server on '187.127.22.30' (timed out)` | servidor dos bancos fora do ar | Esperar e rodar de novo; não publicar meia atualização. Aconteceu em 23/10/2026 às 15:41 |
| Gerador abortou por sanidade | consulta voltou vazia ou degenerada | Não publicar; conferir conexão e a consulta |
| Seven Contagem um dia atrasada no Mapa | `atualizar_mapa.py` rodou antes do `gerar_bling_un4.py` | Rodar A0 e depois A6 de novo (aconteceu de 30/09 a 09/10/2026) |
| Seven Ipatinga parada no Mapa ("ate AAAA-MM-DD" antigo no `atualizar_mapa.log`) | espelho `projeto_f7` sem carga | Não é erro do painel; o Relatório Gerencial mostra o aviso. Em 23/10/2026 estava parada desde 16/10 e voltou no mesmo dia |
| "sem regra de colapso por empresa" no log | chave nova no payload sem regra RHS/SEVEN | Acrescentar a regra em `_emp_payload.REGRAS` (explícita, nunca inferir) |
| "AVISO: caixa … não carregado" no dashboard | `buscar()` da Posição de Caixa falhou | O dashboard volta à regra antiga; investigar a Posição de Caixa |
| Montar Pedido vazio | gerador de catálogo escrito à mão ou com casamento de código errado (`'002275'` × `2275`) | Restaurar o arquivo do último commit bom e rodar o gerador fixo |
| Dia sem commit no GitHub | app do Claude fechado às 09:00, ou rotina falhou | Rodar a rotina à mão ("Run now" na tarefa) |

---

## 7. Rodar à mão

Qualquer passo pode ser rodado sozinho, fora de hora, respeitando as dependências da seção 2.
A maioria aceita `--dry-run` (relata sem gravar). Exemplo para refrescar só a SEVEN:

```bash
C:\Python314\python.exe gerar_bling_un4.py
```

```bash
C:\Python314\python.exe gerar_raw_data_seven.py
```

Depois, validar a sintaxe (seção 3) e publicar (seção 4).

---

## 8. O que **não** é atualizado pela rotina

| Item | Como é mantido |
|---|---|
| `crm-seven.html` (RHS/SEVEN › CRM › CRM) | Arquivo estático de 24/07/2026, sem gerador |
| `painel-caixa.html` (dentro de Contas a Pagar da MC MOTO) | Cópia de `painel_caixa feito.html`, que é feito à parte; a rotina só copia quando ele muda |
| `parametros-painel.json` | Manual, com o texto exportado pelo usuário |
| `USUARIOS_PADRAO` (usuários e senhas do painel) | Manual, pelo master ("Copiar configuração para publicar") |
| `cotacoes/` (formulários de cotação para fornecedor) | Publicação manual, uma por cotação |
| E-mail diário de faturamento da MC MOTO (`gerar_faturamento_email_mcmoto.py`) | Pronto, **não agendado**: falta a credencial SMTP em `.env.email` |
| `Painel Geral.exe` (`dist_colaboradores\`, fonte `abrir_painel.py`) | Só abre a URL publicada; nunca precisa ser trocado |

---

## 9. Histórico das mudanças no fluxo

| Data | Mudança |
|---|---|
| 20/07/2026 | Uma rotina só para os dois bancos; o Mapa passa a ser gerado na rotina (fim da tarefa das 19h) |
| 23/07/2026 | Fim do script escrito à mão para o `RAW_DATA`: entra `gerar_raw_data_mcmoto.py` com sanidade |
| 28/08/2026 | Recebimentos da MC MOTO viram script fixo, com valor `TOTAL + OUTRAS_DESP` |
| 02/09/2026 | Recebimentos da SEVEN passam a vir de `TENT_ENTRADA` (antes eram reconstruídos dos títulos) |
| 28/09/2026 | Dados de Compras saem do `index.html` para `dados-mc.js` / `dados-seven.js` |
| 30/09/2026 | Unidade 4 passa a vir do Bling RHS (`gerar_bling_un4.py`, passo A0/B0) |
| 09/10/2026 | Coletor do Bling relê 45 dias; só pedido Atendido conta; A0 vai para antes do Mapa |
| 14/10/2026 | Painel passa a falar em empresa (RHS = 3+4, SEVEN = 5); colapso em `_emp.py` / `_emp_payload.py` |
| 16/10/2026 | Recebimentos da RHS vêm do Bling (pedido Atendido + NF registrada); meta por empresa |
| 23/10/2026 | MC com desconto fixo de 7% em todo o painel (`venda × 0,93 − CMV`) |
