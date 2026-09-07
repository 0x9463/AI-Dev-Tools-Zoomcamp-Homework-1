# ChoreHub — Shared Household Chores Manager

## 1. Objetivo

Construir uma aplicação para uma única casa/grupo familiar, na qual um administrador organiza tarefas domésticas, atribui responsáveis, acompanha prazos e recorrências, valida conclusões e mantém um sistema simples de pontos e ranking.

O MVP deve priorizar clareza operacional, controle pelo administrador e um fluxo simples para os membros.

---

## 2. Papéis

### 2.1 Administrador

O administrador é responsável por:

- criar e gerenciar a casa;
- convidar membros;
- criar, editar, excluir e reatribuir tarefas;
- definir prioridade, categoria, prazo, recorrência e pontuação;
- aprovar ou rejeitar tarefas marcadas como concluídas;
- acompanhar tarefas pendentes, atrasadas e aguardando aprovação;
- consultar histórico e ranking.

### 2.2 Membro

O membro pode:

- visualizar todas as tarefas da casa;
- alterar apenas tarefas atribuídas a ele;
- marcar suas tarefas como concluídas;
- anexar uma foto opcional;
- comentar em suas tarefas;
- solicitar troca de responsável com justificativa;
- acompanhar seu próprio calendário;
- visualizar rankings.

---

## 3. Conta e acesso

### 3.1 Estrutura da casa

- Cada conta de administrador gerencia apenas uma casa.
- O administrador é o único responsável por adicionar membros.
- Membros entram somente por convite enviado por e-mail.

### 3.2 Cadastro do membro

O membro convidado pode criar sua conta por:

- e-mail e senha; ou
- login social.

### 3.3 Regra crítica adicionada

Para simplificar o MVP:

- um membro não pode entrar em outra casa enquanto estiver vinculado à casa atual;
- membros não podem sair da casa por conta própria no MVP;
- somente o administrador pode removê-los.

**Justificativa:** isso evita conflitos de propriedade, histórico, pontos e permissões durante a primeira versão.

---

## 4. Tarefas

### 4.1 Criação

Somente o administrador pode criar tarefas.

Cada tarefa deve possuir:

- título;
- descrição opcional;
- responsável;
- categoria;
- prioridade;
- pontos;
- prazo opcional;
- recorrência opcional;
- data de criação;
- status.

### 4.2 Prioridade

Valores disponíveis:

- Baixa
- Média
- Alta
- Urgente

### 4.3 Categorias

O sistema deve oferecer categorias iniciais, por exemplo:

- Limpeza
- Cozinha
- Compras
- Organização

O administrador também pode criar novas categorias.

### 4.4 Prazo

O prazo é opcional.

Uma tarefa com prazo que ultrapasse a data/hora limite sem conclusão deve ser marcada automaticamente como **Atrasada**.

### 4.5 Recorrência

O MVP deve suportar:

- diária;
- semanal;
- mensal;
- dias específicos da semana.

### 4.6 Regra crítica adicionada para recorrência

Cada ocorrência recorrente deve gerar uma instância própria da tarefa.

Exemplo:

> “Lavar a louça — toda segunda-feira”

Cada segunda-feira gera uma nova ocorrência independente, preservando o histórico das anteriores.

**Justificativa:** editar a mesma tarefa repetidamente destruiria o histórico e prejudicaria o ranking.

---

## 5. Status das tarefas

O MVP deve usar os seguintes status:

1. **Pendente** — criada e ainda não concluída;
2. **Atrasada** — prazo expirado sem conclusão;
3. **Aguardando aprovação** — membro informou conclusão;
4. **Concluída** — administrador aprovou;
5. **Cancelada** — administrador cancelou a tarefa.

### 5.1 Rejeição da conclusão

Quando o administrador rejeitar uma conclusão:

- deve informar obrigatoriamente um comentário;
- a tarefa volta para **Pendente**;
- o comentário fica registrado no histórico.

Se o prazo original já tiver expirado, ela retorna como **Atrasada**.

---

## 6. Fluxo de conclusão

1. O membro executa a tarefa.
2. Pode adicionar um comentário.
3. Pode anexar uma foto opcional.
4. Marca a tarefa como concluída.
5. O status passa para **Aguardando aprovação**.
6. O administrador analisa.
7. O administrador pode:
   - aprovar; ou
   - rejeitar com comentário obrigatório.
8. Os pontos só são creditados após aprovação.

---

## 7. Edição e reatribuição

O administrador pode editar qualquer campo da tarefa a qualquer momento.

Também pode reatribuir a tarefa para outro membro a qualquer momento.

### 7.1 Regra crítica adicionada

Toda alteração relevante deve registrar:

- quem realizou a alteração;
- data/hora;
- valor anterior;
- novo valor.

Isso vale especialmente para:

- responsável;
- prazo;
- prioridade;
- pontos;
- status.

**Justificativa:** como o administrador pode editar tarefas mesmo depois de atribuídas, um pequeno histórico de alterações evita inconsistências e disputas.

---

## 8. Solicitação de troca

O membro pode solicitar ao administrador a troca de uma tarefa.

A solicitação deve conter:

- tarefa;
- membro solicitante;
- justificativa obrigatória;
- data da solicitação;
- status da solicitação.

Status possíveis:

- Pendente
- Aceita
- Recusada

Somente o administrador decide se a troca será realizada.

---

## 9. Comentários e anexos

### 9.1 Comentários

Podem comentar:

- administrador;
- membro responsável pela tarefa.

Outros membros podem visualizar a tarefa, mas não comentar.

### 9.2 Fotos

O responsável pode anexar uma foto opcional como evidência da execução.

### 9.3 Limitação sugerida para o MVP

Permitir no máximo uma imagem por submissão de conclusão.

**Justificativa:** reduz complexidade de armazenamento e interface sem impedir o principal caso de uso.

---

## 10. Pontos

Cada tarefa possui uma quantidade de pontos.

O sistema sugere uma pontuação inicial com base na prioridade:

| Prioridade | Pontos sugeridos |
|---|---:|
| Baixa | 5 |
| Média | 10 |
| Alta | 20 |
| Urgente | 30 |

O administrador pode alterar o valor sugerido antes ou depois da criação da tarefa.

Os pontos somente são creditados quando a tarefa é aprovada.

### 10.1 Regra crítica adicionada

Depois que uma tarefa for aprovada, os pontos registrados naquela conclusão ficam congelados para fins históricos.

Alterações futuras no valor padrão da tarefa recorrente afetam apenas novas ocorrências.

**Justificativa:** evita alterar retroativamente rankings já calculados.

---

## 11. Ranking

O sistema deve apresentar:

- ranking semanal;
- ranking mensal;
- ranking geral acumulado.

O ranking é baseado exclusivamente em pontos de tarefas aprovadas.

Não existem recompensas ou troca de pontos no MVP.

### 11.1 Critério de desempate sugerido

Em caso de empate em pontos:

1. maior número de tarefas aprovadas;
2. persistindo o empate, ambos ocupam a mesma posição.

---

## 12. Visualização das tarefas

Todos os membros podem visualizar todas as tarefas da casa.

Porém:

- membros podem alterar apenas tarefas atribuídas a eles;
- administrador pode alterar qualquer tarefa.

### 12.1 Filtros do administrador

O administrador pode filtrar por:

- status;
- responsável;
- prioridade;
- categoria.

---

## 13. Calendário

### Administrador

Pode visualizar todas as tarefas em calendário com visões:

- diária;
- semanal;
- mensal.

### Membro

Visualiza apenas suas próprias tarefas no calendário.

O calendário deve mostrar tarefas:

- com prazo;
- recorrentes.

---

## 14. Painel do administrador

O dashboard do administrador deve apresentar pelo menos:

- quantidade de tarefas pendentes;
- quantidade de tarefas atrasadas;
- quantidade aguardando aprovação;
- lista das tarefas que exigem aprovação;
- próximas tarefas com prazo.

Gráficos avançados e indicadores de desempenho ficam fora do MVP.

---

## 15. Histórico

O administrador pode consultar histórico completo contendo:

- tarefas concluídas;
- tarefas rejeitadas;
- tarefas atrasadas;
- responsáveis;
- datas de conclusão e aprovação;
- pontos concedidos;
- comentários de rejeição;
- alterações relevantes.

### Regra crítica adicionada

Tarefas concluídas não devem ser apagadas fisicamente pelo sistema.

Quando necessário, ficam registradas no histórico.

**Justificativa:** histórico e ranking dependem desses registros.

---

## 16. Notificações

O MVP deve gerar notificações quando:

- uma tarefa for atribuída ao membro;
- o prazo estiver próximo.

### Regra sugerida para prazo próximo

Considerar “próximo do prazo” como **24 horas antes**.

Para tarefas com prazo inferior a 24 horas após a criação, enviar apenas a notificação de atribuição.

### Escopo técnico sugerido

No MVP, as notificações podem ser internas na própria aplicação.

E-mail, push notification e WhatsApp ficam para versões futuras.

**Justificativa:** reduz dependências externas e mantém o foco no fluxo principal.

---

## 17. Telas mínimas

### Públicas

1. Login
2. Cadastro por convite
3. Recuperação de senha

### Administrador

4. Dashboard
5. Lista de tarefas
6. Criar/editar tarefa
7. Detalhes da tarefa
8. Aprovações pendentes
9. Calendário
10. Membros da casa
11. Categorias
12. Ranking
13. Histórico

### Membro

14. Minhas tarefas
15. Detalhes da tarefa
16. Enviar conclusão
17. Solicitar troca
18. Meu calendário
19. Ranking
20. Notificações

---

## 18. Entidades principais

Uma estrutura de dados mínima pode conter:

### User

- id
- name
- email
- password/auth_provider
- role
- created_at

### Household

- id
- name
- admin_id

### HouseholdMember

- household_id
- user_id
- joined_at
- active

### Task

- id
- household_id
- title
- description
- category_id
- priority
- assigned_user_id
- due_at
- recurrence_type
- recurrence_config
- suggested_points
- points
- status
- created_at
- updated_at

### TaskCompletion

- id
- task_id
- submitted_by
- submitted_at
- comment
- attachment
- approval_status
- reviewed_by
- reviewed_at
- rejection_comment
- awarded_points

### Category

- id
- household_id
- name
- is_default

### Comment

- id
- task_id
- user_id
- content
- created_at

### SwapRequest

- id
- task_id
- requested_by
- justification
- status
- reviewed_by
- reviewed_at

### Notification

- id
- user_id
- type
- message
- read
- created_at

### TaskHistory

- id
- task_id
- changed_by
- event_type
- previous_value
- new_value
- created_at

---

## 19. Regras de permissão resumidas

| Ação | Administrador | Membro responsável | Outro membro |
|---|:---:|:---:|:---:|
| Visualizar tarefa | ✓ | ✓ | ✓ |
| Criar tarefa | ✓ | ✗ | ✗ |
| Editar tarefa | ✓ | Limitado | ✗ |
| Excluir/cancelar tarefa | ✓ | ✗ | ✗ |
| Reatribuir tarefa | ✓ | ✗ | ✗ |
| Marcar como concluída | ✓ | ✓ | ✗ |
| Aprovar conclusão | ✓ | ✗ | ✗ |
| Rejeitar conclusão | ✓ | ✗ | ✗ |
| Comentar | ✓ | ✓ | ✗ |
| Solicitar troca | ✗ | ✓ | ✗ |
| Ver ranking | ✓ | ✓ | ✓ |

---

## 20. Fora do escopo do MVP

Para manter o trabalho controlável, ficam explicitamente fora da primeira versão:

- múltiplas casas por usuário;
- membros participando de várias casas;
- troca direta de tarefas entre membros;
- chat privado;
- recompensas por pontos;
- badges/conquistas;
- inteligência artificial para distribuição de tarefas;
- distribuição automática;
- geolocalização;
- integração com calendários externos;
- notificações por WhatsApp/SMS;
- analytics avançado;
- gráficos de produtividade;
- múltiplos anexos por conclusão;
- dependências entre tarefas;
- subtarefas;
- marketplace de recompensas;
- pagamentos.

---

## 21. Critérios de sucesso do MVP

O MVP pode ser considerado funcional quando for possível executar integralmente este cenário:

1. Administrador cria uma casa.
2. Convida um membro por e-mail.
3. Membro cria sua conta e entra na casa.
4. Administrador cria uma tarefa e atribui ao membro.
5. Define prioridade, categoria, pontos e prazo.
6. Membro recebe a tarefa.
7. Membro marca a tarefa como concluída e opcionalmente envia foto/comentário.
8. Administrador recebe a conclusão para validação.
9. Administrador aprova ou rejeita.
10. Se aprovada, os pontos entram no ranking.
11. Se rejeitada, a tarefa volta para execução com justificativa registrada.
12. Administrador consegue consultar o histórico.
13. Tarefas recorrentes geram novas ocorrências corretamente.
14. Calendário e notificações refletem os prazos relevantes.

---

## 22. Prioridade de implementação

### P0 — Fluxo essencial

- autenticação;
- casa e membros;
- convite;
- CRUD de tarefas;
- atribuição;
- status;
- conclusão;
- aprovação/rejeição;
- histórico básico.

### P1 — Organização

- categorias;
- prioridades;
- prazos;
- recorrência;
- filtros;
- calendário.

### P2 — Engajamento

- pontos;
- ranking;
- comentários;
- foto de evidência;
- solicitações de troca;
- notificações internas.

---

## 23. Resumo do produto

O produto é uma aplicação de gestão doméstica centralizada no administrador. O administrador organiza e distribui tarefas, enquanto os membros executam e submetem suas conclusões para validação.

A principal diferença em relação a uma lista de tarefas comum é a combinação de:

- responsabilidade individual;
- validação da execução;
- histórico auditável;
- tarefas recorrentes;
- calendário;
- pontuação e ranking.

Essa combinação é suficiente para produzir um MVP demonstrável sem introduzir complexidades desnecessárias como múltiplas casas, distribuição inteligente, recompensas ou integrações externas.
