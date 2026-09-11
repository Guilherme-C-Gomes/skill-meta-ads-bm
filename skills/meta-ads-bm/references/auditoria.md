# Auditoria de conta: controles, achados e limites

Este arquivo serve ao pedido que não é "por que esse anúncio caiu", e sim "olha a conta inteira". Auditoria entrega valor sem escrever nada na conta, então é o primeiro trabalho útil quando a ponte acabou de subir ou quando ninguém olha a estrutura há meses.

Índice:
1. Quando usar e o que a auditoria não é
2. Coleta mínima
3. Controles por área
4. Formato do achado
5. O que não conta como achado
6. Severidade e ordenação
7. Fechamento

---

## 1. Quando usar e o que a auditoria não é

Use em: conta assumida agora, revisão trimestral, "está gastando e eu não sei se está certo", preparação antes de aumentar verba de forma relevante, e depois de qualquer período sem acompanhamento.

Auditoria **lê e classifica**. Ela não muda nada. Toda correção que sair dela vira proposta na Fase 3 e passa pelo gate da Fase 4, igual a qualquer outra escrita. Terminar a auditoria já tendo aplicado correção "óbvia" quebra o contrato da skill, e a correção óbvia é justamente a que costuma ter efeito colateral em aprendizado.

Auditoria também não é diagnóstico de performance. Ela responde "a conta está configurada de forma que o número signifique alguma coisa?". Se a medição está quebrada, todo diagnóstico de CPL feito antes de consertar isso é chute com casa decimal.

## 2. Coleta mínima

Antes de abrir qualquer controle, junte:

- Conta: moeda, fuso, `spend_cap`, `amount_spent`, `min_daily_budget_low_freq`, status da conta e do meio de pagamento.
- Estrutura: campanhas, conjuntos e anúncios com `status`, `effective_status`, verba, `optimization_goal`, `bid_strategy`, `targeting`, `attribution_spec`, `is_dynamic_creative`, `learning_stage_info`.
- Criativos ativos: `degrees_of_freedom_spec`, formato, data de criação.
- Medição: pixel, eventos recebidos nas últimas 24h e nos últimos 7 dias, domínio verificado, CAPI ativa ou não, deduplicação.
- Públicos: custom audiences e lookalikes em uso, tamanho, data de atualização, exclusões aplicadas.
- Insights dos últimos 30 dias por nível, em janela fechada (descontando o atraso de conversão da ficha).

O que não vier, vira linha de **dado faltante**, com a rota que traria. Auditoria com metade da coleta é honesta se disser qual metade.

## 3. Controles por área

Cada controle tem: o que ler, o que caracteriza achado, e por que importa. Rode na ordem, porque os primeiros invalidam a leitura dos últimos.

### 3.1 Medição (pixel, CAPI, deduplicação)

| Controle | Achado quando |
|---|---|
| Pixel recebendo evento | nenhum evento na janela de 24h com campanha ativa |
| Evento de conversão certo | o `action_type` otimizado não é o que o time considera lead |
| Domínio verificado | domínio da página de destino não verificado na BM |
| CAPI | ausente, ou presente sem `event_id` para deduplicar com o pixel |
| Deduplicação | mesmo evento contado duas vezes, inflando conversão e derrubando CPL artificialmente |
| Página de destino | evento dispara em página diferente da que o anúncio manda |

Por que vem primeiro: sem sinal chegando, otimização por conversão não tem o que otimizar e o CPL "explode" por falta de evento, não por criativo. Time inteiro já trocou criativo bom por causa de pixel mudo.

### 3.2 Atribuição

| Controle | Achado quando |
|---|---|
| Janela declarada | relatório em uso sem `action_attribution_windows` explícito |
| Janela uniforme | conjuntos comparados entre si com `attribution_spec` diferente |
| Comparação com CRM | número da Meta usado como se fosse o do CRM, sem rótulo |
| Atraso de conversão | decisão tomada sobre janela que ainda vai receber crédito |

Comparar dois conjuntos com janelas diferentes é comparar coisas diferentes com o mesmo nome. Isso aparece pouco e decide muito.

### 3.3 Estrutura

| Controle | Achado quando |
|---|---|
| Verba na campanha | `daily_budget` ou `lifetime_budget` na campanha, o que é CBO e devolve a distribuição para a Meta |
| Nomenclatura | objeto fora do padrão `ET \| objetivo \| oferta \| aaaa-mm`, o que quebra leitura de relatório |
| Fragmentação | muitos conjuntos com verba abaixo do mínimo diário, todos em aprendizado permanente |
| Objetos zumbis | campanha ativa sem anúncio ativo, ou anúncio ativo apontando para página fora do ar |
| Objetivo | `objective` incompatível com o resultado cobrado (tráfego contratado, lead esperado) |

### 3.4 Público

| Controle | Achado quando |
|---|---|
| Exclusão em prospecção | conjunto de prospecção sem excluir clientes e leads dos últimos 90 dias |
| Sobreposição | dois conjuntos ativos disputando o mesmo público no leilão |
| Semente de lookalike | semente pequena demais para sustentar a faixa escolhida |
| Base desatualizada | custom audience de lista sem atualização há meses |
| Amplitude | público estreito demais para a verba, ou amplo a ponto de a segmentação não significar nada |

### 3.5 Posicionamento

| Controle | Achado quando |
|---|---|
| Posicionamento declarado | `publisher_platforms` e as listas de posição ausentes, o que é automático |
| Posição extinta | configuração antiga ainda citando posicionamento removido na versão atual |
| Criativo por formato | um único formato servindo feed, story e reels sem adaptação, com `adapt_to_placement` desligado |

O último é armadilha: a decisão de desligar adaptação automática é nossa e está certa, mas ela obriga a entregar o criativo no formato de cada posição. Desligar e não adaptar entrega peça cortada.

### 3.6 Automação e IA da Meta

Rode o checklist da seção 3 de `api-meta.md` em todos os objetos ativos, que é o mesmo que a rota `/api/auditoria-ia` faz. Achado é qualquer toggle ligado, com o nome do objeto e o campo.

Aqui vale a honestidade da seção de abertura da skill: leilão e otimização de entrega não têm desligamento. Não registre isso como achado, registre como limite conhecido.

### 3.7 Verba e teto

| Controle | Achado quando |
|---|---|
| Teto real | investida com teto acordado usando só verba diária |
| `lifetime_budget` sem `end_time` | configuração que a API recusa ou que não trava nada |
| Conflito | `daily_budget` e `lifetime_budget` no mesmo conjunto |
| Mínimo diário | verba abaixo do mínimo da conta, com entrega em zero |
| `spend_cap` de conta | presente sem que o time saiba, o que para tudo ao ser atingido |
| Ritmo | gasto acumulado fora do previsto para a data, para mais ou para menos |

### 3.8 Criativo

| Controle | Achado quando |
|---|---|
| Diversidade | um criativo só carregando toda a conta, sem substituto pronto |
| Fadiga | frequência subindo com CTR caindo e CPM subindo, no padrão de `decisao.md` |
| Idade | criativo no ar além do prazo de reposição definido para a conta |
| UTM | `utm_content` ausente no nível do anúncio, o que quebra o rastreio no CRM |
| Consistência | promessa do anúncio diferente do que a página entrega, o que aparece como CTR bom e conversão ruim |

### 3.9 Política e OAB

| Controle | Achado quando |
|---|---|
| Reprovação | anúncio `DISAPPROVED` ou `WITH_ISSUES`, com `issues_info` lido |
| Reincidência | mesma reprovação recriada em loop, o que pesa na conta |
| Categoria especial | anúncio que toca crédito, emprego ou habitação sem `special_ad_categories` declarado |
| Discurso | copy que promete resultado, cita caso concreto ou sugere abordagem ativa de quem não procurou o escritório |

O último controle é da seção de OAB da skill. A Eyes Tech não está sujeita ao Provimento 205/2021, mas o público está, e copy que induz o escritório a prática vedada é achado, mesmo aprovada pela Meta. Sinalize o ponto e mande validar com o compliance do cliente, sem dar parecer jurídico.

## 4. Formato do achado

Um achado por linha, na tabela de saída:

| Área | Objeto (ID) | Observação | Fonte | Diagnóstico | Recomendação | Severidade |
|---|---|---|---|---|---|---|

Regras que fazem a tabela ser usável:

- **Observação** é o dado cru, com número e janela. Sem adjetivo e sem interpretação.
- **Fonte** é a procedência: `API`, `CSV` com data, `UI`, `CRM` com pipeline, `PESSOA`.
- **Diagnóstico** é hipótese e vai escrita como hipótese.
- **Recomendação** é a ação, no formato da Fase 3 quando implicar escrita.
- Nada de linha sem objeto identificado. "A conta tem problema de público" não é achado, é impressão.

Depois da tabela, três listas curtas: **contradições** (fontes que discordam, com os dois números), **dados faltantes** (o que traria a resposta) e **oportunidades não avaliadas** (o que apareceu e não dá para julgar agora).

## 5. O que não conta como achado

Encher a lista destrói a lista. Fora:

- Recurso indisponível para a conta, em beta ou restrito por elegibilidade.
- IA da Meta desligada por decisão nossa. Isso é conformidade, não achado.
- Diferença entre Meta e CRM dentro do esperado por janela de atribuição. Vira contradição só quando aponta direções opostas.
- Preferência de estilo sem efeito em número, como nome de criativo feio.
- Recomendação da interface do gerenciador. Ela é sugestão da plataforma, e a decisão é nossa.
- Objeto pausado há muito tempo, a menos que esteja pausado por engano e devesse estar rodando.

## 6. Severidade e ordenação

Três níveis, ordenados por efeito sobre dinheiro e sobre a validade do número:

| Nível | Critério | Exemplo |
|---|---|---|
| Bloqueante | invalida a leitura da conta ou gasta verba errado agora | pixel sem evento, conta sem teto real, conjunto duplicado disputando leilão |
| Relevante | degrada resultado ou decisão, sem invalidar tudo | prospecção sem exclusão, janela de atribuição inconsistente, criativo único |
| Registro | vale corrigir na próxima janela | nomenclatura fora do padrão, UTM incompleta em objeto de baixo gasto |

Ordene por severidade e, dentro dela, por gasto do objeto. Achado bloqueante em conjunto que gasta R$ 20 por mês não vem antes de achado relevante no conjunto que carrega a conta.

## 7. Fechamento

Termine com quatro coisas, nesta ordem:

1. Cobertura: quantos objetos ativos foram lidos com dado real, e o que ficou sem.
2. Os bloqueantes, em lista curta, com o que cada um custa se ficar como está.
3. A proposta de correção da rodada, no limite de 3 mudanças por conjunto, já no formato da Fase 3.
4. Data de reavaliação e onde o resultado da auditoria fica registrado.

Auditoria que não vira proposta com data é relatório, e relatório não muda conta.
