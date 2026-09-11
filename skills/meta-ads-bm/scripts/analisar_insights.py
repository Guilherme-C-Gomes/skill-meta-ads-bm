#!/usr/bin/env python3
"""
Le um JSON de insights da Marketing API e devolve metricas derivadas,
sinalizacoes de amostra e acoes candidatas. Nao decide e nao escreve nada:
a decisao e da LLM, com a pessoa confirmando.

Uso:
  python3 analisar_insights.py insights.json --meta-cpl 120 --evento lead
  python3 analisar_insights.py atual.json --anterior anterior.json --meta-cpl 120
  python3 analisar_insights.py insights.json --meta-cpl 120 --json > acoes.json

Aceita: {"data": [...]}, uma lista crua de linhas, ou {"atual": {...}, "anterior": {...}}.
Valores monetarios de entrada sao em unidade da conta (reais), como o insights devolve.
"""

import argparse
import json
import sys

# Limiares de partida. Vem de references/decisao.md; calibre com o historico da conta.
PADRAO = {
    "min_conversoes": 10,
    "gasto_min_multiplo_meta": 3.0,
    "corte_cpl_multiplo": 1.5,
    "reduzir_cpl_multiplo": 1.2,
    "ctr_link_minimo": 0.4,          # em %
    "impressoes_min_ctr": 5000,
    "frequencia_alta": 2.5,
    "passo_escala": 0.20,
}


def num(valor, default=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def extrair_linhas(bruto):
    if isinstance(bruto, list):
        return bruto
    if isinstance(bruto, dict):
        for chave in ("data", "linhas", "insights"):
            if isinstance(bruto.get(chave), list):
                return bruto[chave]
        if isinstance(bruto.get("atual"), (list, dict)):
            return extrair_linhas(bruto["atual"])
    raise ValueError("Nao encontrei lista de insights no JSON (esperado 'data' ou lista crua).")


def valor_acao(linha, campo, evento):
    """Soma o valor do evento em 'actions' ou 'cost_per_action_type'.
    Casa por igualdade ou por sufixo, para pegar offsite_conversion.fb_pixel_lead com --evento lead."""
    itens = linha.get(campo) or []
    if not isinstance(itens, list):
        return None
    exato = [num(i.get("value")) for i in itens if i.get("action_type") == evento]
    if exato:
        return sum(exato)
    parcial = [
        num(i.get("value"))
        for i in itens
        if isinstance(i.get("action_type"), str) and i["action_type"].endswith(evento)
    ]
    if parcial:
        return sum(parcial)
    return None


def eventos_disponiveis(linhas):
    tipos = set()
    for linha in linhas:
        for item in linha.get("actions") or []:
            if isinstance(item, dict) and item.get("action_type"):
                tipos.add(item["action_type"])
    return sorted(tipos)


def nome_objeto(linha):
    for chave in ("ad_name", "adset_name", "campaign_name"):
        if linha.get(chave):
            return linha[chave]
    return linha.get("ad_id") or linha.get("adset_id") or linha.get("campaign_id") or "(sem nome)"


def id_objeto(linha):
    for chave in ("ad_id", "adset_id", "campaign_id"):
        if linha.get(chave):
            return linha[chave]
    return ""


ADITIVOS = ("spend", "impressions", "clicks", "inline_link_clicks", "reach")


def chave_objeto(linha):
    return id_objeto(linha) or nome_objeto(linha)


def agregar(linhas):
    """Consulta com time_increment devolve uma linha por objeto por dia. Sem somar
    antes de calcular, cada dia seria tratado como um objeto e toda decisao sairia
    errada: 7 linhas de R$ 200 nao sao 7 anuncios baratos, sao um anuncio de R$ 1.400.

    Devolve (linhas_agregadas, dias, frequencia_confiavel).
    frequency = impressoes/alcance e nao e somavel, entao ela se perde na agregacao.
    """
    grupos = {}
    ordem = []
    datas = set()
    for linha in linhas:
        k = chave_objeto(linha)
        if linha.get("date_start"):
            datas.add(linha["date_start"])
        if k not in grupos:
            grupos[k] = {c: linha.get(c) for c in
                         ("ad_id", "adset_id", "campaign_id", "ad_name", "adset_name", "campaign_name")}
            grupos[k].update({campo: 0.0 for campo in ADITIVOS})
            grupos[k]["actions"] = {}
            ordem.append(k)
        g = grupos[k]
        for campo in ADITIVOS:
            if linha.get(campo) is not None:
                g[campo] += num(linha.get(campo))
        for item in linha.get("actions") or []:
            if isinstance(item, dict) and item.get("action_type"):
                g["actions"][item["action_type"]] = g["actions"].get(item["action_type"], 0.0) + num(item.get("value"))

    if len(grupos) == len(linhas):
        return linhas, len(datas) or 1, True

    saida = []
    for k in ordem:
        g = dict(grupos[k])
        g["actions"] = [{"action_type": t, "value": v} for t, v in g["actions"].items()]
        saida.append(g)
    return saida, len(datas) or 1, False


def calcular(linha, evento):
    gasto = num(linha.get("spend"))
    impressoes = num(linha.get("impressions"))
    conversoes = valor_acao(linha, "actions", evento)
    cpl_api = valor_acao(linha, "cost_per_action_type", evento)

    ctr_link = linha.get("inline_link_click_ctr")
    if ctr_link is None:
        cliques_link = num(linha.get("inline_link_clicks"))
        ctr_link = (cliques_link / impressoes * 100) if impressoes else 0.0
    ctr_link = num(ctr_link)

    ctr = linha.get("ctr")
    if ctr is None:
        ctr = (num(linha.get("clicks")) / impressoes * 100) if impressoes else 0.0

    cpl = None
    if conversoes:
        cpl = gasto / conversoes
    elif cpl_api:
        cpl = cpl_api

    return {
        "id": id_objeto(linha),
        "nome": nome_objeto(linha),
        "gasto": gasto,
        "impressoes": impressoes,
        "frequencia": num(linha.get("frequency")),
        "cpm": num(linha.get("cpm")) or ((gasto / impressoes * 1000) if impressoes else 0.0),
        "ctr": num(ctr),
        "ctr_link": ctr_link,
        "conversoes": conversoes,
        "cpl": cpl,
    }


def amostra_fechada(m, meta_cpl, cfg):
    conv_ok = (m["conversoes"] or 0) >= cfg["min_conversoes"]
    gasto_ok = m["gasto"] >= meta_cpl * cfg["gasto_min_multiplo_meta"]
    return conv_ok and gasto_ok


def sinalizar(m, meta_cpl, cfg, anterior=None, evento_ausente=False, freq_ok=True):
    """Devolve lista de (severidade, sinal, acao_sugerida). Sugestao, nao decisao."""
    saida = []
    if evento_ausente:
        # O evento pedido nao existe em nenhuma linha: quase sempre nome errado do
        # action_type, nao performance ruim. Sinalizar corte aqui mandaria pausar a
        # conta inteira por erro de consulta, entao so o sinal de topo de funil vale.
        if m["impressoes"] >= cfg["impressoes_min_ctr"] and m["ctr_link"] < cfg["ctr_link_minimo"]:
            saida.append((
                "media",
                f"CTR de link {m['ctr_link']:.2f}% com {int(m['impressoes'])} impressoes",
                "trocar criativo (nao mexer em publico)",
            ))
        if freq_ok and m["frequencia"] >= cfg["frequencia_alta"]:
            saida.append((
                "media",
                f"frequencia {m['frequencia']:.2f}",
                "criativo novo ou ampliar publico",
            ))
        saida.append((
            "info",
            "evento de conversao nao encontrado no JSON",
            "corrigir o action_type da consulta antes de decidir",
        ))
        return saida
    fechada = amostra_fechada(m, meta_cpl, cfg)
    cpl = m["cpl"]

    if not fechada:
        faltam = max(0, cfg["min_conversoes"] - int(m["conversoes"] or 0))
        saida.append((
            "info",
            f"amostra insuficiente ({int(m['conversoes'] or 0)} conv., faltam {faltam})",
            "manter e reavaliar",
        ))

    if (m["conversoes"] or 0) == 0 and m["gasto"] >= meta_cpl * cfg["gasto_min_multiplo_meta"]:
        saida.append((
            "alta",
            f"zero conversao com R$ {brl(m['gasto'])} gastos",
            "pausar",
        ))

    if cpl and fechada:
        if cpl >= meta_cpl * cfg["corte_cpl_multiplo"]:
            saida.append((
                "alta",
                f"CPL R$ {brl(cpl)} = {cpl / meta_cpl:.2f}x a meta",
                "pausar",
            ))
        elif cpl >= meta_cpl * cfg["reduzir_cpl_multiplo"]:
            saida.append((
                "media",
                f"CPL R$ {brl(cpl)} = {cpl / meta_cpl:.2f}x a meta",
                "reduzir verba 30% e reavaliar em 4 dias",
            ))
        elif cpl <= meta_cpl:
            saida.append((
                "oportunidade",
                f"CPL R$ {brl(cpl)} dentro da meta",
                f"escalar +{int(cfg['passo_escala'] * 100)}% (passo unico)",
            ))

    if m["impressoes"] >= cfg["impressoes_min_ctr"] and m["ctr_link"] < cfg["ctr_link_minimo"]:
        saida.append((
            "media",
            f"CTR de link {m['ctr_link']:.2f}% com {int(m['impressoes'])} impressoes",
            "trocar criativo (nao mexer em publico)",
        ))

    if freq_ok and m["frequencia"] >= cfg["frequencia_alta"]:
        saida.append((
            "media",
            f"frequencia {m['frequencia']:.2f}",
            "criativo novo ou ampliar publico",
        ))

    if anterior:
        cpl_ant = anterior.get("cpl")
        if cpl and cpl_ant and cpl_ant > 0:
            delta = (cpl / cpl_ant - 1) * 100
            if abs(delta) >= 20:
                saida.append((
                    "info",
                    f"CPL {'subiu' if delta > 0 else 'caiu'} {abs(delta):.0f}% vs periodo anterior",
                    "investigar antes de agir",
                ))
        ctr_ant = anterior.get("ctr_link")
        if ctr_ant and m["ctr_link"] and ctr_ant > 0:
            if (m["ctr_link"] / ctr_ant - 1) <= -0.25 and freq_ok and m["frequencia"] >= cfg["frequencia_alta"]:
                saida.append((
                    "media",
                    "CTR caindo com frequencia alta",
                    "fadiga de criativo",
                ))

    if not saida:
        saida.append(("ok", "sem sinal relevante", "manter"))
    return saida


def brl(valor):
    if valor is None:
        return "-"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def esc(texto):
    """Nome de objeto usa | na nomenclatura padrao, o que quebraria a tabela Markdown."""
    return str(texto).replace("|", "\\|")


def tabela(resultados, meta_cpl):
    cab = "| Objeto | Gasto | Impr. | Freq. | CPM | CTR link | Conv. | CPL | vs meta | Sinal |"
    sep = "|---|---|---|---|---|---|---|---|---|---|"
    linhas = [cab, sep]
    for r in resultados:
        m = r["metricas"]
        cpl = m["cpl"]
        vs = f"{cpl / meta_cpl:.2f}x" if cpl else "-"
        freq = f"{m['frequencia']:.2f}" if m["frequencia"] else "-"
        sinais = esc("; ".join(s[1] for s in r["sinais"]))
        linhas.append(
            f"| {esc(m['nome'])} | R$ {brl(m['gasto'])} | {int(m['impressoes'])} | "
            f"{freq} | R$ {brl(m['cpm'])} | {m['ctr_link']:.2f}% | "
            f"{int(m['conversoes'] or 0)} | {'R$ ' + brl(cpl) if cpl else '-'} | {vs} | {sinais} |"
        )
    return "\n".join(linhas)


def main():
    p = argparse.ArgumentParser(description="Analisa insights da Meta e sinaliza acoes candidatas.")
    p.add_argument("arquivo", help="JSON de insights do periodo atual")
    p.add_argument("--anterior", help="JSON de insights do periodo anterior, para comparacao")
    p.add_argument("--meta-cpl", type=float, required=True, help="meta de custo por lead, em reais")
    p.add_argument("--evento", default="lead", help="action_type da conversao (padrao: lead)")
    p.add_argument("--min-conversoes", type=int, default=PADRAO["min_conversoes"])
    p.add_argument("--json", action="store_true", help="saida em JSON em vez de tabela")
    args = p.parse_args()

    cfg = dict(PADRAO, min_conversoes=args.min_conversoes)

    with open(args.arquivo, encoding="utf-8") as f:
        bruto = json.load(f)
    linhas, dias, freq_ok = agregar(extrair_linhas(bruto))

    anteriores = {}
    if args.anterior:
        with open(args.anterior, encoding="utf-8") as f:
            for linha in agregar(extrair_linhas(json.load(f)))[0]:
                m = calcular(linha, args.evento)
                anteriores[m["id"] or m["nome"]] = m
    elif isinstance(bruto, dict) and isinstance(bruto.get("anterior"), (list, dict)):
        for linha in agregar(extrair_linhas(bruto["anterior"]))[0]:
            m = calcular(linha, args.evento)
            anteriores[m["id"] or m["nome"]] = m

    disponiveis = eventos_disponiveis(linhas)
    evento_ausente = not any(
        t == args.evento or t.endswith(args.evento) for t in disponiveis
    )

    resultados = []
    for linha in linhas:
        m = calcular(linha, args.evento)
        ant = anteriores.get(m["id"] or m["nome"])
        resultados.append({
            "metricas": m,
            "sinais": sinalizar(m, args.meta_cpl, cfg, ant, evento_ausente, freq_ok),
        })

    resultados.sort(key=lambda r: r["metricas"]["gasto"], reverse=True)

    gasto_total = sum(r["metricas"]["gasto"] for r in resultados)
    conv_total = sum(r["metricas"]["conversoes"] or 0 for r in resultados)
    cpl_geral = gasto_total / conv_total if conv_total else None

    if args.json:
        json.dump(
            {
                "meta_cpl": args.meta_cpl,
                "evento": args.evento,
                "limiares": cfg,
                "total": {
                    "gasto": gasto_total,
                    "conversoes": conv_total,
                    "cpl": cpl_geral,
                    "objetos": len(resultados),
                },
                "objetos": resultados,
                "eventos_disponiveis": disponiveis,
                "evento_ausente": evento_ausente,
                "dias_na_janela": dias,
                "frequencia_confiavel": freq_ok,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        print()
        return

    print(f"Meta de CPL: R$ {brl(args.meta_cpl)}  |  evento: {args.evento}  |  objetos: {len(resultados)}")
    if not freq_ok:
        print(
            f"Serie diaria detectada ({dias} dia(s)): agreguei por objeto. "
            "Frequencia nao e somavel e foi ignorada nas sinalizacoes; "
            "para ler frequencia, puxe a mesma janela sem time_increment."
        )
    print(
        f"Total: R$ {brl(gasto_total)} gastos, {int(conv_total)} conversoes, "
        f"CPL geral {'R$ ' + brl(cpl_geral) if cpl_geral else 'indefinido'}"
    )
    print()
    print(tabela(resultados, args.meta_cpl))
    print()

    if conv_total == 0:
        print(f"Nenhuma conversao encontrada para o evento '{args.evento}'.")
        if disponiveis:
            print("Eventos presentes no JSON: " + ", ".join(disponiveis))
        else:
            print("O JSON nao trouxe o campo 'actions'. Confira os fields da consulta.")
        print()

    print("Acoes candidatas (sugestao do script, decisao e da LLM com confirmacao humana):")
    ordem = {"alta": 0, "media": 1, "oportunidade": 2, "info": 3, "ok": 4}
    pendencias = [
        (sev, r["metricas"]["nome"], sinal, acao)
        for r in resultados
        for sev, sinal, acao in r["sinais"]
        if sev in ("alta", "media", "oportunidade")
    ]
    if not pendencias:
        print("- nenhuma. Manter e reavaliar na data combinada.")
    for sev, nome, sinal, acao in sorted(pendencias, key=lambda x: ordem[x[0]]):
        print(f"- [{sev}] {nome}: {sinal} -> {acao}")


if __name__ == "__main__":
    main()
