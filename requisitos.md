# Engenharia de Requisitos - BiblioTech

## Requisitos Funcionais

| ID | Descrição | Prioridade |
|----|-----------|------------|
| RF01 | O sistema deve permitir o cadastro de livros com título, autor, ISBN, categoria e quantidade de exemplares[cite: 11]. | Alta |
| RF02 | O sistema deve permitir o cadastro de leitores com nome, CPF, e-mail e telefone[cite: 11]. | Alta |
| RF03 | O sistema deve registrar o empréstimo de livros vinculando o ISBN do livro ao CPF do leitor[cite: 11]. | Alta |
| RF04 | O sistema deve calcular automaticamente a data prevista de devolução no momento do empréstimo[cite: 11]. | Alta |
| RF05 | O sistema deve permitir que um leitor reserve um livro caso todos os exemplares estejam emprestados[cite: 11]. | Média |
| RF06 | O sistema deve registrar a devolução de livros emprestados[cite: 11]. | Alta |
| RF07 | O sistema deve notificar por e-mail o primeiro leitor da fila de reservas quando o livro for devolvido[cite: 11]. | Média |
| RF08 | O sistema deve permitir a renovação de empréstimos ativos[cite: 11]. | Baixa |
| RF09 | O sistema deve impedir a renovação de um empréstimo caso exista uma reserva ativa para o livro[cite: 11]. | Alta |
| RF10 | O sistema deve calcular e aplicar multas financeiras para devoluções realizadas após o prazo previsto[cite: 11]. | Alta |

## Requisitos Não-Funcionais

| ID | Categoria | Descrição | Métrica |
|----|-----------|-----------|---------|
| RNF01 | Desempenho | O sistema deve processar o registro de empréstimos rapidamente. | Tempo de resposta < 2 segundos. |
| RNF02 | Confiabilidade | O banco de dados SQLite deve manter a integridade transacional. | Zero perda de dados em falhas (ACID). |
| RNF03 | Notificação | O envio de e-mails não deve travar o fluxo principal da aplicação. | Processamento assíncrono ou timeout < 3s. |
| RNF04 | Usabilidade | A interface do bibliotecário deve requerer mínimo de cliques para o fluxo principal. | Máximo de 3 interações para emprestar. |
| RNF05 | Manutenibilidade| O código fonte deve seguir os padrões de engenharia e boas práticas de design. | 100% de conformidade com PEP 8 e princípios SOLID. |

## Regras de Negócio

| ID | Descrição |
|----|-----------|
| RN01 | O prazo padrão para empréstimos e devoluções é fixado em exatos 14 dias[cite: 11]. |
| RN02 | A multa por atraso na devolução é calculada no valor fixo de R$ 2,00 por dia de atraso[cite: 11]. |
| RN03 | Uma reserva só pode ser efetivada se a quantidade de exemplares disponíveis do livro for igual a zero[cite: 11]. |
| RN04 | A renovação de um empréstimo é estritamente proibida caso exista qualquer reserva pendente para a obra[cite: 11]. |
| RN05 | A fila de reservas deve respeitar a ordem cronológica (FIFO), notificando sempre o leitor mais antigo da fila[cite: 11]. |

---

## User Stories (Critério INVEST)

**US01: Cadastro de Acervo**
Como Bibliotecário
Quero cadastrar novos livros no sistema
Para manter o acervo atualizado e disponível para consulta

Critérios de Aceitação:
- [ ] O sistema deve validar se o ISBN é único.
- [ ] Todos os campos obrigatórios (título, autor, ISBN) devem ser preenchidos.
Story Points: 3

**US02: Cadastro de Leitores**
Como Leitor
Quero me cadastrar no sistema da biblioteca
Para poder realizar empréstimos e reservas de livros

Critérios de Aceitação:
- [ ] O sistema deve validar a unicidade e o formato do CPF.
- [ ] O e-mail fornecido deve ter um formato válido.
Story Points: 2

**US03: Registro de Empréstimo**
Como Bibliotecário
Quero registrar o empréstimo de um livro para um leitor
Para controlar a saída do acervo e os prazos de devolução

Critérios de Aceitação:
- [ ] A quantidade de exemplares disponíveis deve diminuir em 1.
- [ ] A data de devolução deve ser cravada em 14 dias a partir de hoje.
Story Points: 5

**US04: Reserva de Obra Indisponível**
Como Leitor
Quero reservar um livro que não possui exemplares disponíveis
Para garantir que serei o próximo a lê-lo quando for devolvido

Critérios de Aceitação:
- [ ] O botão de reserva só deve estar habilitado se exemplares_disponiveis == 0.
- [ ] A reserva deve ser registrada com a data e hora exatas da solicitação.
Story Points: 3

**US05: Processamento de Devolução**
Como Bibliotecário
Quero registrar a devolução de um livro
Para liberar o exemplar no acervo ou para o próximo da fila

Critérios de Aceitação:
- [ ] Se houver multa, o sistema deve calcular e exibir o valor total.
- [ ] Se houver reserva, o sistema deve disparar notificação por e-mail para o primeiro da fila.
Story Points: 8

**US06: Renovação de Empréstimo**
Como Leitor
Quero renovar o empréstimo do meu livro
Para estender meu prazo de leitura por mais 14 dias

Critérios de Aceitação:
- [ ] A renovação deve ser bloqueada se houver reservas pendentes para o livro.
- [ ] A nova data de devolução deve ser acrescida em 14 dias.
Story Points: 5