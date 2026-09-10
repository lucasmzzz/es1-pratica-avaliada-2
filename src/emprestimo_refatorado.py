import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Any

# ==========================================
# INTERFACES (Contratos Abstratoss)
# ==========================================
class IRepositorio(ABC):
    @abstractmethod
    def buscar(self, id: Any) -> Optional[dict]:
        pass

    @abstractmethod
    def salvar(self, entidade: dict) -> int:
        pass

class IRepositorioEmprestimo(IRepositorio):
    @abstractmethod
    def registrar_devolucao(self, emp_id: int, data_devolucao: str) -> None:
        pass

class IRepositorioReserva(IRepositorio):
    @abstractmethod
    def buscar_primeira_da_fila(self, livro_isbn: str) -> Optional[dict]:
        pass

    @abstractmethod
    def remover(self, reserva_id: int) -> None:
        pass

class IRepositorioMulta(IRepositorio):
    pass

class IServicoNotificacao(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> None:
        pass

class IServicoRelatorio(ABC):
    @abstractmethod
    def gerar_comprovante(self, dados: dict) -> None:
        pass

class ICalculadoraMulta(ABC):
    @abstractmethod
    def calcular(self, data_prevista: datetime, data_real: datetime) -> float:
        pass

# ==========================================
# UTILITÁRIOS
# ==========================================
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# ==========================================
# REPOSITÓRIOS E SERVIÇOS REAIS
# ==========================================
class RepositorioLivro(IRepositorio):
    def __init__(self, db_path: str = 'biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM livros WHERE isbn = ?", (id,)).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE livros SET exemplares_disponiveis = ? WHERE isbn = ?",
                (entidade['exemplares_disponiveis'], entidade['isbn'])
            )
            conn.commit()
            return 1

class RepositorioLeitor(IRepositorio):
    def __init__(self, db_path: str = 'biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM leitores WHERE cpf = ?", (id,)).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO leitores (cpf, nome, email, telefone)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cpf) DO UPDATE SET
                    nome = excluded.nome,
                    email = excluded.email,
                    telefone = excluded.telefone
            """, (entidade['cpf'], entidade['nome'], entidade['email'], entidade.get('telefone')))
            conn.commit()
            return 1

class RepositorioEmprestimo(IRepositorioEmprestimo):
    def __init__(self, db_path: str = 'biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id: int) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM emprestimos WHERE id = ?", (id,)).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emprestimos (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                VALUES (?, ?, ?, ?)
            """, (
                entidade['livro_isbn'],
                entidade['leitor_cpf'],
                entidade['data_emprestimo'],
                entidade['data_devolucao_prevista']
            ))
            conn.commit()
            return cursor.lastrowid

    def registrar_devolucao(self, emp_id: int, data_devolucao: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE emprestimos SET data_devolucao = ? WHERE id = ?",
                (data_devolucao, emp_id)
            )
            conn.commit()

class RepositorioReserva(IRepositorioReserva):
    def __init__(self, db_path: str = 'biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id: str) -> Optional[dict]:
        return self.buscar_primeira_da_fila(id)

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva)
                VALUES (?, ?, ?)
            """, (entidade['livro_isbn'], entidade['leitor_cpf'], entidade['data_reserva']))
            conn.commit()
            return cursor.lastrowid

    def buscar_primeira_da_fila(self, livro_isbn: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute(
                "SELECT * FROM reservas WHERE livro_isbn = ? ORDER BY id ASC LIMIT 1",
                (livro_isbn,)
            ).fetchone()

    def remover(self, reserva_id: int) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
            conn.commit()

class RepositorioMulta(IRepositorioMulta):
    def __init__(self, db_path: str = 'biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute(
                "SELECT * FROM multas WHERE emprestimo_id = ?", (id,)
            ).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO multas (emprestimo_id, valor) VALUES (?, ?)",
                (entidade['emprestimo_id'], entidade['valor'])
            )
            conn.commit()
            return 1

class ServicoNotificacao(IServicoNotificacao):
    def enviar(self, destinatario: str, assunto: str, mensagem: str) -> None:
        try:
            msg = MIMEText(mensagem)
            msg['Subject'] = assunto
            msg['To'] = destinatario
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=3)
            server.starttls()
            server.login('biblioteca@exemplo.com', 'senha')
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"[Aviso de Envio de E-mail]: {e}")

class ServicoRelatorio(IServicoRelatorio):
    def gerar_comprovante(self, dados: dict) -> None:
        try:
            c = canvas.Canvas(f"comprovante_{dados['emp_id']}.pdf")
            c.drawString(100, 750, f"Empréstimo #{dados['emp_id']}")
            c.drawString(100, 730, f"Livro: {dados['livro_titulo']}")
            c.drawString(100, 710, f"Leitor: {dados['leitor_nome']}")
            c.drawString(100, 690, f"Devolução: {dados['data_dev']}")
            c.save()
        except Exception as e:
            print(f"[Aviso de Geração de PDF]: {e}")

class CalculadoraMulta(ICalculadoraMulta):
    TAXA_DIARIA = 2.0

    def calcular(self, data_prevista: datetime, data_real: datetime) -> float:
        if data_real > data_prevista:
            return (data_real - data_prevista).days * self.TAXA_DIARIA
        return 0.0

# ==========================================
# DOMÍNIO
# ==========================================
class GerenciadorEmprestimo:
    def __init__(
        self,
        repo_livro: IRepositorio,
        repo_leitor: IRepositorio,
        repo_emprestimo: IRepositorioEmprestimo,
        servico_notificacao: IServicoNotificacao,
        servico_relatorio: IServicoRelatorio,
        calculadora_multa: ICalculadoraMulta,
        repo_reserva: Optional[IRepositorioReserva] = None,
        repo_multa: Optional[IRepositorioMulta] = None,
    ):
        self.repo_livro = repo_livro
        self.repo_leitor = repo_leitor
        self.repo_emprestimo = repo_emprestimo
        self.servico_notificacao = servico_notificacao
        self.servico_relatorio = servico_relatorio
        self.calculadora_multa = calculadora_multa
        self.repo_reserva = repo_reserva if repo_reserva is not None else RepositorioReserva()
        self.repo_multa = repo_multa if repo_multa is not None else RepositorioMulta()

    def realizar_emprestimo(self, livro_isbn: str, leitor_cpf: str) -> Tuple[bool, str]:
        livro = self.repo_livro.buscar(livro_isbn)
        if not livro:
            return False, "Livro não encontrado"

        leitor = self.repo_leitor.buscar(leitor_cpf)
        if not leitor:
            return False, "Leitor não encontrado"

        if livro['exemplares_disponiveis'] > 0:
            data_atual = datetime.now()
            entidade_emp = {
                'livro_isbn': livro_isbn,
                'leitor_cpf': leitor_cpf,
                'data_emprestimo': data_atual.strftime('%Y-%m-%d'),
                'data_devolucao_prevista': (data_atual + timedelta(days=14)).strftime('%Y-%m-%d')
            }

            emp_id = self.repo_emprestimo.salvar(entidade_emp)
            livro['exemplares_disponiveis'] -= 1
            self.repo_livro.salvar(livro)

            self.servico_notificacao.enviar(
                destinatario=leitor['email'],
                assunto='Empréstimo Realizado',
                mensagem=f"Empréstimo realizado: {livro['titulo']}"
            )

            self.servico_relatorio.gerar_comprovante({
                'emp_id': emp_id,
                'livro_titulo': livro['titulo'],
                'leitor_nome': leitor['nome'],
                'data_dev': entidade_emp['data_devolucao_prevista']
            })
            return True, "Empréstimo realizado com sucesso"

        else:
            self.repo_reserva.salvar({
                'livro_isbn': livro_isbn,
                'leitor_cpf': leitor_cpf,
                'data_reserva': datetime.now().strftime('%Y-%m-%d')
            })
            return False, "Livro indisponível. Reserva criada."

    def processar_devolucao(self, emprestimo_id: int) -> Tuple[bool, str]:
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo or emprestimo.get('data_devolucao'):
            return False, "Empréstimo inválido ou já devolvido"

        data_atual_str = datetime.now().strftime('%Y-%m-%d')
        self.repo_emprestimo.registrar_devolucao(emprestimo_id, data_atual_str)

        emprestimo['data_devolucao'] = data_atual_str
        self.calcular_multa_com_data(emprestimo, data_atual_str)

        reserva = self.repo_reserva.buscar_primeira_da_fila(emprestimo['livro_isbn'])
        if reserva:
            leitor_reserva = self.repo_leitor.buscar(reserva['leitor_cpf'])
            if leitor_reserva:
                self.servico_notificacao.enviar(
                    destinatario=leitor_reserva['email'],
                    assunto='Seu livro chegou!',
                    mensagem='O livro que você reservou já está disponível.'
                )
            self.repo_reserva.remover(reserva['id'])
        else:
            livro = self.repo_livro.buscar(emprestimo['livro_isbn'])
            if livro:
                livro['exemplares_disponiveis'] += 1
                self.repo_livro.salvar(livro)

        return True, "Devolução processada"

    def calcular_multa(self, emprestimo_id: int) -> float:
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo:
            return 0.0
        data_real_str = emprestimo.get('data_devolucao') or datetime.now().strftime('%Y-%m-%d')
        return self.calcular_multa_com_data(emprestimo, data_real_str)

    def calcular_multa_com_data(self, emprestimo: dict, data_real_str: str) -> float:
        data_prevista = datetime.strptime(emprestimo['data_devolucao_prevista'], '%Y-%m-%d')
        data_real = datetime.strptime(data_real_str, '%Y-%m-%d')

        multa_valor = self.calculadora_multa.calcular(data_prevista, data_real)

        if multa_valor > 0.0:
            self.repo_multa.salvar({
                'emprestimo_id': emprestimo['id'],
                'valor': multa_valor
            })
            leitor = self.repo_leitor.buscar(emprestimo['leitor_cpf'])
            if leitor:
                self.servico_notificacao.enviar(
                    destinatario=leitor['email'],
                    assunto='Multa por Atraso',
                    mensagem=f"Multa de R$ {multa_valor:.2f} aplicada"
                )
        return multa_valor