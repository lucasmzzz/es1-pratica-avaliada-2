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
    def buscar(self, identificador):
        pass
    
    @abstractmethod
    def salvar(self, *args, **kwargs):
        pass

class IServicoNotificacao(ABC):
    @abstractmethod
    def enviar(self, destinatario, assunto, mensagem):
        pass

class IServicoRelatorio(ABC):
    @abstractmethod
    def gerar_comprovante(self, emp_id, livro_titulo, leitor_nome, data_dev):
        pass

# ==========================================
# REPOSITÓRIOS SQLITE (Infraestrutura)
# ==========================================
class RepositorioLivroSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path

    def buscar(self, isbn):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM livros WHERE isbn = ?", (isbn,)).fetchone()
            
    def salvar(self):
        pass 
        
    def atualizar_estoque(self, isbn, decremento=1):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE livros SET exemplares_disponiveis = exemplares_disponiveis - ? WHERE isbn = ?", (decremento, isbn))
            conn.commit()

class RepositorioLeitorSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path

    def buscar(self, cpf):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM leitores WHERE cpf = ?", (cpf,)).fetchone()
            
    def salvar(self):
        pass

class RepositorioEmprestimoSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, emp_id):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM emprestimos WHERE id = ?", (emp_id,)).fetchone()

    def salvar(self, livro_isbn, leitor_cpf, data_emp, data_dev):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emprestimos (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                VALUES (?, ?, ?, ?)
            """, (livro_isbn, leitor_cpf, data_emp, data_dev))
            conn.commit()
            return cursor.lastrowid

class RepositorioReservaSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, id):
        pass

    def salvar(self, livro_isbn, leitor_cpf, data_reserva):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva)
                VALUES (?, ?, ?)
            """, (livro_isbn, leitor_cpf, data_reserva))
            conn.commit()

class RepositorioMultaSQLite(IRepositorio):
    def __init__(self, db_path):
        self.db_path = db_path
        
    def buscar(self, id):
        pass

    def salvar(self, emprestimo_id, valor):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO multas (emprestimo_id, valor) VALUES (?, ?)", (emprestimo_id, valor))
            conn.commit()

# ==========================================
# SERVIÇOS REAIS (E-mail e PDF)
# ==========================================
class ServicoEmail(IServicoNotificacao):
    def enviar(self, destinatario, assunto, mensagem):
        try:
            msg = MIMEText(mensagem)
            msg['Subject'] = assunto
            msg['To'] = destinatario
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login('biblioteca@exemplo.com', 'senha')
            server.send_message(msg)
            server.quit()
        except:
            pass 

class ServicoPdfReportLab(IServicoRelatorio):
    def gerar_comprovante(self, emp_id, livro_titulo, leitor_nome, data_dev):
        try:
            c = canvas.Canvas(f'comprovante_{emp_id}.pdf')
            c.drawString(100, 750, f'Empréstimo #{emp_id}')
            c.drawString(100, 730, f'Livro: {livro_titulo}')
            c.drawString(100, 710, f'Leitor: {leitor_nome}')
            c.drawString(100, 690, f'Devolução: {data_dev}')
            c.save()
        except:
            pass

# ==========================================
# DOMÍNIO (Classe Principal Refatorada)
# ==========================================
class GerenciadorEmprestimo:
    """Orquestra o processo de empréstimo respeitando o SOLID."""
    
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
            
        exemplares_disponiveis = livro[4]
        
        if exemplares_disponiveis > 0:
            data_atual = datetime.now()
            data_emp = data_atual.strftime('%Y-%m-%d')
            data_dev = (data_atual + timedelta(days=14)).strftime('%Y-%m-%d')
            
            emp_id = self.repo_emprestimo.salvar(livro_isbn, leitor_cpf, data_emp, data_dev)
            self.repo_livro.atualizar_estoque(livro_isbn)
            
            self.servico_notificacao.enviar(
                destinatario=leitor[2], 
                assunto='Empréstimo Realizado', 
                mensagem=f"Empréstimo realizado: {livro[1]}"
            )
            
            self.servico_relatorio.gerar_comprovante(emp_id, livro[1], leitor[1], data_dev)
            return True, "Empréstimo realizado com sucesso"
            
        else:
            data_reserva = datetime.now().strftime('%Y-%m-%d')
            self.repo_reserva.salvar(livro_isbn, leitor_cpf, data_reserva)
            return False, "Livro indisponível. Reserva criada."

    def calcular_multa(self, emprestimo_id):
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo:
            return 0
            
        data_devolucao_prevista = datetime.strptime(emprestimo[4], '%Y-%m-%d')
        
        if datetime.now() > data_devolucao_prevista:
            dias_atraso = (datetime.now() - data_devolucao_prevista).days
            multa = dias_atraso * 2.0
            
            self.repo_multa.salvar(emprestimo_id, multa)
            
            leitor = self.repo_leitor.buscar(emprestimo[2])
            if leitor:
                self.servico_notificacao.enviar(
                    destinatario=leitor[2],
                    assunto='Multa por Atraso',
                    mensagem=f"Multa de R$ {multa:.2f} aplicada"
                )
            return multa
            
        return 0