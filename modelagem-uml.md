# Modelagem UML - BiblioTech

## A. Diagrama de Classes

```mermaid
classDiagram
    class Livro {
        -String isbn
        -String titulo
        -String autor
        -String categoria
        -int exemplares_disponiveis
        +cadastrarLivro()
        +verificarDisponibilidade() bool
    }
    
    class Leitor {
        -String cpf
        -String nome
        -String email
        -String telefone
        +cadastrarLeitor()
        +consultarHistorico()
    }
    
    class Emprestimo {
        -int id
        -Date data_emprestimo
        -Date data_devolucao_prevista
        -Date data_devolucao
        +registrarEmprestimo()
        +renovarEmprestimo()
    }
    
    class Reserva {
        -int id
        -Date data_reserva
        +criarReserva()
        +notificarLeitor()
    }
    
    class Multa {
        -int id
        -float valor
        -bool paga
        +calcularMulta()
        +quitarMulta()
    }
    
    class Bibliotecario {
        -String matricula
        -String nome
        +autorizarEmprestimo()
        +processarDevolucao()
    }

    Bibliotecario "1" --> "*" Emprestimo : gerencia
    Leitor "1" --> "*" Emprestimo : realiza
    Leitor "1" --> "*" Reserva : solicita
    Livro "1" --> "*" Reserva : possui
    Livro "1" --> "*" Emprestimo : possui (via isbn)
    Emprestimo "1" --> "0..1" Multa : gera
```

## B. Diagrama de Sequência: Realizar Empréstimo

```mermaid
sequenceDiagram
    actor B as Bibliotecário
    participant S as Sistema
    participant L as Leitor
    participant V as Livro
    participant E as Empréstimo
    
    B->>S: realizar_emprestimo(isbn, cpf)
    activate S
    
    S->>L: buscar(cpf)
    activate L
    L-->>S: leitor_dados (Verificação de cadastro e adimplência)
    deactivate L
    
    S->>V: buscar(isbn)
    activate V
    V-->>S: livro_dados (Verificação de disponibilidade)
    deactivate V
    
    alt Exemplares > 0 e Leitor Adimplente
        S->>E: salvar(entidade_emp)
        activate E
        E-->>S: emp_id
        deactivate E
        S->>V: salvar(livro_atualizado)
        S-->>B: True, "Empréstimo realizado com sucesso"
    else Indisponível ou Irregular
        S->>B: False, "Falha na validação ou Leitor inadimplente"
    end
    deactivate S
```

## C. Diagrama de Atividades: Devolução e Reservas

```mermaid
flowchart TD
    A([Iniciar Devolução]) --> B[Registrar data de devolução]
    B --> C{Entregue com atraso?}
    
    C -- Sim --> D[Calcular e Aplicar Multa]
    D --> E{Existem reservas pendentes?}
    
    C -- Não --> E
    
    E -- Sim --> F[Notificar primeiro leitor da fila]
    F --> G([Fim: Com multa, Com reserva])
    
    E -- Não --> H[Incrementar estoque do livro]
    H --> I{Houve aplicação de multa?}
    
    I -- Sim --> J([Fim: Com multa, Sem reserva])
    I -- Não --> K([Fim: Sem multa, Sem reserva])
```