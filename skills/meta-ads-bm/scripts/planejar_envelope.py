#!/usr/bin/env python3
"""
Planeja uma investida a partir do teto de verba disponivel (o envelope).

Responde tres coisas que mudam com o tamanho do envelope: o que essa verba
consegue de fato responder, como travar o gasto no teto, e em que ponto parar
antes de queimar o envelope inteiro num criativo que ja se sabe que nao vai.

Uso:
  python3 planejar_envelope.py --envelope 100 --meta-cpl 120
  python3 planejar_envelope.py --envelope 4500 --meta-cpl 120 --dias 30 --min-diario 6.50
"""

import argparse

# Vem de references/decisao.md. O piso de 10 conversoes e o mesmo do analisar_insights.py:
# se a investida nao compra 10 conversoes, ela nao decide nada por CPL.
PISO_CONVERSOES = 10
PISO_SINAL_PARCIAL = 3          # multiplo da meta de CPL
EVENTOS_SAIDA_APRENDIZADO = 50  # por conjunto, em 7 dias


def brl(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def banda(ratio):
    if ratio < PISO_SINAL_PARCIAL:
        return (
            "sinal de topo de funil",
            "Nao decide por CPL. O envelope nao compra amostra: qualquer CPL que aparecer "
            "e um numero solto, nao uma medida.",
            ["o criativo engaja (CTR de link, CPM)",
             "a pagina recebe visita e a estrutura roda ponta a ponta",
             "o publico existe e tem entrega no leilao"],
            ["se o CPL esta bom ou ruim",
             "qual criativo e melhor",
             "se vale escalar"],
        )
    if ratio < PISO_CONVERSOES:
        return (
            "sinal parcial",
            "CPL indicativo, nao conclusivo. Serve para descartar o que esta muito fora, "
            "nao para escolher entre coisas parecidas.",
            ["se o CPL esta absurdamente fora da meta (2x ou mais)",
             "CTR de link, CPM e taxa de conversao da pagina",
             "se a estrutura entrega e converte"],
            ["diferenca de 10 ou 20% entre criativos",
             "decisao de escala",
             "troca de otimizacao"],
        )
    return (
        "decisao plena",
        "Envelope compra amostra suficiente para decidir corte e escala por CPL.",
        ["CPL por objeto, com corte e escala",
         "comparacao entre criativos e publicos",
         "custo por reuniao, se o CRM estiver ligado"],
        ["nada relevante fica de fora, desde que a leitura respeite as janelas"],
    )


def main():
    p = argparse.ArgumentParser(description="Planeja a investida dentro do envelope disponivel.")
    p.add_argument("--envelope", type=float, required=True, help="teto total da investida, em reais")
    p.add_argument("--meta-cpl", type=float, required=True, help="meta de custo por lead, em reais")
    p.add_argument("--dias", type=int, default=7, help="duracao da investida em dias (padrao: 7)")
    p.add_argument("--min-diario", type=float, default=None,
                   help="minimo diario da conta em reais (campo min_daily_budget_* da conta)")
    p.add_argument("--evento", default="lead")
    args = p.parse_args()

    env, meta, dias = args.envelope, args.meta_cpl, max(1, args.dias)
    ratio = env / meta
    diaria = env / dias
    semanal = diaria * 7
    eventos_semana = semanal / meta
    leads_min, leads_max = ratio * 0.6, ratio * 1.4

    nome, leitura, responde, nao_responde = banda(ratio)

    print("PLANO DA INVESTIDA")
    print(f"Envelope: R$ {brl(env)}  |  meta de CPL: R$ {brl(meta)}  |  duracao: {dias} dias")
    print(f"Equivale a {ratio:.1f}x a meta de CPL")
    print()
    print(f"Banda de decisao: {nome}")
    print(f"  {leitura}")
    print()
    print("Responde:")
    for item in responde:
        print(f"  - {item}")
    print("Nao responde:")
    for item in nao_responde:
        print(f"  - {item}")
    print()

    print("VERBA")
    print(f"  Diaria: R$ {brl(diaria)}  ({dias} dias x diaria = R$ {brl(diaria * dias)})")
    if args.min_diario and diaria < args.min_diario:
        possiveis = int(env // args.min_diario)
        print(f"  ATENCAO: abaixo do minimo diario da conta (R$ {brl(args.min_diario)}).")
        print(f"  Com esse envelope cabem no maximo {possiveis} dias no minimo diario.")
        print("  Encurte a janela em vez de reduzir a diaria: diaria abaixo do minimo nao entrega.")
    print(f"  Leads plausiveis no fim: {leads_min:.0f} a {leads_max:.0f} (faixa, nao previsao)")
    print()

    print("ESTRUTURA")
    if ratio < PISO_CONVERSOES:
        print("  1 campanha, 1 conjunto, 1 criativo.")
        print("  Criativo unico por investida, testado em sequencia e nao em paralelo.")
        print("  Dois anuncios no mesmo conjunto devolvem a decisao de distribuicao para a")
        print("  Meta, que e exatamente o que esta operacao nao aceita; e dois conjuntos")
        print("  deixam cada um abaixo do minimo de entrega.")
    else:
        print("  1 campanha, 1 ou 2 conjuntos (publicos diferentes, com exclusao mutua).")
        print("  Um criativo por conjunto, para que o resultado seja atribuivel.")
    print()

    print("OTIMIZACAO")
    if eventos_semana < EVENTOS_SAIDA_APRENDIZADO:
        print(f"  Eventos de conversao por semana no ritmo atual: {eventos_semana:.1f}")
        print(f"  Abaixo dos {EVENTOS_SAIDA_APRENDIZADO} necessarios para sair do aprendizado.")
        if ratio < PISO_SINAL_PARCIAL:
            print("  Otimize por evento mais frequente (visualizacao de pagina de destino ou")
            print(f"  clique no link), nao por '{args.evento}'. Otimizar por conversao com esse")
            print("  volume so entrega sinal insuficiente para o algoritmo trabalhar.")
        else:
            print(f"  Pode otimizar por '{args.evento}', mas o conjunto vive em aprendizado:")
            print("  custo por resultado instavel, e leitura sempre com essa ressalva.")
    else:
        print(f"  Eventos por semana no ritmo atual: {eventos_semana:.1f}, acima de "
              f"{EVENTOS_SAIDA_APRENDIZADO}.")
        print(f"  Otimize por '{args.evento}'. O conjunto tem volume para sair do aprendizado.")
    print()

    print("TRAVAS (aplicar todas, verba diaria nao trava gasto total)")
    print(f"  1. Conjunto com lifetime_budget = {int(round(env * 100))} centavos e end_time definido.")
    print(f"  2. Campanha com spend_cap = {int(round(env * 100))} centavos, como segunda barreira.")
    print("  3. Readback de lifetime_budget, end_time e spend_cap antes de ativar.")
    print("  Verba diaria pode entregar acima do valor do dia (compensando na semana),")
    print("  entao ela sozinha nunca garante teto. Teto e orcamento total mais data de fim.")
    print()

    print("PARADA NO MEIO DO CAMINHO")
    marcos = [
        (0.20, "sem nenhum clique no link", "parar: criativo ou publico, nao verba"),
        (0.40, "CTR de link abaixo de 0,4%", "parar e trocar criativo"),
    ]
    if ratio >= PISO_SINAL_PARCIAL:
        marcos.append((0.60, f"nenhum '{args.evento}' registrado", "parar e olhar pagina e pixel"))
    marcos.append((1.00, "envelope encerrado", "ler, registrar hipotese e resultado"))
    for fracao, gatilho, acao in marcos:
        print(f"  R$ {brl(env * fracao)} ({int(fracao * 100)}% do envelope): {gatilho} -> {acao}")
    print()
    print("Parada e proposta, nao execucao: mostrar o numero, pedir confirmacao, aplicar.")


if __name__ == "__main__":
    main()
