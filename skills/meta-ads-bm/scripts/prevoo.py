#!/usr/bin/env python3
"""
Pre-voo da conta de anuncio: gera a sondagem e traduz o resultado em veredito.

Por que existe: os bloqueios de uma subida aparecem um de cada vez e cada um
custa uma ida e volta com a pessoa. Este script junta as sondagens que dao para
automatizar numa chamada so, e classifica o resultado em verde / bloqueia /
vai doer depois, que e o formato que a pessoa consegue agir em cima.

Uso:

  1) Gerar o bloco de sondagem para colar no console do navegador,
     com a aba aberta na origem da ponte:

       python3 scripts/prevoo.py gerar --chave-escrita SUA_CHAVE
       python3 scripts/prevoo.py gerar --chave-escrita SUA_CHAVE --chave-leitura OUTRA

  2) Colar o JSON devolvido e pedir o veredito:

       python3 scripts/prevoo.py avaliar resultado.json --envelope 100 --dias 7

O bloco de sondagem nao cria nada. As unicas escritas que ele faz sao
propositalmente invalidas, para que a ponte recuse e a mensagem de erro
ensine o contrato.
"""

import argparse
import json
import sys

JS = r"""
(async () => {
  const KW = "__WRITE__", KR = "__READ__";
  const out = {};
  const get = async (rota, hdr) => {
    try {
      const r = await fetch(rota, { headers: hdr || {} });
      const t = await r.text();
      let corpo; try { corpo = JSON.parse(t); } catch { corpo = t.slice(0, 300); }
      return { status: r.status, corpo };
    } catch (e) { return { status: 0, erro: String(e).slice(0, 200) }; }
  };
  const post = async (body, idem) => {
    try {
      const h = { "content-type": "application/json" };
      if (KW) h["x-ponte-write-key"] = KW;
      if (idem) h["Idempotency-Key"] = idem;
      const r = await fetch("/api/criar", { method: "POST", headers: h, body: JSON.stringify(body) });
      const t = await r.text();
      let corpo; try { corpo = JSON.parse(t); } catch { corpo = t.slice(0, 300); }
      return { status: r.status, corpo };
    } catch (e) { return { status: 0, erro: String(e).slice(0, 200) }; }
  };

  out.A_saude   = await get("/api/health");
  out.B_sem_idem = await post({}, null);
  out.B_contrato = await post({}, "prevoo-" + Date.now());
  out.C_leitura  = await get("/api/estrutura?nivel=campaign", KR ? { "x-ponte-read-key": KR } : {});

  return JSON.stringify(out, null, 1);
})()
"""


def gerar(args):
    js = JS.replace("__WRITE__", args.chave_escrita or "").replace("__READ__", args.chave_leitura or "")
    print("# Abra uma aba na origem da ponte (ex.: /api/ping) e rode este bloco.")
    print("# Depois salve a saida num arquivo e rode:  python3 scripts/prevoo.py avaliar <arquivo>\n")
    print(js.strip())


def _achar(d, *chaves):
    for k in chaves:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return None
    return d


def avaliar(args):
    dados = json.load(open(args.arquivo, encoding="utf-8"))
    verde, bloqueia, depois = [], [], []

    # --- Bloco A: ponte e conta ---
    a = dados.get("A_saude") or {}
    corpo = a.get("corpo") if isinstance(a.get("corpo"), dict) else {}
    if a.get("status") != 200:
        bloqueia.append(("ponte", f"/api/health respondeu {a.get('status')}. "
                                  "Sem ponte nao ha leitura nem escrita. Rode pelo navegador, "
                                  "nao pelo container."))
    else:
        versao = corpo.get("versaoApi")
        conta = corpo.get("contaConfigurada")
        verde.append(("ponte", f"no ar, API {versao}, conta {conta}"))

        c = corpo.get("conta") or {}
        status = c.get("account_status")
        if status == 1:
            verde.append(("conta", f"ativa, moeda {c.get('currency')}, fuso {c.get('timezone_name')}"))
        else:
            bloqueia.append(("conta", f"account_status={status}, disable_reason={c.get('disable_reason')}. "
                                      "Conta restrita: nenhuma decisao de midia resolve isso."))

        gasto = c.get("amount_spent")
        if gasto not in (None, "0", 0):
            depois.append(("gasto acumulado", f"conta ja gastou {gasto} centavos. "
                                              "Limite de conta, se usado, conta o acumulado."))

        minimo = _achar(corpo, "minimoDiario", "valorCentavos")
        if minimo and args.envelope and args.dias:
            diaria = (args.envelope * 100) / args.dias
            if diaria < minimo:
                bloqueia.append(("minimo diario",
                                 f"diaria derivada R$ {diaria/100:.2f} abaixo do minimo R$ {minimo/100:.2f}. "
                                 f"Encurte a janela para {int((args.envelope*100)//minimo)} dias ou menos. "
                                 "Nao afine a diaria."))
            else:
                verde.append(("minimo diario",
                              f"R$ {minimo/100:.2f}; diaria derivada R$ {diaria/100:.2f} "
                              f"({diaria/minimo:.1f}x o minimo)"))

        teto_ponte = corpo.get("limiteVerbaCentavos")
        if teto_ponte:
            verde.append(("trava da ponte", f"recusa verba acima de R$ {teto_ponte/100:.2f}"))
            if args.envelope and args.envelope * 100 > teto_ponte:
                bloqueia.append(("trava da ponte",
                                 f"envelope R$ {args.envelope:.2f} acima do teto da ponte. "
                                 "Ajuste o envelope ou a variavel PONTE_LIMITE_VERBA_CENTAVOS."))

    # --- Bloco B: contrato de escrita ---
    b1 = dados.get("B_sem_idem") or {}
    b2 = dados.get("B_contrato") or {}
    if b1.get("status") == 401 or b2.get("status") == 401:
        bloqueia.append(("chave de escrita", "401. Chave errada ou ausente: nenhuma criacao vai passar."))
    else:
        if b1.get("status") == 400:
            verde.append(("idempotencia", "ponte exige Idempotency-Key, como deve ser"))
        erro = _achar(b2, "corpo", "erro") or ""
        if erro:
            verde.append(("contrato de /api/criar", f"recusa util: \"{erro}\""))

    # --- Bloco C: chave de leitura ---
    c = dados.get("C_leitura") or {}
    if c.get("status") == 200:
        verde.append(("chave de leitura", "valida; readback por API disponivel"))
    else:
        depois.append(("chave de leitura",
                       f"/api/estrutura respondeu {c.get('status')}. Sem ela, todo readback vira leitura "
                       "de tela (procedencia UI, nao API). Variavel marcada como sensivel na Vercel nao e "
                       "recuperavel pelo painel: ou a pessoa tem o valor guardado, ou gera uma nova e faz deploy."))

    # --- Checagens que dependem de pessoa ---
    if args.envelope and args.envelope < 300:
        depois.append(("spend_cap de campanha",
                       f"envelope R$ {args.envelope:.2f} abaixo do piso de R$ 300,00 em BRL. "
                       "A segunda camada de teto nao existe nesta investida: sobram lifetime_budget "
                       "com end_time, e o readback. Diga isso no gate."))

    if args.envelope and args.meta_cpl:
        mult = args.envelope / args.meta_cpl
        if mult < 3:
            banda = "sinal de topo de funil: NAO responde se o CPL esta bom"
        elif mult < 10:
            banda = "sinal parcial: descarta o que esta muito fora da meta, nao escolhe entre parecidos"
        else:
            banda = "decisao plena: corte e escala por CPL"
        depois.append(("banda de decisao",
                       f"envelope e {mult:.2f}x a meta de CPL. {banda}."))

    manuais = [
        ("modo do app", "confirme em developers.facebook.com/apps que o app NAO esta 'Em desenvolvimento'. "
                        "Se estiver, criacao de criativo falha com error_subcode 1885183, e publicar exige "
                        "URL de politica de privacidade e categoria."),
        ("acervo de midia", "video_id e image_hash precisam vir de 'Midia da conta de anuncios', nunca de "
                            "'Midia da empresa'. Hash tem 32 caracteres hexadecimais; numero de 16 digitos nao e hash."),
        ("rascunhos soltos", "confira 'Conferir e publicar (N)' no gerenciador. Rascunho criado sozinho "
                             "nasce com o botao ligado."),
    ]

    def bloco(titulo, itens, marca):
        print(f"\n{titulo}")
        if not itens:
            print("  (nada)")
        for nome, txt in itens:
            print(f"  {marca} {nome}: {txt}")

    print("=" * 72)
    print("PRE-VOO")
    print("=" * 72)
    bloco("VERDE (pronto, com o numero que prova)", verde, "+")
    bloco("BLOQUEIA AGORA (impede a subida)", bloqueia, "!")
    bloco("VAI DOER DEPOIS (nao impede hoje, cobra juros)", depois, "~")
    bloco("CONFERIR NA MAO (nao da para sondar pela ponte)", manuais, "?")
    print()
    print(f"Veredito: {'NAO SUBIR ainda' if bloqueia else 'liberado para a Fase 1'}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gerar", help="gera o bloco JS de sondagem")
    g.add_argument("--chave-escrita", default="")
    g.add_argument("--chave-leitura", default="")
    g.set_defaults(func=gerar)

    a = sub.add_parser("avaliar", help="traduz o JSON da sondagem em veredito")
    a.add_argument("arquivo")
    a.add_argument("--envelope", type=float, help="teto de verba em reais")
    a.add_argument("--dias", type=int, help="dias da janela")
    a.add_argument("--meta-cpl", type=float, help="meta de CPL em reais")
    a.set_defaults(func=avaliar)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
