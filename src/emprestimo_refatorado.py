import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from abc import ABC, abstractmethod

# ==========================================
# INTERFACES (Contratos)
# ==========================================
class IRepositorio(ABC):
    @abstractmethod
    def buscar(self, identificador: str) -> dict:
        pass
    
    @abstractmethod
    def salvar(self, entidade: dict) -> int:
        pass

class IServicoNotificacao(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, assunto: str, mensagem: str):
        pass

class IServicoRelatorio(ABC):
    @abstractmethod
    def gerar_comprovante(self, dados: dict):
        pass

# ==========================================
# REPOSITÓRIOS SQLITE (Infraestrutura)
# ==========================================
def dict_factory(cursor, row):
    """Converte as tuplas do SQLite em dicionários puros."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class RepositorioLivroSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path

    def buscar(self, isbn: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM livros WHERE isbn = ?", (isbn,)).fetchone()
            
    def salvar(self, entidade: dict) -> int:
        pass 
        
    def atualizar_estoque(self, isbn, decremento=1):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE livros SET exemplares_disponiveis = exemplares_disponiveis - ? WHERE isbn = ?", (decremento, isbn))
            conn.commit()

class RepositorioLeitorSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path

    def buscar(self, cpf: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM leitores WHERE cpf = ?", (cpf,)).fetchone()
            
    def salvar(self, entidade: dict) -> int:
        pass

class RepositorioEmprestimoSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, emp_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM emprestimos WHERE id = ?", (emp_id,)).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emprestimos (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                VALUES (?, ?, ?, ?)
            """, (entidade['livro_isbn'], entidade['leitor_cpf'], entidade['data_emprestimo'], entidade['data_devolucao_prevista']))
            conn.commit()
            return cursor.lastrowid
            
    def registrar_devolucao(self, emp_id: int, data_devolucao: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE emprestimos SET data_devolucao = ? WHERE id = ?", (data_devolucao, emp_id))
            conn.commit()

class RepositorioReservaSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, livro_isbn: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM reservas WHERE livro_isbn = ? ORDER BY id ASC LIMIT 1", (livro_isbn,)).fetchone()

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva)
                VALUES (?, ?, ?)
            """, (entidade['livro_isbn'], entidade['leitor_cpf'], entidade['data_reserva']))
            conn.commit()
            return 1
            
    def remover(self, reserva_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
            conn.commit()

class RepositorioMultaSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, id: str) -> dict:
        pass

    def salvar(self, entidade: dict) -> int:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO multas (emprestimo_id, valor) VALUES (?, ?)", (entidade['emprestimo_id'], entidade['valor']))
            conn.commit()
            return 1

# ==========================================
# SERVIÇOS REAIS (E-mail e PDF)
# ==========================================
class ServicoEmail(IServicoNotificacao):
    def enviar(self, destinatario: str, assunto: str, mensagem: str):
        try:
            msg = MIMEText(mensagem)
            msg['Subject'] = assunto
            msg['To'] = destinatario
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('biblioteca@exemplo.com', 'senha')
            server.send_message(msg)
            server.quit()
        except Exception:
            pass 

class ServicoPdfReportLab(IServicoRelatorio):
    def gerar_comprovante(self, dados: dict):
        try:
            c = canvas.Canvas(f"comprovante_{dados['emp_id']}.pdf")
            c.drawString(100, 750, f"Empréstimo #{dados['emp_id']}")
            c.drawString(100, 730, f"Livro: {dados['livro_titulo']}")
            c.drawString(100, 710, f"Leitor: {dados['leitor_nome']}")
            c.drawString(100, 690, f"Devolução: {dados['data_dev']}")
            c.save()
        except Exception:
            pass

# ==========================================
# DOMÍNIO (Classe Principal Refatorada)
# ==========================================
class GerenciadorEmprestimo:
    """Orquestra o processo mantendo regras de negócio limpas e isoladas."""
    
    def __init__(
        self, 
        db_path='biblioteca.db',
        repo_livro=None,
        repo_leitor=None,
        repo_emprestimo=None,
        repo_reserva=None,
        repo_multa=None,
        servico_notificacao=None,
        servico_relatorio=None
    ):
        self.db_path = db_path
        self.repo_livro = repo_livro or RepositorioLivroSQLite(db_path)
        self.repo_leitor = repo_leitor or RepositorioLeitorSQLite(db_path)
        self.repo_emprestimo = repo_emprestimo or RepositorioEmprestimoSQLite(db_path)
        self.repo_reserva = repo_reserva or RepositorioReservaSQLite(db_path)
        self.repo_multa = repo_multa or RepositorioMultaSQLite(db_path)
        self.servico_notificacao = servico_notificacao or ServicoEmail()
        self.servico_relatorio = servico_relatorio or ServicoPdfReportLab()
    
    def realizar_emprestimo(self, livro_isbn, leitor_cpf):
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
            self.repo_livro.atualizar_estoque(livro_isbn, decremento=1)
            
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

    def processar_devolucao(self, emprestimo_id):
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo or emprestimo.get('data_devolucao'):
            return False, "Empréstimo inválido ou já devolvido"

        data_atual = datetime.now()
        self.repo_emprestimo.registrar_devolucao(emprestimo_id, data_atual.strftime('%Y-%m-%d'))
        self.calcular_multa(emprestimo_id)

        reserva = self.repo_reserva.buscar(emprestimo['livro_isbn'])
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
            self.repo_livro.atualizar_estoque(emprestimo['livro_isbn'], decremento=-1)
            
        return True, "Devolução processada"

    def calcular_multa(self, emprestimo_id):
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo:
            return 0
            
        data_devolucao_prevista = datetime.strptime(emprestimo['data_devolucao_prevista'], '%Y-%m-%d')
        data_base = datetime.strptime(emprestimo['data_devolucao'], '%Y-%m-%d') if emprestimo.get('data_devolucao') else datetime.now()
        
        if data_base > data_devolucao_prevista:
            dias_atraso = (data_base - data_devolucao_prevista).days
            multa = dias_atraso * 2.0
            
            self.repo_multa.salvar({'emprestimo_id': emprestimo_id, 'valor': multa})
            
            leitor = self.repo_leitor.buscar(emprestimo['leitor_cpf'])
            if leitor:
                self.servico_notificacao.enviar(
                    destinatario=leitor['email'],
                    assunto='Multa por Atraso',
                    mensagem=f"Multa de R$ {multa:.2f} aplicada"
                )
            return multa
            
        return 0