# -*- coding: utf-8 -*-
"""
Alimenta a aba RHS/SEVEN > Compras > Recebimentos, gravando no index.html:
  const RECEBIMENTOS_SEVEN = [...]   -> notas de fornecedor dos ultimos 12 meses
  const CMV_MENSAL_SEVEN = {...}     -> CMV por mes (usado como meta automatica)

DIFERENCA IMPORTANTE PARA A MC MOTO (documentar e nao esquecer):
o espelho `projeto_f7` NAO tem tabela de notas de entrada (a MC MOTO usa
`notas_entrada`). A unica fonte de compras de fornecedor no espelho sao os TITULOS
A PAGAR (TPAG_ABERTO + TPAG_BAIXADO). Entao a "nota" e reconstruida agrupando os
titulos por (unidade, tipo, numero, fornecedor) e usando TPAG_VALOR_FATURA, que e o
valor da NOTA (nao da parcela) -- assim uma NF parcelada em 5x conta UMA vez.
Consequencia: entram tambem titulos que nao sao mercadoria (servicos, impostos...).
Por isso a aba tem o mesmo filtro "fornecedores de mercadoria" da MC MOTO.

TPAG_BAIXADO tem duplicacao (~66x) no espelho -> o SELECT DISTINCT e obrigatorio.

Uso:  python gerar_recebimentos_seven.py            (grava no index.html)
      python gerar_recebimentos_seven.py --dry-run  (so relata)
"""
import json
import re
import sys
import datetime
import mysql.connector

DB = dict(host="187.127.22.30", port=3306, user="vitor", password="F7bretas@2026",
          database="projeto_f7", charset="utf8")
INDEX_HTML = r"C:\Users\Vitor\Desktop\DOCS EMPRESAS\PROTON\MC MOTO\index.html"
UNIDADES = (3, 4, 5)
MESES = 12


def buscar_notas(cur):
    """Reconstroi as notas de fornecedor a partir dos titulos a pagar."""
    notas = {}   # (u, tipo, numero, forn) -> {valor, data, parcelas}
    for tabela in ("TPAG_ABERTO", "TPAG_BAIXADO"):
        cur.execute(f"""
            SELECT DISTINCT
                   TPAG_UNIDADE_FK_UK      AS unidade,
                   TPAG_TIPO_FK_UK         AS tipo,
                   TPAG_NUMERO_UK          AS numero,
                   TPAG_PARCELA_UK         AS parcela,
                   TPAG_FORNECEDOR_FK_UK   AS fornecedor,
                   TPAG_VALOR_FATURA       AS fatura,
                   TPAG_VALOR_TITULO       AS titulo,
                   TPAG_DATA_EMISSAO       AS emissao
            FROM {tabela}
            WHERE TPAG_UNIDADE_FK_UK IN {UNIDADES}
              AND TPAG_DATA_EMISSAO >= DATE_SUB(CURDATE(), INTERVAL {MESES} MONTH)
        """)
        for unidade, tipo, numero, parcela, forn, fatura, titulo, emissao in cur.fetchall():
            if emissao is None:
                continue
            chave = (int(unidade), str(tipo), str(numero), int(forn or 0))
            n = notas.setdefault(chave, {"fatura": 0.0, "parcelas": 0.0, "data": emissao})
            n["fatura"] = max(n["fatura"], float(fatura or 0))
            n["parcelas"] += float(titulo or 0)
            if emissao < n["data"]:
                n["data"] = emissao
    return notas


def buscar_fornecedores(cur):
    cur.execute("SELECT TFOR_FORNECEDOR_PK, TFOR_FANTASIA, TFOR_NOME_RAZAO FROM TFOR_FORNECEDOR")
    return {int(pk): (fantasia or razao or f"Fornecedor {pk}").strip()
            for pk, fantasia, razao in cur.fetchall()}


def buscar_cmv(cur):
    """CMV mensal aproximado POR UNIDADE = SUM(qtd vendida x custo medio real do item).
    O espelho nao guarda o custo da venda; esta e a mesma aproximacao que o painel
    ja usa para a margem da SEVEN.
    Retorna {"3": {"2026-06": v, ...}, "4": {...}, "5": {...}} — a meta de recebimento
    e por unidade de negocio (decisao do usuario 30/07/2026), entao o CMV tambem precisa
    ser por unidade; o total das unidades e somado no navegador."""
    cur.execute(f"""
        SELECT v.UNIDADE_VENDA unidade,
               DATE_FORMAT(v.DATA_PEDIDO,'%Y-%m') ym,
               ROUND(SUM(v.QTDE_COMPRADO * COALESCE(e.TMER_CUSTO_MEDIO_REAL,0)),2) cmv
        FROM mv_resumo_vendas v
        LEFT JOIN TMER_ESTOQUE e
               ON e.TMER_UNIDADE_FK_PK = v.UNIDADE_VENDA
              AND e.TMER_CODIGO_PRI_FK_PK = v.CODIGO_PRODUTO
        WHERE v.UNIDADE_VENDA IN {UNIDADES}
          AND v.DATA_PEDIDO >= DATE_SUB(CURDATE(), INTERVAL 25 MONTH)
        GROUP BY unidade, ym ORDER BY unidade, ym
    """)
    porUnidade = {}
    for unidade, ym, cmv in cur.fetchall():
        porUnidade.setdefault(str(int(unidade)), {})[ym] = float(cmv or 0)
    return porUnidade


def main():
    dry = "--dry-run" in sys.argv
    conn = mysql.connector.connect(**DB)
    cur = conn.cursor()
    notas = buscar_notas(cur)
    fornecedores = buscar_fornecedores(cur)
    cmv = buscar_cmv(cur)
    cur.close()
    conn.close()

    itens = []
    for (unidade, tipo, numero, forn), n in notas.items():
        # TPAG_VALOR_FATURA e o valor da nota; se vier zerado, cai para a soma das parcelas
        valor = n["fatura"] if n["fatura"] > 0 else n["parcelas"]
        if valor <= 0:
            continue
        itens.append({
            "id": f"sv_{unidade}_{tipo}_{numero}_{forn}",
            "u": unidade,
            "fornecedor": fornecedores.get(forn, f"Fornecedor {forn}"),
            "data": n["data"].strftime("%Y-%m-%d"),
            "valor": round(valor, 2),
            "obs": f"NF {numero}",
            "origem": "sistema",
        })
    itens.sort(key=lambda r: r["data"], reverse=True)

    total = sum(i["valor"] for i in itens)
    meses_cmv = sorted({ym for u in cmv.values() for ym in u})
    print(f"notas reconstruidas: {len(itens)} | total R$ {total:,.2f} | "
          f"CMV: {len(cmv)} unidades, {len(meses_cmv)} meses")
    if itens:
        print(f"periodo: {itens[-1]['data']} a {itens[0]['data']}")

    if len(itens) < 50:
        raise SystemExit(f"ABORTADO: so {len(itens)} notas encontradas - consulta suspeita. Nada gravado.")

    if dry:
        print("--dry-run: nada gravado.")
        return

    with open(INDEX_HTML, "r", encoding="utf-8") as fh:
        content = fh.read()

    linha_r = "const RECEBIMENTOS_SEVEN = " + json.dumps(itens, ensure_ascii=False, separators=(",", ":")) + ";"
    linha_c = "const CMV_MENSAL_SEVEN = " + json.dumps(cmv, ensure_ascii=False, separators=(",", ":")) + ";"

    novo, n1 = re.subn(r"^const RECEBIMENTOS_SEVEN = \[.*?\];$", lambda _: linha_r, content, count=1, flags=re.M)
    if n1 != 1:
        raise SystemExit("ERRO: const RECEBIMENTOS_SEVEN nao encontrado no index.html")
    novo, n2 = re.subn(r"^const CMV_MENSAL_SEVEN = \{.*?\};$", lambda _: linha_c, novo, count=1, flags=re.M)
    if n2 != 1:
        raise SystemExit("ERRO: const CMV_MENSAL_SEVEN nao encontrado no index.html")

    with open(INDEX_HTML, "w", encoding="utf-8") as fh:
        fh.write(novo)
    print(f"index.html atualizado ({datetime.datetime.now():%d/%m/%Y %H:%M}).")


if __name__ == "__main__":
    main()
