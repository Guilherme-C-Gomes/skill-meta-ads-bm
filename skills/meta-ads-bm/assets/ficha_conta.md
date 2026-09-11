# Ficha da conta: Meta Ads Eyes Tech

Preencher uma vez, atualizar quando mudar. Sem isso, cada rodada recomeça perguntando o que já foi respondido.

Nada de token nesta ficha. Token vive só em variável de ambiente na Vercel.

## Identificação

| Campo | Valor |
|---|---|
| BM (nome e ID) | |
| Conta de anúncio (`act_...`) | |
| Página do Facebook (ID) | |
| Conta do Instagram (ID) | |
| Pixel (ID) | |
| Domínio verificado | |
| Moeda e fuso da conta | BRL / America/Sao_Paulo |
| Ponte: URL base | |
| Ponte: versão da API | v26.0 |
| Onde vive o registro de rodadas | |

## Meta e limites

| Campo | Valor |
|---|---|
| Evento de conversão real (`action_type`) | ex. `offsite_conversion.fb_pixel_lead` |
| Meta de CPL (R$) | |
| Meta de custo por reunião (R$) | |
| Verba diária total teto (R$) | |
| Envelope padrão por investida (R$) | |
| Duração padrão da investida (dias) | |
| Mínimo diário da conta (R$) | ler em min_daily_budget_low_freq |
| Limite de gasto da conta, se houver (R$) | |
| Teto de verba por conjunto (R$) | |
| Janela de atribuição padrão | 7d click |
| Atraso típico de conversão (dias a descontar da janela) | 3, até calibrar |
| Origem do dado de qualidade de lead | CRM, campo/pipeline: |
| Última auditoria de conta (data e onde ficou) | |

## Limiares calibrados

Começam nos valores de `references/decisao.md` e são substituídos pelo histórico da conta. Registrar a data da última calibração, porque limiar antigo decide errado com confiança.

| Limiar | Padrão | Valor da conta | Calibrado em |
|---|---|---|---|
| Mínimo de conversões para decidir | 10 | | |
| Múltiplo da meta para cortar | 1,5x | | |
| Múltiplo da meta para reduzir verba | 1,2x | | |
| CTR de link mínimo | 0,4% | | |
| Frequência considerada alta (7d) | 2,5 | | |
| Passo de escala | +20% / 3 dias | | |

## Públicos em uso

| Nome | Tipo | ID | Observação |
|---|---|---|---|
| | custom / lookalike / salvo | | |

Exclusões que entram por padrão em todo conjunto de prospecção: lista de clientes, leads dos últimos 90 dias, visitantes que já converteram.

## Estrutura viva

| Campanha | Objetivo | Oferta | Status | Verba diária |
|---|---|---|---|---|
| | | | | |
