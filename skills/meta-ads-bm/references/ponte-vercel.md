# Ponte Meta Ads: Vercel serverless + Upstash Redis

A ponte existe por dois motivos: o ambiente onde a LLM roda script não tem rota para `graph.facebook.com`, e o token da conta não pode circular em conversa. A ponte concentra credencial, versão da API, idempotência e limite de taxa em um lugar só.

Se a skill `integracao-api` estiver disponível, ela manda na infraestrutura (estrutura de projeto, retry, fila, Redis, deploy, teste). Este arquivo trata só do que é específico de Meta.

## 1. Credenciais e onde ficam

| Variável | O que é | Como obter |
|---|---|---|
| `META_SYSTEM_USER_TOKEN` | token de System User da BM, sem expiração | Business Settings > Usuários do sistema > gerar token com `ads_management`, `ads_read`, `business_management` |
| `META_AD_ACCOUNT_ID` | ID da conta, sem o prefixo `act_` | Gerenciador de anúncios |
| `META_API_VERSION` | ex. `v26.0` | changelog oficial |
| `PONTE_WRITE_KEY` | chave que autoriza rotas de escrita | gerada por você, 32 bytes aleatórios |
| `PONTE_READ_KEY` | chave curta e rotativa das rotas de leitura | gerada por você, rotação semanal |
| `UPSTASH_REDIS_REST_URL` / `_TOKEN` | Redis | painel Upstash |

Regras:
- Token de System User nunca no chat, nunca no repositório, nunca em URL. Só em variável de ambiente da Vercel.
- Use System User, não token de usuário pessoal: token pessoal morre quando a pessoa troca senha ou sai da BM, e derruba a operação no pior momento.
- Peça à pessoa apenas o que falta. Se ela já configurou, peça a URL base e a rota de saúde, não as credenciais.

## 2. Rotas

Leitura (GET, autenticada por `PONTE_READ_KEY` em header, ou no path quando o consumo for por `web_fetch`):

| Rota | Faz |
|---|---|
| `GET /api/health` | devolve versão da API, ID da conta, hora do servidor |
| `GET /api/insights?level=ad&since=&until=&increment=` | insights no nível pedido, mais janela anterior de igual tamanho |
| `GET /api/estrutura?nivel=adset` | objetos ativos com campos de configuração e `learning_stage_info` |
| `GET /api/auditoria-ia` | roda o checklist da seção 3 de `api-meta.md` em todos os objetos ativos e devolve o que está com IA ligada |
| `GET /api/snapshot/{read-key}` | último payload de leitura salvo em Redis, para consumo por `web_fetch` |

Escrita (POST, autenticada por `PONTE_WRITE_KEY` em header):

| Rota | Faz |
|---|---|
| `POST /api/validar` | repassa o payload com `execution_options: ["validate_only"]` |
| `POST /api/criar` | cria campanha, conjunto, criativo ou anúncio; exige `Idempotency-Key` |
| `POST /api/atualizar` | altera status, verba ou targeting de um objeto; exige `Idempotency-Key` |
| `POST /api/pausar` | atalho para `status: PAUSED` em lote |

Desenho que evita acidente:
- Toda rota de escrita recusa payload sem `Idempotency-Key`.
- Toda criação força `status: PAUSED`, independente do que vier no payload. Ativar é chamada separada e explícita.
- `/api/atualizar` recusa alteração de verba acima de um teto configurável (`PONTE_LIMITE_VERBA_CENTAVOS`). Erro de casa decimal para de existir como risco.
- Nenhuma rota aceita instrução em texto livre. A ponte recebe campo tipado e devolve JSON. Ela não interpreta nada.

## 3. Redis: o que fica lá

| Chave | Conteúdo | TTL |
|---|---|---|
| `idem:{hash}` | ID retornado pela API para aquele payload | 24h |
| `snapshot:ultimo` | último resultado de leitura, para `web_fetch` | 1h |
| `rate:{janela}` | contador de chamadas na janela | conforme janela |
| `log:{timestamp}` | payload enviado, resposta, quem chamou | 90 dias |

O log de 90 dias serve para auditoria: quando alguém perguntar "por que essa campanha mudou de verba na quinta", a resposta tem que estar em algum lugar que não seja a memória de ninguém.

Não guarde dado pessoal de lead em Redis. Insight agregado e ID de objeto, nada de nome, telefone ou e-mail.

## 4. Ordem de construção

1. `/api/health` no ar, respondendo versão e conta. Sem isso, nada mais é testável.
2. `/api/insights`, testado contra uma janela conhecida e comparado com a interface do gerenciador. Divergência aqui é problema de janela de atribuição, não de código: resolva antes de seguir.
3. `/api/estrutura` e `/api/auditoria-ia`. A auditoria é o primeiro valor real entregue: ela mostra o que está ligado hoje sem escrever nada.
4. `/api/validar`. Escrita de mentira antes de escrita de verdade.
5. `/api/criar` e `/api/atualizar`, com idempotência e teto de verba.
6. `/api/pausar`.

Cada etapa termina em teste real e gate humano, no padrão da skill `integracao-api`. Não declare pronto sem teste real: payload que valida não é campanha que entrega.

## 5. Teste de aceite da ponte

Faça nesta ordem, com dado da conta:

- `health` devolve a versão esperada.
- `insights` de uma janela fechada bate com o gerenciador, na mesma janela de atribuição, com diferença explicável.
- `auditoria-ia` sinaliza corretamente um conjunto que você ligou o Advantage+ de propósito para testar.
- `validar` recusa payload com campo errado e devolve a mensagem da Meta.
- `criar` chamado duas vezes com a mesma `Idempotency-Key` devolve o mesmo ID e cria um objeto só.
- `atualizar` com verba acima do teto é recusado pela ponte, antes de chegar na Meta.
- Objeto criado no teste é pausado e apagado depois, e isso fica registrado.
