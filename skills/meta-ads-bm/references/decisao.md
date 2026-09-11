# Decisão: amostra, aprendizado, corte, escala e fadiga

Este arquivo existe para que a decisão não dependa de humor. Os limiares abaixo são ponto de partida calibrável, não lei. Quando o time tiver histórico próprio na conta, substitua pelos números da conta e registre a mudança.

## 1. Amostra: a pergunta antes de todas

Métrica de conversão em volume baixo oscila muito. Um conjunto com 4 leads a R$ 90 e outro com 3 leads a R$ 160 podem ser o mesmo conjunto em dias diferentes.

Piso para decidir corte ou escala por CPL:

| Situação | Piso |
|---|---|
| Conversão (lead) no objeto | 10 no período analisado |
| Gasto no objeto | pelo menos 3x a meta de CPL |
| Tempo no ar | 4 dias, e fora do aprendizado |

Abaixo do piso, a decisão certa é uma destas: manter e reavaliar em data marcada, ou aumentar deliberadamente a verba de teste para atingir amostra mais rápido (com o custo declarado). O que não se faz é matar objeto por 3 leads caros e depois não saber se aquilo funcionava.

Antes de aplicar esse piso, olhe o envelope. Se a verba total da investida for menor que 3x a meta de CPL, a amostra nunca vai fechar e não há nada a reavaliar: a investida é de sinal de topo de funil por construção, e a decisão certa é ler CTR de link, CPM e taxa de conversão da página. Rode `scripts/planejar_envelope.py` antes de prometer leitura de CPL.

Exceção legítima: sinal de topo de funil já é conclusivo com muito menos volume. CTR de link em 0,2% com 8.000 impressões não precisa de 10 leads para dizer que o criativo não está engajando.

## 2. Aprendizado

Conjunto sai do aprendizado depois de cerca de 50 eventos de otimização em 7 dias. Enquanto está lá, o custo por resultado é instável e não serve de base para decisão.

Consultar `learning_stage_info` na leitura de estrutura. Duas leituras que importam: se está em aprendizado, e se caiu em aprendizado limitado (volume insuficiente para sair, o que é um problema estrutural de verba ou de público estreito, não de criativo).

Edição relevante reinicia o aprendizado: mudança de otimização, de público, de criativo, de posicionamento e alteração grande de verba. Consequência prática: agrupe as mudanças de um conjunto em uma rodada só, e conte a partir dali. Ficar editando de dois em dois dias mantém o conjunto em aprendizado permanente, e aí nada do que se lê presta.

Aprendizado limitado com público muito pequeno pede consolidação de conjuntos, não mais criativo.

## 3. Corte

Cortar significa pausar, não deletar. Deletar destrói histórico e não devolve nada em troca.

Critérios, com amostra fechada:

| Sinal | Limiar de partida | Ação |
|---|---|---|
| CPL acima da meta | 1,5x a meta, com 10+ conversões | pausar o objeto |
| CPL entre 1,2x e 1,5x da meta | com 10+ conversões | reduzir verba em 30% e reavaliar em 4 dias |
| CTR de link muito baixo | abaixo de 0,4% com 5.000+ impressões | trocar criativo, não mexer em público |
| Zero conversão | gasto acima de 3x a meta de CPL | pausar |
| Frequência alta com CPL subindo | frequência acima de 2,5 em 7 dias | criativo novo ou ampliar público |

Antes de cortar por CPL, verifique se o problema é do anúncio ou da página. CTR bom com conversão ruim aponta para a página ou a oferta, e nesse caso cortar o anúncio esconde o problema em vez de resolver.

## 4. Escala

Escala é passo, não salto. Aumento grande de verba joga o conjunto de volta em aprendizado e costuma piorar o CPL exatamente no objeto que estava indo bem.

- Passo: +20% sobre a verba diária, no máximo a cada 3 dias, com leitura entre os passos.
- Só escala o que tem 10+ conversões e CPL igual ou abaixo da meta.
- Quando o objeto satura (verba sobe e CPL sobe junto, duas leituras seguidas), a saída é público novo em conjunto novo, não mais verba no mesmo lugar.
- Duplicar conjunto que funciona compete consigo mesmo no leilão quando o público é o mesmo. Duplicar faz sentido com público diferente, não com o mesmo público.

## 5. Fadiga de criativo

Sinais, em ordem de aparecimento: frequência subindo, CTR caindo, CPM subindo, CPL subindo. Quando os quatro aparecem juntos, é fadiga e não falta de verba.

Prazo típico de vida de criativo em público pequeno (que é o caso de um ICP estreito como escritório de advocacia) é curto. Trate reposição de criativo como rotina de calendário, não como reação a queda. O briefing do criativo novo sai daqui e a produção vai para as skills `image` e `video`.

## 6. Teste: um por vez, com hipótese escrita

Sem hipótese, teste não ensina nada, só gasta.

Formato:
- Hipótese: o que se acredita e por quê.
- Variável isolada: uma só (ângulo, formato, público, página).
- Métrica de decisão e limiar, definidos antes de subir.
- Data de leitura.

Se duas variáveis mudarem juntas, o resultado é inutilizável para decisão futura, mesmo que o número melhore.

## 7. Exclusão e sobreposição

Duas formas comuns de gastar verba contra si mesmo, e nenhuma das duas aparece como problema no relatório:

- **Prospecção sem exclusão.** Sem excluir clientes e leads recentes, parte da verba fala com quem já está na base, e o "lead" que volta é duplicado. Exclusão de lista de clientes e de leads dos últimos 90 dias entra por padrão em todo conjunto de prospecção.
- **Conjuntos disputando o mesmo público.** Duplicar o conjunto que vai bem, mantendo o mesmo público, coloca os dois no mesmo leilão. O CPM sobe e o resultado de cada um piora. Duplicar só faz sentido com público diferente, e mesmo assim com exclusão mútua quando a sobreposição for grande.

Ao propor público novo, diga qual é a exclusão que vai junto. Público novo sem exclusão declarada é proposta incompleta.

## 8. CPL da Meta versus CPL qualificado

Três números diferentes, que decidem coisas diferentes:

| Número | De onde vem | Serve para |
|---|---|---|
| CPL | Meta | comparar criativo e público dentro da plataforma, sinal rápido |
| CPL qualificado | CRM, leads que passaram a triagem | decidir verba entre conjuntos |
| Custo por reunião | CRM, agenda | decidir se a campanha se paga |

Com público estreito, é comum o criativo de CPL mais baixo trazer o lead que não fecha, porque copy vaga atrai qualquer um. Quando o CPL cai e o custo por reunião sobe, o problema é qualidade de lead, e cortar o anúncio "caro" nessa hora é o erro clássico.

Regra prática: se o CPL qualificado não estiver disponível, decida com o CPL da Meta e diga que a camada de qualidade está faltando. Decisão com dado parcial declarado é aceitável; decisão com dado parcial disfarçado de completo, não.

## 9. Por que os dois números nunca fecham

Janela de atribuição, desduplicação e cancelamento de lead são diferentes nas duas bases, então divergência é o estado normal, não erro de configuração.

Ao reportar, deixe explícito de onde veio cada número. Misturar as duas bases na mesma tabela sem rótulo é a forma mais comum de tomar decisão errada com dado certo. Quando as duas divergirem em direção (Meta diz que melhorou, CRM diz que piorou), o CRM manda.
