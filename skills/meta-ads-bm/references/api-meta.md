# Marketing API: campos, payloads e desligamento de IA

Índice:
1. Versão e como conferir
2. Leitura: insights e estrutura
3. Checklist de desligamento de IA da Meta
4. Payload de campanha
5. Payload de conjunto de anúncios
6. Payload de criativo e anúncio
7. Teto de gasto: lifetime_budget, spend_cap e mínimo diário
8. Públicos: custom audience, lookalike e exclusão
9. Diagnóstico de entrega: effective_status e issues_info
10. Escrita segura: validate_only, idempotência, readback
11. Erros comuns

---

## 1. Versão e como conferir

Referência desta skill: **v26.0**, lançada em 29/07/2026. A v25.0 saiu em 18/02/2026 e a v23.0 morreu em 09/06/2026.

Nome de campo muda entre versões e a Meta bloqueia chamada legada fora de ciclo. Então:

- A ponte fixa a versão em variável de ambiente (`META_API_VERSION`), nunca hardcoded em cada rota.
- Antes de gerar payload para uma estrutura nova, confirme no changelog oficial se algum campo desta referência mudou. Se não houver acesso a busca no momento, gere o payload e trate a divergência no readback (seção 7) como esperada, não como falha.
- Nunca conclua que um toggle está desligado porque foi enviado desligado. Conclua pelo GET.

Mudanças recentes que afetam esta skill:
- `advantage_audience` precisa ser declarado explicitamente (0 ou 1) em conjunto novo ou copiado de campanha de categoria especial (crédito, emprego, habitação). Setup relaxado volta para 1.
- Posicionamento Instagram Explore saiu na v26.0. Remova de configuração antiga.
- `reach` está em retirada, substituída por contagem de espectadores. Planeje o relatório sem depender de `reach`.
- Chamadas legadas de Advantage+ estão bloqueadas em todas as versões.

## 2. Leitura: insights e estrutura

Insights, por nível:

```
GET /v26.0/act_{AD_ACCOUNT_ID}/insights
  ?level=ad                     # campaign | adset | ad
  &fields=campaign_name,adset_name,ad_name,campaign_id,adset_id,ad_id,
          spend,impressions,frequency,clicks,ctr,cpm,inline_link_clicks,
          inline_link_click_ctr,actions,cost_per_action_type,
          video_thruplay_watched_actions
  &time_range={"since":"2026-09-01","until":"2026-09-07"}
  &action_attribution_windows=["7d_click","1d_view"]
  &time_increment=1             # opcional, série diária
  &limit=200
```

Notas:
- `actions` e `cost_per_action_type` vêm como lista de objetos com `action_type` e `value`. O evento que importa para a Eyes Tech normalmente é `lead` ou `offsite_conversion.fb_pixel_lead`. Confirme qual está sendo populado antes de calcular CPL.
- Sempre puxe a janela anterior de igual tamanho para comparação. Sem período anterior, "subiu" e "caiu" não têm base.
- Volume grande pede relatório assíncrono (`POST .../insights` e polling do `report_run_id`). A resposta assíncrona hoje devolve `error_code`, `error_message`, `error_subcode` e `error_user_title`: use isso no diagnóstico em vez de tratar falha como vazio.
- Recorte por `breakdowns` (`age`, `gender`, `publisher_platform`, `platform_position`, `device_platform`, `country`) levanta hipótese de público e de formato. Recorte divide a amostra: o piso de `decisao.md` passa a valer por fatia, não pelo total, então recorte informa e raramente decide sozinho.
- Resposta vem paginada. Percorra `paging.next` até o fim antes de concluir qualquer coisa sobre a conta: ler a primeira página e fechar diagnóstico é o erro silencioso mais fácil de cometer em conta com muitos objetos.
- Autenticação em cabeçalho (`Authorization: Bearer`), nunca `access_token=` na URL. URL vaza em log de proxy, histórico de shell e print de tela, e a URL de `paging.next` carrega o token adiante quando a chamada original usou query.

Estrutura dos objetos ativos, para auditar configuração:

```
GET /v26.0/act_{AD_ACCOUNT_ID}/adsets
  ?fields=id,name,status,effective_status,daily_budget,lifetime_budget,
          bid_strategy,billing_event,optimization_goal,is_dynamic_creative,
          targeting,attribution_spec,learning_stage_info
  &limit=200
```

`targeting` é o objeto que revela IA de público. `learning_stage_info` diz se o conjunto está em aprendizado e quantos eventos faltam.

## 3. Checklist de desligamento de IA da Meta

Rode este checklist na criação e no readback. Um item por linha, com o valor que caracteriza manual.

| Recurso da Meta | Onde | Campo | Valor manual |
|---|---|---|---|
| Advantage campaign budget (CBO) | campanha | `daily_budget` / `lifetime_budget` | ausentes na campanha; verba fica no conjunto |
| Advantage+ audience | conjunto | `targeting.targeting_automation.advantage_audience` | `0` |
| Expansão de segmentação detalhada | conjunto | `targeting.targeting_relaxation_types` | `{"lookalike":0,"custom_audience":0}` |
| Posicionamento automático | conjunto | `targeting.publisher_platforms`, `facebook_positions`, `instagram_positions`, `device_platforms` | listas declaradas explicitamente |
| Criativo dinâmico | conjunto | `is_dynamic_creative` | `false` |
| Melhorias de criativo Advantage+ | criativo | `degrees_of_freedom_spec.creative_features_spec.*.enroll_status` | `"OPT_OUT"` em cada feature |
| Campanha Advantage+ pronta | campanha | tipo de campanha | criar campanha manual, não Advantage+ |
| Recomendações automáticas do gerenciador | interface | nenhum | ignorar; não aplicar sugestão da interface |

Features de criativo que aparecem em `creative_features_spec` e devem sair todas com `OPT_OUT`: `standard_enhancements`, `image_touchups`, `image_brightness_and_contrast`, `text_optimizations`, `image_templates`, `media_type_automation`, `product_extensions`, `description_automation`, `adapt_to_placement`, `catalog_feed_tags`, `site_extensions`. A lista cresce a cada versão: no readback, se voltar feature que não está aqui com `enroll_status` diferente de `OPT_OUT`, reporte como pendência e adicione a esta tabela.

Bloco reutilizável para o conjunto:

```json
"targeting": {
  "geo_locations": { "countries": ["BR"] },
  "age_min": 28,
  "age_max": 60,
  "publisher_platforms": ["facebook", "instagram"],
  "facebook_positions": ["feed"],
  "instagram_positions": ["stream", "story", "reels"],
  "device_platforms": ["mobile", "desktop"],
  "targeting_automation": { "advantage_audience": 0 },
  "targeting_relaxation_types": { "lookalike": 0, "custom_audience": 0 }
}
```

Bloco reutilizável para o criativo:

```json
"degrees_of_freedom_spec": {
  "creative_features_spec": {
    "standard_enhancements": { "enroll_status": "OPT_OUT" },
    "image_touchups": { "enroll_status": "OPT_OUT" },
    "text_optimizations": { "enroll_status": "OPT_OUT" },
    "media_type_automation": { "enroll_status": "OPT_OUT" },
    "adapt_to_placement": { "enroll_status": "OPT_OUT" }
  }
}
```

## 4. Payload de campanha

```
POST /v26.0/act_{AD_ACCOUNT_ID}/campaigns
```

```json
{
  "name": "ET | Leads | Implantacao CRM advocacia | 2026-09",
  "objective": "OUTCOME_LEADS",
  "status": "PAUSED",
  "special_ad_categories": [],
  "buying_type": "AUCTION"
}
```

Sem `daily_budget` aqui: verba na campanha é CBO, e CBO é a Meta distribuindo verba entre conjuntos. A distribuição é nossa.

`special_ad_categories` vazio só se o anúncio realmente não tocar crédito, emprego ou habitação. Declarar errado é violação de política, não otimização.

## 5. Payload de conjunto de anúncios

```
POST /v26.0/act_{AD_ACCOUNT_ID}/adsets
```

```json
{
  "name": "Advogado civel SP | Feed+Reels | Lead",
  "campaign_id": "{CAMPAIGN_ID}",
  "status": "PAUSED",
  "daily_budget": 8000,
  "billing_event": "IMPRESSIONS",
  "optimization_goal": "OFFSITE_CONVERSIONS",
  "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
  "promoted_object": {
    "pixel_id": "{PIXEL_ID}",
    "custom_event_type": "LEAD"
  },
  "is_dynamic_creative": false,
  "attribution_spec": [
    { "event_type": "CLICK_THROUGH", "window_days": 7 }
  ],
  "targeting": { "...bloco da seção 3..." }
}
```

Pontos de atenção:
- Verba em centavos. `8000` é R$ 80,00. Erro de duas ordens de grandeza aqui é o erro mais caro possível: confira antes de enviar e mostre o valor em reais no gate.
- `bid_strategy` com teto (`LOWEST_COST_WITH_BID_CAP`, `COST_CAP`) dá mais controle e entrega menos. Se propor teto, traga o trade-off.
- `optimization_goal` define o que a Meta persegue. Otimizar por clique quando o objetivo é lead traz volume e piora qualidade. Otimizar por conversão exige volume de evento para sair do aprendizado.

## 6. Payload de criativo e anúncio

```
POST /v26.0/act_{AD_ACCOUNT_ID}/adcreatives
```

```json
{
  "name": "Criativo | Estatico | Triagem de caso | v1",
  "object_story_spec": {
    "page_id": "{PAGE_ID}",
    "link_data": {
      "image_hash": "{IMAGE_HASH}",
      "link": "https://exemplo.com.br/lp?utm_source=meta&utm_medium=cpc&utm_campaign={{campaign.name}}&utm_content={{ad.name}}",
      "message": "[copy principal]",
      "name": "[titulo]",
      "description": "[descricao]",
      "call_to_action": { "type": "LEARN_MORE" }
    }
  },
  "degrees_of_freedom_spec": { "...bloco da seção 3..." }
}
```

```
POST /v26.0/act_{AD_ACCOUNT_ID}/ads
```

```json
{
  "name": "Estatico | Triagem de caso | v1",
  "adset_id": "{ADSET_ID}",
  "creative": { "creative_id": "{CREATIVE_ID}" },
  "status": "PAUSED"
}
```

UTM sempre preenchida, com `utm_content` no nível do anúncio. Sem isso o rastreio de origem no CRM quebra e a decisão de verba volta a depender só do número da Meta.

Imagem entra por upload prévio (`POST /adimages`) e vídeo por `POST /advideos`; use o `hash` ou `video_id` retornado.

## 7. Teto de gasto: lifetime_budget, spend_cap e mínimo diário

Verba diária não é teto. A entrega pode passar do valor do dia e compensar ao longo da semana, então quem precisa garantir "no máximo R$ 100" usa orçamento total com data de fim, não diária.

Mínimo diário da conta, antes de definir qualquer verba:

```
GET /v26.0/act_{AD_ACCOUNT_ID}
  ?fields=currency,timezone_name,min_daily_budget_low_freq,min_daily_budget_high_freq,spend_cap,amount_spent,balance
```

Os mínimos vêm na unidade menor da moeda e variam por tipo de cobrança. Não chute: leia da conta. Diária abaixo do mínimo não entrega, e o sintoma é entrega zero sem nenhuma reprovação, o que faz perder tempo procurando problema de criativo.

Conjunto com orçamento total e janela fechada:

```json
{
  "name": "Advogado civel SP | Feed+Reels | LPV",
  "campaign_id": "{CAMPAIGN_ID}",
  "status": "PAUSED",
  "lifetime_budget": 10000,
  "start_time": "2026-09-10T00:00:00-0300",
  "end_time": "2026-09-17T23:59:00-0300",
  "billing_event": "IMPRESSIONS",
  "optimization_goal": "LANDING_PAGE_VIEWS",
  "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
  "is_dynamic_creative": false,
  "targeting": { "...bloco da seção 3..." }
}
```

`lifetime_budget` exige `end_time`. Sem data de fim a API recusa, e é essa exigência que faz o teto valer de fato.

Segunda barreira, na campanha:

```
POST /v26.0/{CAMPAIGN_ID}
{ "spend_cap": 10000 }
```

Terceira camada, na conta inteira, com efeito colateral que precisa ser dito antes de propor:

```
POST /v26.0/act_{AD_ACCOUNT_ID}
{ "spend_cap": 10000 }
```

O limite de conta para tudo que estiver rodando nela, não só a investida nova, e depois de atingido exige ação manual para voltar. Só proponha em conta com uma campanha só.

Valores em centavos. R$ 100,00 é `10000`. Confirme no gate em reais, não em centavos: é onde o erro de duas casas passa despercebido.

Readback específico de teto, antes de ativar:

```
GET /v26.0/{ADSET_ID}?fields=lifetime_budget,daily_budget,start_time,end_time,budget_remaining
GET /v26.0/{CAMPAIGN_ID}?fields=spend_cap,daily_budget,lifetime_budget
```

`daily_budget` presente junto de `lifetime_budget` é configuração conflitante: resolva antes de ativar. `budget_remaining` é o número a acompanhar durante a investida.

Alterar `lifetime_budget` no meio do voo muda o ritmo de entrega do que restou e mexe no aprendizado. Se o envelope aumentar, prefira encerrar a investida, registrar e abrir a próxima com o novo teto, em vez de esticar a atual.

## 8. Públicos: custom audience, lookalike e exclusão

Escala em público estreito depende de público novo, não de mais verba. Então esta seção é usada com frequência.

Lista do CRM, com dado hasheado:

```
POST /v26.0/act_{AD_ACCOUNT_ID}/customaudiences
{ "name": "Clientes Eyes Tech | 2026-09", "subtype": "CUSTOM", "customer_file_source": "USER_PROVIDED_ONLY" }

POST /v26.0/{AUDIENCE_ID}/users
{
  "payload": {
    "schema": ["EMAIL_SHA256", "PHONE_SHA256"],
    "data": [["<sha256 do e-mail normalizado>", "<sha256 do telefone em E.164 sem +>"]]
  }
}
```

Normalize antes de hashear: minúsculas, sem espaço nas pontas, telefone só dígitos com código do país. Hash errado não dá erro, só entrega match baixo, e aí a conclusão sai errada sobre o público, não sobre o hash. Nunca envie e nunca exiba o dado em texto claro, e não cole lista de lead no chat.

Lookalike:

```
POST /v26.0/act_{AD_ACCOUNT_ID}/customaudiences
{
  "name": "LAL 1% | Clientes | 2026-09",
  "subtype": "LOOKALIKE",
  "origin_audience_id": "{AUDIENCE_ID}",
  "lookalike_spec": { "type": "similarity", "country": "BR", "ratio": 0.01 }
}
```

Semente pequena gera lookalike ruim. Com base de clientes de escritório, semente abaixo de algumas centenas costuma não sustentar 1%: nesse caso, prefira semente de comportamento (quem converteu no site) e faixa maior.

Exclusão, no `targeting` do conjunto de prospecção:

```json
"excluded_custom_audiences": [
  { "id": "{ID_CLIENTES}" },
  { "id": "{ID_LEADS_90D}" }
]
```

Prospecção sem exclusão gasta verba falando com quem já é cliente ou já é lead, e infla o número de "lead" repetido. Exclusão é padrão, não exceção.

## 9. Diagnóstico de entrega: effective_status e issues_info

Antes de qualquer teoria de performance, leia o estado real do objeto:

```
GET /v26.0/{AD_ID}?fields=effective_status,issues_info,ad_review_feedback,configured_status
```

- `effective_status`: `ACTIVE`, `PAUSED`, `PENDING_REVIEW`, `DISAPPROVED`, `WITH_ISSUES`, `CAMPAIGN_PAUSED`, `ADSET_PAUSED`.
- `issues_info`: motivo e nível do problema, com o caminho de recurso.
- `ad_review_feedback`: detalhe da reprovação, quando houver.

Entrega em zero com `PAUSED` ou `DISAPPROVED` não é problema de leilão nem de criativo, e propor mudança de verba nesse caso é ruído. Anúncio reprovado não se recria em loop: repetição de reprovação pesa na conta.

Pixel mudo é a outra causa silenciosa. Confirme evento chegando na janela recente antes de acusar o criativo:

```
GET /v26.0/{PIXEL_ID}/stats?aggregation=event
```

## 10. Escrita segura: validate_only, idempotência, readback

Validação antes de criar de verdade:

```json
{ "...payload...", "execution_options": ["validate_only"] }
```

Retorno de sucesso na validação significa payload aceito, não campanha criada. Diga isso com clareza para não gerar falsa sensação de que já está no ar.

Idempotência: a ponte guarda em Redis a chave `idem:{hash-do-payload}` com o ID retornado e TTL de 24h. Retry com a mesma chave devolve o ID salvo em vez de criar objeto novo. Sem isso, um timeout de rede vira duas campanhas gastando.

Readback, obrigatório depois de cada escrita:

```
GET /v26.0/{OBJECT_ID}?fields=id,name,status,daily_budget,is_dynamic_creative,targeting,degrees_of_freedom_spec
```

Compare campo por campo com o enviado e reporte em tabela `campo | enviado | lido | ok?`. Divergência em toggle de IA é bloqueio: não ative o objeto até resolver.

Limite de taxa: a conta tem cota por janela e a ponte responde 429 quando estoura. Trate com backoff exponencial e nunca em loop cego. A partir de 2026 o limiar de auto-aprovação de tier caiu para 500 chamadas em 15 dias, e taxa de erro acima de 15% em janela móvel de 500 requisições pesa contra a conta: chamada malfeita tem custo administrativo, não só técnico.

## 11. Erros comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Objeto criado mas não entrega | ficou `PAUSED`, ou anúncio em revisão | conferir `effective_status` |
| CPL "zerado" no insights | evento de conversão diferente do consultado | listar `actions` cru e achar o `action_type` real |
| Público muito maior que o definido | `advantage_audience` voltou 1 | readback e correção antes de ativar |
| Campo rejeitado | mudou de nome na versão | conferir changelog e ajustar a ponte |
| Duas campanhas iguais | retry sem idempotência | pausar a duplicada, corrigir a chave na ponte |
| `reach` vazio | métrica em retirada | usar impressões e frequência |
| Metade dos objetos "sumiu" | resposta paginada lida só na primeira página | percorrer `paging.next` até o fim |
| Erro 17, 32 ou 613 | limite de taxa por usuário, página ou conta | espera crescente, agrupar campos, relatório assíncrono |
| Erro 190 ou 200 | token expirado ou sem permissão | trocar por System User com `ads_management`, `ads_read`, `business_management` |
| Erro 100 com campo válido "ontem" | nome de campo mudou na versão | conferir changelog e ajustar a ponte |

Códigos de erro completos e os comandos executáveis correspondentes estão em `references/comandos-curl.md`, que também cobre o caminho degradado quando a ponte não está disponível.
