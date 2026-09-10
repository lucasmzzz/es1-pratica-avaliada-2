from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Tuple, Optional

class IRepositorio(ABC):
    @abstractmethod
    def buscar(self, id: str) -> Optional[dict]:
        pass
    
    @abstractmethod
    def salvar(self, entidade: dict) -> int:
        pass

class RepositorioLivro(IRepositorio):
    def buscar(self, isbn: str) -> Optional[dict]:
        pass
        
    def salvar(self, entidade: dict) -> int:
        pass

class RepositorioLeitor(IRepositorio):
    def buscar(self, cpf: str) -> Optional[dict]:
        pass
        
    def salvar(self, entidade: dict) -> int:
        pass

class RepositorioEmprestimo(IRepositorio):
    def buscar(self, id: str) -> Optional[dict]:
        pass
        
    def salvar(self, entidade: dict) -> int:
        return 1 

class RepositorioReserva(IRepositorio):
    def buscar(self, id: str) -> Optional[dict]:
        pass
        
    def salvar(self, entidade: dict) -> int:
        return 1

class ServicoNotificacao(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, mensagem: str):
        pass

class EmailNotificacao(ServicoNotificacao):
    def enviar(self, destinatario: str, assunto: str, mensagem: str):
        pass

class ServicoRelatorio(ABC):
    @abstractmethod
    def gerar_comprovante(self, dados: dict):
        pass

class PdfRelatorio(ServicoRelatorio):
    def gerar_comprovante(self, dados: dict):
        pass

class CalculadoraMulta:
    TAXA_DIARIA = 2.0
    
    def calcular(self, data_prevista: datetime, data_real: datetime) -> float:
        if data_real > data_prevista:
            dias_atraso = (data_real - data_prevista).days
            return dias_atraso * self.TAXA_DIARIA
        return 0.0

class GerenciadorEmprestimo:
    """Orquestra o processo de empréstimo usando abstrações (DIP)."""
    
    def __init__(
        self, 
        repo_livro: RepositorioLivro,
        repo_leitor: RepositorioLeitor,
        repo_emprestimo: RepositorioEmprestimo,
        repo_reserva: RepositorioReserva,
        servico_notificacao: ServicoNotificacao,
        servico_relatorio: ServicoRelatorio,
        calculadora_multa: CalculadoraMulta
    ):
        self.repo_livro = repo_livro
        self.repo_leitor = repo_leitor
        self.repo_emprestimo = repo_emprestimo
        self.repo_reserva = repo_reserva
        self.servico_notificacao = servico_notificacao
        self.servico_relatorio = servico_relatorio
        self.calculadora_multa = calculadora_multa
    
    def realizar_emprestimo(self, livro_isbn: str, leitor_cpf: str) -> Tuple[bool, str]:
        livro = self.repo_livro.buscar(livro_isbn)
        if not livro:
            return False, "Livro não encontrado"
            
        leitor = self.repo_leitor.buscar(leitor_cpf)
        if not leitor:
            return False, "Leitor não encontrado"
            
        if livro.get('exemplares_disponiveis', 0) <= 0:
            reserva = {
                'livro_isbn': livro_isbn,
                'leitor_cpf': leitor_cpf,
                'data_reserva': datetime.now().strftime('%Y-%m-%d')
            }
            self.repo_reserva.salvar(reserva)
            return False, "Livro indisponível. Reserva criada."
            
        data_atual = datetime.now()
        emprestimo = {
            'livro_isbn': livro_isbn,
            'leitor_cpf': leitor_cpf,
            'data_emprestimo': data_atual.strftime('%Y-%m-%d'),
            'data_devolucao_prevista': (data_atual + timedelta(days=14)).strftime('%Y-%m-%d')
        }
        
        emprestimo_id = self.repo_emprestimo.salvar(emprestimo)
        
        livro['exemplares_disponiveis'] -= 1
        self.repo_livro.salvar(livro)
        
        self.servico_notificacao.enviar(
            destinatario=leitor.get('email'),
            assunto="Empréstimo Realizado",
            mensagem=f"Empréstimo realizado: {livro.get('titulo')}"
        )
        
        self.servico_relatorio.gerar_comprovante({
            'id': emprestimo_id,
            'livro': livro.get('titulo'),
            'leitor': leitor.get('nome'),
            'devolucao': emprestimo['data_devolucao_prevista']
        })
        
        return True, "Empréstimo realizado com sucesso"