# Pré-voo: a varredura que evita descobrir bloqueio um de cada vez

Leia isto **antes** de desenhar estrutura, escrever copy ou perguntar qualquer ID. É a Fase 0 da skill.

## Por que este arquivo existe

Numa investida real de R$ 100, a subida levou várias horas não por causa da decisão de mídia, que ficou pronta rápido, mas porque cada bloqueio apareceu sozinho, depois do anterior resolvido. A sequência foi esta:

1. `spend_cap` de campanha recusado por piso de moeda
2. janela de atribuição recusada pela otimização escolhida
3. `creative_features_spec` com nomes de campo que não existem mais
4. `video_id` inválido porque o vídeo estava no acervo errado
5. `image_hash` inválido pelo mesmo motivo
6. miniatura obrigatória, descoberta só na terceira tentativa
7. app em modo de desenvolvimento bloqueando criativo
8. app exigindo URL de política de privacidade que não existia
9. chave de leitura não recuperável do painel
10. `locales` apontando para inglês sem ninguém perceber

Nenhum desses é difícil. O custo foi a **serialização**: cada um só apareceu quando o anterior saiu do caminho, e cada um custou uma ida e volta com a pessoa.

A varredura abaixo encontra os dez de uma vez, em minutos, antes de qualquer trabalho de mídia. Rode ela inteira e reporte o resultado em bloco, não pergunta a pergunta.

## Parte 1: o que a pessoa precisa ter em mãos

Peça isto **de uma vez só**, em uma mensagem, não pingado. Se a ficha da conta (`assets/ficha_conta.md`) já existir no projeto, a maior parte já está respondida e você só confirma o que mudou.

| # | Item | Por que trava se faltar |
|---|---|---|
| 1 | Envelope: valor teto, data de início, data de fim | Define banda de decisão e estrutura. Sem isso não existe proposta, só chute |
| 2 | Meta de CPL de referência | Sem meta, "melhor" não tem definição e o diagnóstico não fecha |
| 3 | `PONTE_READ_KEY` vigente | Sem ela não há readback por API, e readback é o que prova que o Advantage+ não voltou |
| 4 | Confirmação de que o app da ponte está publicado | App em desenvolvimento bloqueia criação de criativo, e o conserto exige URL pública |
| 5 | Criativo final, no formato do posicionamento pretendido | Trocar formato depois muda posicionamento, que muda CPM, que muda a leitura |
| 6 | Onde vive o registro de rodadas | Fase 6 não fecha sem lugar definido, e registro espalhado não é registro |

Diga por que precisa de cada um em uma linha. Pedir seis coisas sem justificar soa burocrático; pedir seis coisas explicando o que cada uma destrava soa como alguém que já fez isso antes.

## Parte 2: a varredura mecânica

Rode `scripts/prevoo.py` para gerar o bloco de sondagem, execute pelo navegador contra a ponte, e cole o JSON de volta no script para o veredito. Se preferir fazer na mão, é isto que ele testa:

### Bloco A — ponte e conta

`GET /api/health`, sem chave nenhuma. Devolve de uma vez: versão da API, conta configurada, `account_status`, `disable_reason`, `min_daily_budget`, `spend_cap` e `amount_spent` da conta, e o teto de verba que a própria ponte impõe.

| Sintoma | Causa |
|---|---|
| não responde | ponte fora do ar, ou o container tentando alcançar domínio bloqueado. Use o navegador |
| `account_status` diferente de 1 | conta restrita. Nada de mídia resolve isso |
| `min_daily_budget` maior que o envelope dividido pelos dias | a janela é longa demais. Encurte a janela, não afine a diária |

### Bloco B — contrato de escrita

`POST /api/criar` com corpo `{}` e a chave de escrita. A ponte recusa e a mensagem de erro **ensina o contrato**: cabeçalho de idempotência obrigatório, campo `tipo`, campo `payload`.

Faça isso mesmo achando que conhece o contrato. Ponte é código de alguém, muda entre versões, e descobrir o formato por erro controlado custa dois segundos.

### Bloco C — chave de leitura

`GET /api/estrutura?nivel=campaign` com a chave de leitura.

**Armadilha conhecida:** se as variáveis de ambiente estiverem marcadas como sensíveis na Vercel, elas são graváveis e **não legíveis**. Ninguém recupera a chave do painel. Então ou a pessoa tem o valor guardado em outro lugar, ou precisa gerar uma nova e fazer deploy.

Se não houver chave de leitura, **diga o que isso custa antes de seguir**: todo readback passa a ser leitura de tela, com procedência `UI` em vez de `API`. Dá para operar, mas a garantia de que os toggles de IA continuam desligados fica visual, não verificada.

### Bloco D — modo do app

Abra `developers.facebook.com/apps`. O card do app mostra "Modo: Em desenvolvimento" ou publicado.

Este é o bloqueio mais caro da lista, porque só aparece na hora de criar o criativo, quando todo o resto já está pronto:

```
error_subcode 1885183
"O post do criativo dos anúncios foi criado por um app que está em modo de desenvolvimento.
 Ele deve estar em modo público para criar este anúncio."
```

Publicar exige, nas configurações básicas, **URL de política de privacidade** e **categoria**. Em cliente sem site isso vira bloqueio de projeto, não de execução.

Saída barata quando não há site: a política não precisa morar no mesmo lugar do produto, precisa de uma URL pública. GitHub Pages num repositório do próprio time resolve em minutos e não encosta em nada que já esteja no ar. Cuidado com o inverso: **não** aponte um projeto Vercel existente para um repositório vazio só para ganhar hospedagem, porque o primeiro deploy substitui o que está no ar pelo conteúdo do repo.

### Bloco E — ativos de mídia no acervo certo

Existem **dois acervos diferentes** e só um serve para anúncio:

| Acervo | Rota | Serve para anúncio? |
|---|---|---|
| Mídia da empresa | `/asset_library/business_creatives` | **não.** Devolve ID de ativo de portfólio |
| Mídia da conta de anúncios | `/asset_library/ad_accounts` | sim |

Usar o ID do acervo errado dá `Param video_id is not a valid video_id ID` ou "Imagem não encontrada", e a mensagem não diz nada sobre acervo, então a pessoa fica procurando no lugar errado.

Como pegar o valor certo, com o seletor de conta no topo apontando para a conta de anúncio correta:

- `video_id`: painel de detalhes do vídeo, botão **"Copiar identificação do vídeo"**. Vai para a área de transferência, dá para ler com `navigator.clipboard.readText()`.
- `image_hash`: painel de detalhes da imagem, campo **"Hash"**. São 32 caracteres hexadecimais.

**Regra de bolso que economiza uma rodada inteira:** ID numérico de 16 dígitos nunca é hash. Se a pessoa mandar um número onde você espera hash, ela está lendo o campo errado da tela, e vale dizer isso antes de tentar aplicar.

### Bloco F — miniatura de vídeo é obrigatória

`video_data` exige `image_hash` ou `image_url`. Sem um dos dois:

```
error_subcode 1443226 — "Seu anúncio precisa de uma miniatura de vídeo"
```

A Meta gera miniaturas automáticas no upload e elas ficam no acervo da conta, mas costumam cair em quadro de transição escuro, que fica feio na prévia do Feed do Facebook. Escolher o quadro e subir como imagem é um passo a mais que vale a pena, e o editor do anúncio também deixa escolher outro quadro do próprio vídeo em "Editar mídia".

### Bloco G — piso de `spend_cap` por moeda

Em BRL o `spend_cap` de campanha tem mínimo de **R$ 300,00** (`error_subcode 2446307`).

Consequência direta: **em investida abaixo disso, a segunda camada de teto não existe.** Sobram `lifetime_budget` com `end_time` e o readback. Isso precisa ser dito no gate, porque o desenho passa de três camadas para duas e a pessoa merece saber em quantas travas está confiando.

Quando o envelope não couber, a resposta certa é remover o campo, nunca inflar o teto para caber.

### Bloco H — janela de atribuição é restringida pela otimização

`attribution_spec` não é livre. Com `optimization_goal: CONVERSATIONS`, a Meta aceita só `window_days: 1` (`error_subcode 1885423`).

Não copie 7d click de outra campanha. E quando comparar com histórico, diga qual janela cada número usou: 1d click e 7d click não são a mesma base.

### Bloco I — `locales` e outros campos que falham em silêncio

`locales: [6]` **não é português**, é inglês dos EUA. Um conjunto criado assim mira brasileiro que usa Facebook em inglês, entrega quase nada, e nenhuma mensagem de erro aparece.

Em campanha de país único, o certo normalmente é **não enviar `locales`**. A própria tela explica: idioma só entra para limitar a um idioma incomum na localização escolhida. Para Brasil, português é o comum, então preencher só encolhe alcance sem ganhar nada.

Regra geral que esse caso ensina: campo que a API aceita sem reclamar mas que você não conferiu no readback é dívida silenciosa. Prefira não enviar a enviar um ID que você não confirmou.

### Bloco J — cargos em português são separados por gênero

Na busca de segmentação detalhada, "Advogado - Sócio Proprietário" e "Advogada - Sócia Proprietária" são **nós diferentes**, com tamanhos diferentes. Usar só a forma masculina deixa metade do ICP de fora.

Vale para qualquer cargo em português. Ao montar segmentação por cargo, procure as duas formas sempre.

Também vale separar o que a Meta chama de cada coisa, porque os rótulos enganam:

| Rótulo na busca | O que é de verdade |
|---|---|
| "Direito" como **campo de estudo** | quem declarou formação em Direito: dominado por estudante e bacharel que não advoga |
| "Ramos do direito" como **interesse** | afinidade genérica, pior ainda para B2B |
| "Advogado - Sócio Proprietário" como **cargo** | o ICP de verdade quando o cliente é escritório |
| "Escritório da Advocacia" como **empregador** | quem trabalha em escritório, sócio ou não |

### Bloco K — rascunhos soltos no gerenciador

Depois de qualquer publicação pelo Ads Manager, confira a barra superior: "Conferir e publicar (N)" com N maior que zero significa rascunho pendente.

O gerenciador cria rascunhos sozinho ao abrir editores, e eles nascem com o botão ligado. Um rascunho "Novo anúncio de Engajamento" esquecido vira anúncio ativo no próximo clique distraído de outra pessoa. Descarte o que não for seu, e confira que sobrou só o que você criou.

## Parte 3: como reportar

Devolva a varredura como **um bloco só**, com três listas:

1. **Verde**: o que está pronto, com o número que prova (versão da API, `min_daily_budget`, modo do app).
2. **Bloqueia agora**: o que impede a subida, com o conserto ao lado e quem faz.
3. **Vai doer depois**: o que não impede hoje mas cobra juros (sem chave de leitura, sem site, token exposto não rotacionado).

Essa separação importa porque mistura de urgências é o que faz a pessoa ignorar a lista inteira. Um item que bloqueia e um item que incomoda não podem aparecer com o mesmo peso.

Só depois desse bloco comece a Fase 1.
