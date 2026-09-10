import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from abc import ABC, abstractmethod

# ==========================================
# INTERFACES
# ==========================================
class IRepositorio(ABC):
    @abstractmethod
    def buscar(self, id):
        pass
    
    @abstractmethod
    def salvar(self, entidade):
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
# REPOSITÓRIOS E SERVIÇOS 
# ==========================================
class RepositorioLivro(IRepositorio):
    """Responsável apenas por operações com livros no BD"""
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM livros WHERE isbn = ?", (id,)).fetchone()
            
    def salvar(self, entidade):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE livros SET exemplares_disponiveis = ? WHERE isbn = ?", 
                         (entidade['exemplares_disponiveis'], entidade['isbn']))
            conn.commit()
            return 1

class RepositorioLeitor(IRepositorio):
    """Responsável apenas por operações com leitores no BD"""
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path

    def buscar(self, id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM leitores WHERE cpf = ?", (id,)).fetchone()
            
    def salvar(self, entidade):
        pass

class RepositorioEmprestimo(IRepositorio):
    """Responsável apenas por operações com empréstimos no BD"""
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path
        
    def buscar(self, id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM emprestimos WHERE id = ?", (id,)).fetchone()

    def salvar(self, entidade):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emprestimos (livro_isbn, leitor_cpf, data_emprestimo, data_devolucao_prevista)
                VALUES (?, ?, ?, ?)
            """, (entidade['livro_isbn'], entidade['leitor_cpf'], entidade['data_emprestimo'], entidade['data_devolucao_prevista']))
            conn.commit()
            return cursor.lastrowid
            
    def registrar_devolucao(self, emp_id, data_devolucao):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE emprestimos SET data_devolucao = ? WHERE id = ?", (data_devolucao, emp_id))
            conn.commit()

class RepositorioReserva(IRepositorio):
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path
        
    def buscar(self, id): 
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = dict_factory
            return conn.execute("SELECT * FROM reservas WHERE livro_isbn = ? ORDER BY id ASC LIMIT 1", (id,)).fetchone()

    def salvar(self, entidade):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO reservas (livro_isbn, leitor_cpf, data_reserva)
                VALUES (?, ?, ?)
            """, (entidade['livro_isbn'], entidade['leitor_cpf'], entidade['data_reserva']))
            conn.commit()
            return 1
            
    def remover(self, reserva_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
            conn.commit()

class RepositorioMulta(IRepositorio):
    def __init__(self, db_path='biblioteca.db'):
        self.db_path = db_path
        
    def buscar(self, id):
        pass

    def salvar(self, entidade):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO multas (emprestimo_id, valor) VALUES (?, ?)", (entidade['emprestimo_id'], entidade['valor']))
            conn.commit()
            return 1

class ServicoNotificacao:
    """Responsável apenas por enviar notificações"""
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
        except Exception:
            pass 

class ServicoRelatorio:
    """Responsável apenas por gerar relatórios"""
    def gerar_comprovante(self, dados):
        try:
            c = canvas.Canvas(f"comprovante_{dados['emp_id']}.pdf")
            c.drawString(100, 750, f"Empréstimo #{dados['emp_id']}")
            c.drawString(100, 730, f"Livro: {dados['livro_titulo']}")
            c.drawString(100, 710, f"Leitor: {dados['leitor_nome']}")
            c.drawString(100, 690, f"Devolução: {dados['data_dev']}")
            c.save()
        except Exception:
            pass

class CalculadoraMulta:
    """Responsável apenas por calcular multas"""
    TAXA_DIARIA = 2.0
    
    def calcular(self, data_prevista: datetime, data_real: datetime) -> float:
        if data_real > data_prevista:
            dias_atraso = (data_real - data_prevista).days
            return dias_atraso * self.TAXA_DIARIA
        return 0.0

# ==========================================
# DOMÍNIO (Classe Principal Refatorada)
# ==========================================
class GerenciadorEmprestimo:
    """Orquestra o processo de empréstimo usando os serviços"""
    
    def __init__(
        self, 
        repo_livro: RepositorioLivro = None,
        repo_leitor: RepositorioLeitor = None,
        repo_emprestimo: RepositorioEmprestimo = None,
        servico_notificacao: ServicoNotificacao = None,
        servico_relatorio: ServicoRelatorio = None,
        calculadora_multa: CalculadoraMulta = None,
        db_path: str = 'biblioteca.db'
    ):
        self.db_path = db_path
        self.repo_livro = repo_livro or RepositorioLivro(db_path)
        self.repo_leitor = repo_leitor or RepositorioLeitor(db_path)
        self.repo_emprestimo = repo_emprestimo or RepositorioEmprestimo(db_path)
        self.repo_reserva = RepositorioReserva(db_path)
        self.repo_multa = RepositorioMulta(db_path)
        self.servico_notificacao = servico_notificacao or ServicoNotificacao()
        self.servico_relatorio = servico_relatorio or ServicoRelatorio()
        self.calculadora_multa = calculadora_multa or CalculadoraMulta()
    
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
            livro = self.repo_livro.buscar(emprestimo['livro_isbn'])
            if livro:
                livro['exemplares_disponiveis'] += 1
                self.repo_livro.salvar(livro)
            
        return True, "Devolução processada"

    def calcular_multa(self, emprestimo_id):
        emprestimo = self.repo_emprestimo.buscar(emprestimo_id)
        if not emprestimo:
            return 0
            
        data_prevista = datetime.strptime(emprestimo['data_devolucao_prevista'], '%Y-%m-%d')
        data_base = datetime.strptime(emprestimo['data_devolucao'], '%Y-%m-%d') if emprestimo.get('data_devolucao') else datetime.now()
        
        multa_valor = self.calculadora_multa.calcular(data_prevista, data_base)
        
        if multa_valor > 0:
            self.repo_multa.salvar({'emprestimo_id': emprestimo_id, 'valor': multa_valor})
            
            leitor = self.repo_leitor.buscar(emprestimo['leitor_cpf'])
            if leitor:
                self.servico_notificacao.enviar(
                    destinatario=leitor['email'],
                    assunto='Multa por Atraso',
                    mensagem=f"Multa de R$ {multa_valor:.2f} aplicada"
                )
        return multa_valor