# meta-ads-bm

Skill do Claude que opera tráfego pago no Meta Ads (BM) por ponte na Marketing API, com a decisão saindo da LLM e zero automação de IA da Meta.

Puxa dado real com procedência, audita a conta por controles, diagnostica, planeja a investida dentro do teto de verba, propõe corte e escala com trade-off declarado, gera a configuração em JSON aplicável, pede confirmação, aplica e confere os toggles.

## Conteúdo

```
skills/meta-ads-bm/
  SKILL.md
  references/
    api-meta.md
    auditoria.md
    comandos-curl.md
    decisao.md
    ponte-vercel.md
  scripts/
    analisar_insights.py
    planejar_envelope.py
  assets/
    ficha_conta.md
    registro.md
    exemplo_insights_atual.json
    exemplo_insights_anterior.json
```

## Como instalar

```bash
git clone https://github.com/Guilherme-C-Gomes/skill-meta-ads-bm.git
cp -r skill-meta-ads-bm/skills/meta-ads-bm ~/.claude/skills/
```

Depois é só chamar `/meta-ads-bm` numa sessão do Claude.

## Atenção a credenciais

A skill trabalha com token da Marketing API, ID de conta de anúncio e pixel. Nada disso deve ser commitado neste repositório. Mantenha as credenciais em variável de ambiente na ponte serverless e deixe os arquivos de `assets/` apenas com exemplo.
