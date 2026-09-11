# Comandos prontos: leitura e escrita sem a ponte no caminho

Este arquivo existe para o caminho degradado: quando a ponte não está no ar, quando ela está fora do ar, ou quando é a pessoa que vai rodar o comando e colar o retorno. São os mesmos endpoints de `api-meta.md`, no formato executável.

Índice:
1. Regras que valem para todo comando
2. Preparar o ambiente
3. Conta
4. Estrutura
5. Insights
6. Auditoria de IA em uma passada
7. Escrita
8. Paginação
9. Erros e limite de taxa

---

## 1. Regras que valem para todo comando

- **Token em cabeçalho, nunca em URL.** Muitos exemplos públicos passam `access_token=` na query. URL vaza em histórico de shell, em log de proxy, em print de tela e em cabeçalho de referência. Use `Authorization: Bearer`.
- **Nunca cole o token no chat.** O comando gerado lê de variável de ambiente. Se um token aparecer na conversa, ele precisa ser rotacionado.
- **Token de System User**, não de usuário pessoal. Token pessoal morre em troca de senha e derruba a operação.
- **Versão vem de variável**, não escrita à mão em cada linha. Trocar de versão precisa ser uma edição, não vinte.
- **`act_` faz parte do ID de conta** nos endpoints. A variável de ambiente da ponte guarda o ID sem o prefixo, então aqui ele é montado. Confusão entre as duas formas é causa comum de 404 que parece problema de permissão.
- **Valor de dinheiro vem em centavos.** `10000` é R$ 100,00. Ao mostrar para a pessoa, converta para reais: o erro de duas casas passa despercebido em centavos e é o mais caro que existe.
- Retorno vai para arquivo quando for alimentar `scripts/analisar_insights.py`. Colar JSON grande no chat gasta contexto e não deixa o script rodar.

## 2. Preparar o ambiente

Na máquina da pessoa, uma vez por sessão:

```bash
export META_TOKEN='...'                 # System User, colado só no terminal dela
export META_VER='v26.0'
export ACT='act_000000000000000'        # com o prefixo
export AUTH="Authorization: Bearer ${META_TOKEN}"
export G="https://graph.facebook.com/${META_VER}"
```

Confirmação de que o token responde e é da conta certa:

```bash
curl -sG "${G}/me" -H "${AUTH}" --data-urlencode 'fields=id,name' | jq .
```

## 3. Conta

Moeda, fuso, teto e mínimo diário. Isso vem antes de propor qualquer verba:

```bash
curl -sG "${G}/${ACT}" -H "${AUTH}" \
  --data-urlencode 'fields=name,account_status,currency,timezone_name,spend_cap,amount_spent,balance,min_daily_budget_low_freq,min_daily_budget_high_freq,disable_reason' \
  | jq .
```

`account_status` diferente de `1` e `disable_reason` preenchido explicam entrega zero sem nenhuma teoria de leilão. Confira isso antes de olhar criativo.

## 4. Estrutura

Campanhas:

```bash
curl -sG "${G}/${ACT}/campaigns" -H "${AUTH}" \
  --data-urlencode 'fields=id,name,status,effective_status,objective,buying_type,daily_budget,lifetime_budget,spend_cap,special_ad_categories,start_time,stop_time' \
  --data-urlencode 'limit=200' \
  | jq '.data[] | {id,name,effective_status,objective,daily_budget,lifetime_budget,spend_cap}'
```

Verba presente na campanha é CBO. Anote como achado.

Conjuntos, com tudo que a auditoria precisa:

```bash
curl -sG "${G}/${ACT}/adsets" -H "${AUTH}" \
  --data-urlencode 'fields=id,name,status,effective_status,campaign_id,daily_budget,lifetime_budget,start_time,end_time,billing_event,optimization_goal,bid_strategy,is_dynamic_creative,promoted_object,attribution_spec,learning_stage_info,targeting' \
  --data-urlencode 'limit=200' \
  > adsets.json && jq '.data | length' adsets.json
```

Anúncios e estado de revisão:

```bash
curl -sG "${G}/${ACT}/ads" -H "${AUTH}" \
  --data-urlencode 'fields=id,name,status,effective_status,adset_id,campaign_id,issues_info,created_time,creative{id,name,degrees_of_freedom_spec}' \
  --data-urlencode 'limit=200' \
  > ads.json && jq '[.data[] | select(.effective_status != "ACTIVE") | {id,name,effective_status,issues_info}]' ads.json
```

## 5. Insights

Janela fechada, com atribuição declarada e comparação com o período anterior. Ajuste as datas para descontar o atraso de conversão da ficha:

```bash
curl -sG "${G}/${ACT}/insights" -H "${AUTH}" \
  --data-urlencode 'level=ad' \
  --data-urlencode 'fields=campaign_name,adset_name,ad_name,campaign_id,adset_id,ad_id,spend,impressions,frequency,clicks,ctr,cpm,inline_link_clicks,inline_link_click_ctr,actions,cost_per_action_type,video_thruplay_watched_actions' \
  --data-urlencode 'time_range={"since":"2026-09-01","until":"2026-09-07"}' \
  --data-urlencode 'action_attribution_windows=["7d_click","1d_view"]' \
  --data-urlencode 'limit=500' \
  > insights_atual.json
```

Mesmo comando com a janela anterior de igual tamanho, salvo em `insights_anterior.json`. Sem período anterior, "subiu" e "caiu" não têm base.

Série diária, para ver ritmo de gasto e o efeito de uma mudança:

```bash
curl -sG "${G}/${ACT}/insights" -H "${AUTH}" \
  --data-urlencode 'level=adset' \
  --data-urlencode 'fields=adset_name,adset_id,spend,impressions,ctr,actions' \
  --data-urlencode 'time_range={"since":"2026-09-01","until":"2026-09-07"}' \
  --data-urlencode 'time_increment=1' \
  | jq '.data[] | {date_start,adset_name,spend,ctr}'
```

Recorte por idade e gênero, ou por posicionamento, quando a hipótese for de público ou de formato:

```bash
curl -sG "${G}/${ACT}/insights" -H "${AUTH}" \
  --data-urlencode 'level=adset' \
  --data-urlencode 'fields=adset_name,spend,impressions,inline_link_click_ctr,actions' \
  --data-urlencode 'time_range={"since":"2026-08-10","until":"2026-09-07"}' \
  --data-urlencode 'breakdowns=publisher_platform,platform_position' \
  | jq '.data[] | {adset_name,publisher_platform,platform_position,spend,inline_link_click_ctr}'
```

Recorte fatia a amostra. Uma conta com 12 conversões vira seis fatias de duas, e cada uma delas é ruído. Use recorte para levantar hipótese, não para cortar objeto: o piso de amostra de `decisao.md` vale por fatia, não pelo total.

Evento real, quando o CPL vier zerado ou estranho:

```bash
jq '[.data[].actions[]? | .action_type] | unique' insights_atual.json
```

Isso lista os `action_type` que a conta está de fato populando. Otimizar por um e medir por outro é causa frequente de CPL fantasma.

Pixel recebendo evento:

```bash
curl -sG "${G}/${PIXEL_ID}/stats" -H "${AUTH}" \
  --data-urlencode 'aggregation=event' | jq .
```

## 6. Auditoria de IA em uma passada

O mesmo checklist da seção 3 de `api-meta.md`, rodado sobre o arquivo já baixado:

```bash
jq '[.data[] | {
  id, name,
  advantage_audience: .targeting.targeting_automation.advantage_audience,
  relaxation: .targeting.targeting_relaxation_types,
  dynamic: .is_dynamic_creative,
  plataformas: .targeting.publisher_platforms
} | select(
  .advantage_audience != 0 or .dynamic == true or .plataformas == null
)]' adsets.json
```

Saída vazia significa conjuntos conformes no que este filtro cobre. Não significa "toda a IA desligada": melhoria de criativo vive no criativo, não no conjunto, e vem do arquivo de anúncios:

```bash
jq '[.data[] | {id, name, feats: .creative.degrees_of_freedom_spec.creative_features_spec}
  | select(.feats != null)
  | .ligadas = ([.feats | to_entries[] | select(.value.enroll_status != "OPT_OUT") | .key])
  | select(.ligadas | length > 0)
  | {id, name, ligadas}]' ads.json
```

Feature que voltar aqui e não estiver na tabela de `api-meta.md` é pendência: reporte e adicione à tabela.

## 7. Escrita

Escrita fora da ponte perde idempotência e teto automático, então ela é exceção e sempre depois do gate da Fase 4. Duas travas manuais compensam parte disso: validar antes e ler depois.

Validação, que custa nada e pega erro de payload:

```bash
cat > /tmp/adset.json << 'EOF'
{
  "name": "Advogado civel SP | Feed+Reels | Lead",
  "campaign_id": "{CAMPAIGN_ID}",
  "status": "PAUSED",
  "lifetime_budget": 10000,
  "end_time": "2026-09-17T23:59:00-0300",
  "execution_options": ["validate_only"]
}
EOF

curl -s -X POST "${G}/${ACT}/adsets" -H "${AUTH}" \
  -H 'Content-Type: application/json' -d @/tmp/adset.json | jq .
```

Sucesso na validação significa payload aceito, não objeto criado. Diga isso com essas palavras, porque a resposta parece confirmação.

Criação real: remova `execution_options` e envie. Sempre `PAUSED`, e ativação em chamada separada.

Pausar em lote, que é a escrita mais comum e a mais segura:

```bash
for ID in 1234 5678; do
  curl -s -X POST "${G}/${ID}" -H "${AUTH}" \
    -H 'Content-Type: application/json' -d '{"status":"PAUSED"}' | jq -c "{\"$ID\": .}"
done
```

Nunca `DELETE`. Pausado guarda histórico e permite voltar atrás; deletado não.

Readback obrigatório depois de cada escrita:

```bash
curl -sG "${G}/{OBJECT_ID}" -H "${AUTH}" \
  --data-urlencode 'fields=id,name,status,daily_budget,lifetime_budget,start_time,end_time,is_dynamic_creative,targeting,budget_remaining' | jq .
```

Compare campo por campo com o enviado, em tabela `campo | enviado | lido | ok?`. Divergência em toggle de IA ou em teto é bloqueio, não observação.

Sem idempotência da ponte, um `POST` que deu timeout pode ter criado o objeto. Antes de repetir, liste e procure pelo nome. Repetir às cegas é como nasce campanha duplicada gastando em silêncio.

## 8. Paginação

A API devolve página. Ignorar isso é ler metade da conta e concluir com confiança:

```bash
NEXT="${G}/${ACT}/ads?fields=id,name,effective_status&limit=100"
: > ads_todos.json
while [ -n "$NEXT" ]; do
  RESP=$(curl -s "$NEXT" -H "${AUTH}")
  echo "$RESP" | jq -c '.data[]' >> ads_todos.json
  NEXT=$(echo "$RESP" | jq -r '.paging.next // empty')
done
wc -l ads_todos.json
```

A URL de `paging.next` já vem com os parâmetros. Ela também costuma vir com token embutido quando a chamada original usou token na query, que é mais um motivo para usar cabeçalho.

## 9. Erros e limite de taxa

| Código | O que é | O que fazer |
|---|---|---|
| 17 | limite de taxa do usuário | esperar e repetir com espera crescente |
| 32 | limite de taxa da página | mesma coisa, e reduzir a frequência de leitura |
| 613 | limite de chamada da conta de anúncio | esperar a janela virar, e agrupar campos em vez de fazer várias chamadas |
| 100 | parâmetro inválido | ler `error_user_title` e conferir nome de campo no changelog da versão |
| 190 | token inválido ou expirado | token pessoal expirado, ou permissão removida; trocar por System User |
| 200 | permissão insuficiente | faltou `ads_management` ou `ads_read` no token |
| 2 | erro temporário da plataforma | repetir depois; não é payload errado |

Nunca repita em laço cego. Taxa de erro alta em janela móvel pesa contra a conta, e chamada malfeita tem custo administrativo além do técnico. Quando o volume for grande, prefira relatório assíncrono a repetir chamada síncrona.

Sempre que uma chamada falhar, guarde `error_code`, `error_subcode` e `error_user_title`. Diagnóstico com a mensagem crua resolve em um passo o que "deu erro" leva três para resolver.
