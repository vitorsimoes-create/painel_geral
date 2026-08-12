# Visão Geral do Painel MC MOTO / RHS-SEVEN

## O que é

Painel interno de gestão para a **MC MOTO** (varejo de peças/acessórios para motos) e para o grupo **RHS/SEVEN** (unidades de negócio relacionadas). É uma aplicação **estática** (HTML + CSS + JS puro, sem backend/servidor próprio), publicada via **GitHub Pages** a partir do repositório [`vitorsimoes-create/painel_geral`](https://github.com/vitorsimoes-create/painel_geral), branch `main`.

Não há API nem banco de dados acessado em tempo real pelo navegador. Todos os dados que o painel exibe são **snapshots gerados periodicamente** por scripts Python locais (rodando na máquina do usuário via tarefas agendadas) e depois "gravados" diretamente dentro dos arquivos HTML publicados. Ver [`06-pipeline-dados.md`](06-pipeline-dados.md) para o fluxo completo de atualização.

## Arquitetura de arquivos

| Arquivo | Papel | Como é gerado/atualizado |
|---|---|---|
| `index.html` | App principal — todo o shell de navegação, controle de acesso, e as abas de **Compras** (Montar Pedido, Cotação, Pedidos Salvos, Recebimentos) | Editado manualmente (features) + reescrita diária automática dos dados (`RAW_DATA`, `RECEBIMENTOS_DB`, `CMV_MENSAL`) por tarefa agendada |
| `mapa-vendas.html` | Iframe embutido em `index.html`, cobre as abas de **Vendas**, **Financeiro → Contas a Pagar** (MC MOTO) e **Unidades de Negócio** (RHS/SEVEN) | É uma **cópia sincronizada** de `Mapa de Vendas.html` (ver abaixo) — nunca editado diretamente |
| `Mapa de Vendas.html` | Arquivo **original**, fonte de verdade do conteúdo acima | Gerado do zero a cada execução do script local `atualizar_mapa.py` (agendado no Windows Task Scheduler). **Nunca deve ser editado à mão** — qualquer mudança de conteúdo tem que ir no template Python e o script tem que ser rerodado |
| `crm-seven.html` | Iframe embutido, aba RHS/SEVEN → CRM | Arquivo separado, não coberto em detalhe nesta documentação |
| `risco-cliente.html` | Iframe embutido, aba RHS/SEVEN → Financeiro → Risco/Cliente | Gerado diariamente pelo script `gerar_risco_cliente.py` |

Regra crítica de manutenção: **`Mapa de Vendas.html` (com espaço no nome) nunca é commitado nem editado diretamente.** Toda mudança de conteúdo do Mapa de Vendas precisa: (1) alterar o template dentro de `atualizar_mapa.py`, (2) rerodar o script para regenerar `Mapa de Vendas.html`, (3) copiar o resultado para `mapa-vendas.html` (nome sem espaço, esse sim publicado), reaplicando o ajuste de CSS `.tabs{display:none!important}` (a barra de abas nativa do arquivo é escondida porque a navegação é controlada de fora, pelo `index.html`), (4) commitar apenas `mapa-vendas.html`.

## Estrutura de navegação

Há dois níveis principais de agrupamento, mais sub-níveis dentro de cada um.

### Nível 1 — Grupo (`switchGrupo`, em `index.html`)

Dois grupos:
- **🏍️ MC MOTO** (`grupobtn-mcmoto`, padrão ao abrir o painel)
- **🏢 RHS/SEVEN** (`grupobtn-rhsseven`)

Cada clique passa primeiro pelo gate de senha (ver seção abaixo) antes de trocar de conteúdo.

### Nível 2 — Categorias / sub-abas

**Dentro de MC MOTO** (`switchCategoriaMcMoto`, pills em `#categorias-mcmoto`):
- 🛍️ **Compras** (`compras`, categoria padrão) → abre a aba nativa "Montar Pedido" dentro do próprio `index.html`, com sub-abas internas: Montar Pedido, Cotação, Pedidos Salvos, Recebimentos.
- 📈 **Vendas** (`vendas`) → as 5 primeiras sub-abas são deep-links para dentro do iframe `mapa-vendas.html` (`abrirSubAbaMapa`): Painel Mensal, Vendas Diárias, Grupo de Produto, Consistência por Grupo, Venda por Fornecedor. As últimas três são abas nativas de `index.html` com iframe próprio: **Vendas Históricas** (`vendas-historicas.html`, `abrirSubAbaVendasHist`), **Vendas por Grupo de Comissão** (`vendas-comissao.html`, `abrirSubAbaVendasComissao`) e **Gráficos** (`graficos-mcmoto.html`, `abrirSubAbaGraficos` — painel consolidado de gráficos SVG dos últimos 12/24 meses).
- 💰 **Financeiro** (`financeiro`) → duas sub-abas: **Contas a Pagar** (deep-link para dentro do iframe `mapa-vendas.html`, que inclui também o Painel de Caixa embutido via `painel-caixa.html`) e **Contas a Receber** (aba nativa de `index.html` com iframe próprio, `contas-receber-mcmoto.html`, aberta por `abrirSubAbaFinanceiroMc`).

**Dentro de RHS/SEVEN** (`abrirSubAbaRHSSeven`, botões em `#subtabs-rhsseven`):
- 🏢 **Unidades de Negócio** (`unidades`, padrão) → **também** é um deep-link para dentro do mesmo iframe `mapa-vendas.html` (chama `trocarAba('unidades')`) — ou seja, é o mesmo arquivo/iframe usado pela aba Vendas da MC MOTO, só que mostrando dados agregados por unidade de negócio (banco `projeto_f7`).
- 👥 **CRM** (`crm`) → mostra o iframe separado `crm-seven.html`.
- 💰 **Financeiro** (`financeiroseven`) → mostra um painel nativo de `index.html` com 3 pills (`switchCategoriaFinanceiroSeven`): Contas a Pagar (placeholder "Em breve"), Contas a Receber (placeholder "Em breve"), Risco/Cliente (iframe `risco-cliente.html`, funcional).

Se o iframe `mapa-vendas.html` ainda não terminou de carregar quando o usuário clica em uma sub-aba que depende dele, o `index.html` guarda o alvo pendente em `_mapaTabPendente` e dispara a troca assim que o evento `load` do iframe ocorre.

## Controle de acesso (usuários e permissões de aba)

Reformulado em 29/07/2026: antes eram 3 senhas fixas (MC MOTO / RHS-SEVEN / admin); agora há **usuários nomeados, cada um com sua senha e a lista de abas que enxerga**, gerenciados por um usuário **master**.

- O overlay `#lock-overlay` continua exigindo senha ao carregar. **A senha identifica o usuário** (cada um tem a sua, e o sistema recusa senhas duplicadas), então o campo de login segue com um único input.
- Cadastro publicado na constante `USUARIOS_PADRAO` de `index.html`: `{id, nome, senha, master, abas[]}`. Vem com o **master**, os dois usuários antigos preservados (o antigo "MC MOTO", hoje renomeado para **DIOGO**, com acesso total à MC MOTO; RHS/SEVEN com as 6 da SEVEN — as senhas antigas continuam valendo) e **5 usuários vazios** prontos para o master configurar.
- **Catálogo de abas** em `ABAS_CATALOGO`: 20 chaves (`mc.montar`, `mc.graficos`, `sv.compras`, `sv.fin.risco`…), cada uma com grupo, categoria, rótulo e o seletor do botão correspondente. É a única fonte de verdade — **ao criar uma aba nova no painel, adicione a chave aqui**, senão ela não aparece na tela de permissões.
- **Acesso total à MC MOTO (`todasAbasMc: true`)** — 12/08/2026: o usuário **DIOGO** (`u_mc`, ex-"MC MOTO") não tem mais lista fixa de abas. Com esse flag, `abasDoUsuario()` monta as abas da MC MOTO a partir do `ABAS_CATALOGO`, então **toda aba nova da MC MOTO já nasce liberada para ele** — basta registrar a chave no catálogo, sem voltar na tela de usuários. A lista `abas[]` desses usuários guarda só o que for de fora da MC MOTO (ex.: RHS/SEVEN). O flag é uma decisão **publicada**: `_herdarAcessoTotalMc()` o reaplica por `id` sobre a configuração que o navegador tiver em cache, para a pessoa receber as abas novas mesmo sem link de acesso novo. Na tela de gestão ele aparece como a chave "Acesso total à MC MOTO" e, quando ligado, os checkboxes da MC MOTO ficam marcados e travados (são o catálogo, não uma escolha).
- `aplicarPermissoes()` esconde o que não é permitido em cascata: botões de sub-aba, as categorias da MC MOTO (COMPRAS/VENDAS/FINANCEIRO), as pills do Financeiro da SEVEN e os próprios botões de grupo — e leva o usuário para a primeira aba liberada. `switchGrupo`/`switchCategoriaMcMoto`/`switchCategoriaFinanceiroSeven` também barram navegação forçada.
- Um usuário **sem nenhuma aba liberada não consegue entrar** (mensagem orientando procurar o master). O master tem sempre acesso total — não é possível restringi-lo.
- Sessão em `sessionStorage` (`painel_usuario` = id do usuário); há badge com o nome e botão **Sair** no cabeçalho.
- **Tela de gestão** (botão 👥 Usuários, só aparece para o master): criar/renomear/excluir usuários, trocar senha e marcar as abas por checkbox (com "marcar todas"/"limpar" por empresa).
- **Permissão por unidade de negócio da SEVEN** (`unidades: ['3','4','5']` no usuário, constante `UNIDADES_SEVEN`): além das abas, o master escolhe quais unidades cada usuário enxerga. `aplicarUnidadesPermitidas()` aplica em três frentes — (1) os checkboxes 3/4/5 do **Compras SEVEN** (esconde e desmarca as bloqueadas, e ajusta `unidadesSelecionadasSeven`, inclusive no botão "Limpar"); (2) os iframes do **Financeiro** (contas a pagar/receber e risco), onde esconde os `.filtro-unidade` bloqueados e dispara o `change` para recalcular — com retry, pois o iframe pode não ter carregado ainda; (3) o `<select id="uni-filtro">` da aba **Unidades de Negócio** no Mapa, escondendo as opções bloqueadas e, quando sobra só uma unidade, travando o filtro nela (some o "Todas"). A função é **idempotente**: reexibe o que voltou a ser permitido. Regra de segurança contra travamento: usuário **sem** a chave `unidades` (config antiga) ou com lista vazia enxerga **todas** as unidades; valores inexistentes são ignorados; o master nunca é restringido.
- ⚠️ **Onde as alterações valem:** o master edita ao vivo e o resultado é gravado em `localStorage` (`painel_usuarios_cfg`) — ou seja, **vale só naquele navegador**. Isso já causou um problema real (30/07/2026): os 5 usuários novos estavam publicados com 0 abas, o master configurou os acessos na máquina dele e **as outras pessoas continuavam com o login recusado**, porque o navegador delas carregava o `USUARIOS_PADRAO` publicado. Há duas formas de distribuir:
  1. **🔗 Gerar link de acesso** (recomendado, não depende de publicação): monta uma URL `…/index.html#cfg=<base64>` com a configuração inteira. Quem abre o link **uma vez** tem a configuração gravada no próprio navegador (`importarCfgDoLink()`), a URL é limpa na hora via `history.replaceState` para as senhas não ficarem na barra de endereço, aparece a confirmação verde no login e a pessoa passa a entrar só com a senha dela, inclusive em visitas futuras. O link **contém as senhas** — enviar apenas para a equipe. Um link válido é rejeitado se o conteúdo não for uma lista de usuários com `id` e `senha`.
  2. **📋 Copiar configuração para publicar** — gera o bloco `const USUARIOS_PADRAO=[...]` para colar no `index.html` e publicar; aí vale para todo mundo sem precisar de link.
  "↺ Restaurar publicado" descarta o override local e volta ao que está no arquivo.
- **Isto não é segurança real.** É um "deterrent" client-side — qualquer pessoa com acesso ao código-fonte (Ctrl+U) vê as senhas em texto simples. Serve para organizar o acesso da equipe, não para proteger dados de alguém mal-intencionado. Segurança de verdade exigiria backend com autenticação.

## Regras de manutenção que já regem este projeto

Estas regras vieram de decisões explícitas ao longo do desenvolvimento e devem ser respeitadas por qualquer pessoa (ou IA) que mexer no projeto:

1. **Nunca editar `Mapa de Vendas.html` diretamente.** É saída de `atualizar_mapa.py`; qualquer mudança de conteúdo vai no template Python.
2. **Nunca commitar `Mapa de Vendas.html`** (o original, com espaço no nome) nem arquivos sensíveis da pasta (ex.: `conexaomc.md`, que guarda credenciais de banco, planilhas locais). Apenas `mapa-vendas.html` (cópia sincronizada, sem espaço) é versionado.
3. **`git add` sempre por nome de arquivo explícito**, nunca `git add -A` ou `git add .` — a pasta de trabalho tem arquivos sensíveis não rastreados que não podem ser commitados por acidente.
4. **Scripts Python de exploração pontual** devem ter prefixo `_` (ex.: `_teste_algo.py`) e ser apagados depois de usados; scripts que rodam de forma recorrente/agendada (ex.: `atualizar_mapa.py`, `gerar_risco_cliente.py`) ficam sem prefixo, mas **permanecem apenas locais** — não são commitados no git.
5. **Acesso a bancos de dados é restrito ao escopo já autorizado.** Qualquer nova fonte de dados exige credenciais fornecidas explicitamente pelo usuário — nunca assumir acesso a um banco/tabela novo.
6. Após qualquer atualização do painel publicado (`index.html` e arquivos relacionados), o padrão é **sempre fazer `git push` automaticamente**, sem precisar perguntar.
