from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'clinica_vida_secret_key')

def get_db_connection():
    database_path = os.environ.get('CLINICA_DB_PATH', os.path.join(app.root_path, 'clinica.db'))
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Criar Tabela usuario
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    ''')
    
    # Criar Tabela medico
    c.execute('''
        CREATE TABLE IF NOT EXISTS medico (
            id_medico INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            crm TEXT NOT NULL UNIQUE,
            especialidade TEXT NOT NULL,
            telefone TEXT NOT NULL
        )
    ''')
    
    # Inserir dados de demonstração somente no esquema legado do app.py.
    user_columns = {row['name'] for row in c.execute('PRAGMA table_info(usuario)').fetchall()}
    c.execute('SELECT COUNT(*) FROM usuario')
    if c.fetchone()[0] == 0 and {'nome', 'email', 'senha'}.issubset(user_columns):
        c.execute("INSERT INTO usuario (nome, email, senha) VALUES ('Ana Souza', 'ana@clinica.com', '123456')")
        c.execute("INSERT INTO usuario (nome, email, senha) VALUES ('Carlos Lima', 'carlos@clinica.com', '654321')")

    doctor_columns = {row['name'] for row in c.execute('PRAGMA table_info(medico)').fetchall()}
    c.execute('SELECT COUNT(*) FROM medico')
    if c.fetchone()[0] == 0 and {'nome', 'crm', 'especialidade', 'telefone'}.issubset(doctor_columns):
        c.execute("INSERT INTO medico (nome, crm, especialidade, telefone) VALUES ('Dr. Roberto Alves', 'CRM/SP 123456', 'Cardiologia', '(11) 98765-4321')")
        c.execute("INSERT INTO medico (nome, crm, especialidade, telefone) VALUES ('Dra. Juliana Mendes', 'CRM/SP 654321', 'Dermatologia', '(11) 91234-5678')")

    conn.commit()
    conn.close()

init_db()

# BASE CSS INLINE DE EMERGENCIA CASO O CSS QUEBRE
CSS_STYLE = """
<style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f6f9; }
    .navbar { background-color: #2c3e50; display: flex; justify-content: space-between; align-items: center; padding: 0 20px; }
    .navbar a { color: white; padding: 16px 20px; text-decoration: none; font-weight: bold; display: inline-block; }
    .navbar a:hover, .navbar a.active { background-color: #34495e; }
    .btn-sair { background-color: #e74c3c !important; border-radius: 4px; padding: 8px 16px !important; }
    .container { max-width: 900px; margin: 30px auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    .form-group { margin-bottom: 15px; }
    .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
    .form-group input { width: 100%; padding: 9px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
    button { padding: 10px 20px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 15px; }
    button:hover { background: #219150; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    table, th, td { border: 1px solid #ddd; }
    th, td { padding: 10px; text-align: left; }
    th { background-color: #f2f2f2; }
    .btn-edit { background-color: #f39c12; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 13px; margin-right: 5px; }
    .btn-del { background-color: #e74c3c; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 13px; }
    .alert { background-color: #d4edda; color: #155724; padding: 12px; margin-bottom: 20px; border-radius: 4px; }
</style>
"""

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect('/painel')
    
    # Tenta renderizar arquivo HTML; se falhar, usa string inline
    if os.path.exists('templates/login.html'):
        return render_template('login.html')
    
    return render_template_string(CSS_STYLE + """
    <div style="max-width:350px; margin:80px auto; background:white; padding:30px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); text-align:center;">
        <h2>Clínica Vida - Login</h2>
        <form action="/login" method="POST">
            <div class="form-group"><label>E-mail:</label><input type="email" name="email" value="ana@clinica.com" required></div>
            <div class="form-group"><label>Senha:</label><input type="password" name="senha" value="123456" required></div>
            <button type="submit" style="width:100%;">Acessar</button>
        </form>
    </div>
    """)

@app.route('/painel')
def painel():
    if os.path.exists('templates/painel.html'):
        return render_template('painel.html')
    
    return render_template_string(CSS_STYLE + """
    <nav class="navbar">
        <div>
            <a href="/painel" class="active">Início</a>
            <a href="/usuarios">Usuários</a>
            <a href="/medicos">Médicos</a>
            <a href="/agendamentos">Agendamentos</a>
        </div>
        <div><a href="/login" class="btn-sair">Sair</a></div>
    </nav>
    <div class="container" style="text-align:center; padding:50px 20px;">
        <h1>Bem-vindo ao Painel da Clínica Vida!</h1>
        <p>Clique em <b>Usuários</b> ou <b>Médicos</b> no menu superior para navegar.</p>
    </div>
    """)

@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        try:
            conn.execute('INSERT INTO usuario (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha))
            conn.commit()
            flash('Usuário cadastrado!')
        except Exception:
            flash('Erro ao cadastrar usuário.')

    lista = conn.execute('SELECT * FROM usuario').fetchall()
    conn.close()

    if os.path.exists('templates/usuarios.html'):
        return render_template('usuarios.html', usuarios=lista, usuario_edicao=None)

    return render_template_string(CSS_STYLE + """
    <nav class="navbar">
        <div>
            <a href="/painel">Início</a>
            <a href="/usuarios" class="active">Usuários</a>
            <a href="/medicos">Médicos</a>
            <a href="/agendamentos">Agendamentos</a>
        </div>
        <div><a href="/login" class="btn-sair">Sair</a></div>
    </nav>
    <div class="container">
        <h2>Clínica Vida - Gerenciamento de Usuários (Questão 6)</h2>
        {% with messages = get_flashed_messages() %}
          {% if messages %}{% for m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}
        <h3>Cadastrar Novo Usuário</h3>
        <form action="/usuarios" method="POST">
            <div class="form-group"><label>Nome:</label><input type="text" name="nome" placeholder="Digite o Nome" required></div>
            <div class="form-group"><label>E-mail:</label><input type="email" name="email" placeholder="Digite o E-mail" required></div>
            <div class="form-group"><label>Senha:</label><input type="password" name="senha" placeholder="Digite a Senha" required></div>
            <button type="submit">Cadastrar</button>
        </form>
        <hr style="margin: 30px 0;">
        <h3>Lista de Usuários Cadastrados</h3>
        <table>
            <thead><tr><th>ID</th><th>Nome</th><th>E-mail</th><th>Ações</th></tr></thead>
            <tbody>
                {% for u in usuarios %}
                <tr>
                    <td>{{ u['id_usuario'] }}</td>
                    <td>{{ u['nome'] }}</td>
                    <td>{{ u['email'] }}</td>
                    <td><a href="/usuarios/excluir/{{ u['id_usuario'] }}" class="btn-del">Excluir</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """, usuarios=lista)

@app.route('/usuarios/excluir/<int:id>')
def excluir_usuario(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM usuario WHERE id_usuario = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/usuarios')

@app.route('/medicos', methods=['GET', 'POST'])
def medicos():
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        crm = request.form['crm']
        especialidade = request.form['especialidade']
        telefone = request.form['telefone']
        try:
            conn.execute('INSERT INTO medico (nome, crm, especialidade, telefone) VALUES (?, ?, ?, ?)', (nome, crm, especialidade, telefone))
            conn.commit()
            flash('Médico cadastrado com sucesso!')
        except Exception:
            flash('Erro: CRM já cadastrado.')

    lista = conn.execute('SELECT * FROM medico').fetchall()
    conn.close()

    if os.path.exists('templates/medicos.html'):
        return render_template('medicos.html', medicos=lista, medico_edicao=None)

    return render_template_string(CSS_STYLE + """
    <nav class="navbar">
        <div>
            <a href="/painel">Início</a>
            <a href="/usuarios">Usuários</a>
            <a href="/medicos" class="active">Médicos</a>
            <a href="/agendamentos">Agendamentos</a>
        </div>
        <div><a href="/login" class="btn-sair">Sair</a></div>
    </nav>
    <div class="container">
        <h2>Clínica Vida - Gerenciamento de Médicos (Questão 7)</h2>
        {% with messages = get_flashed_messages() %}
          {% if messages %}{% for m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}
        {% endwith %}
        <h3>Cadastrar Novo Médico</h3>
        <form action="/medicos" method="POST">
            <div class="form-group"><label>Nome do Médico:</label><input type="text" name="nome" placeholder="Ex: Dr. Roberto Alves" required></div>
            <div class="form-group"><label>CRM:</label><input type="text" name="crm" placeholder="Ex: CRM/SP 123456" required></div>
            <div class="form-group"><label>Especialidade:</label><input type="text" name="especialidade" placeholder="Ex: Cardiologia" required></div>
            <div class="form-group"><label>Telefone de Contato:</label><input type="text" name="telefone" placeholder="Ex: (11) 98765-4321" required></div>
            <button type="submit" style="background-color: #16a085;">Cadastrar Médico</button>
        </form>
        <hr style="margin: 30px 0;">
        <h3>Corpo Médico Cadastrado</h3>
        <table>
            <thead><tr><th>ID</th><th>Nome</th><th>CRM</th><th>Especialidade</th><th>Telefone</th><th>Ações</th></tr></thead>
            <tbody>
                {% for m in medicos %}
                <tr>
                    <td>{{ m['id_medico'] }}</td>
                    <td>{{ m['nome'] }}</td>
                    <td>{{ m['crm'] }}</td>
                    <td>{{ m['especialidade'] }}</td>
                    <td>{{ m['telefone'] }}</td>
                    <td><a href="/medicos/excluir/{{ m['id_medico'] }}" class="btn-del">Excluir</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    """, medicos=lista)

@app.route('/medicos/excluir/<int:id>')
def excluir_medico(id):
    conn = get_db_connection()
    try:
        cursor = conn.execute('DELETE FROM medico WHERE id_medico = ?', (id,))
        conn.commit()
        if cursor.rowcount:
            flash('Médico excluído.')
        else:
            flash('Médico não encontrado.')
    except sqlite3.IntegrityError:
        conn.rollback()
        flash('Não é possível excluir este médico: há agendamentos vinculados.')
    finally:
        conn.close()
    return redirect('/medicos')

from agendamentos import registrar_rotas_agendamentos

registrar_rotas_agendamentos(app, get_db_connection)


@app.get('/manus-routes.json')
def manifest_rotas():
    return jsonify({'routes': [
        {'path': '/', 'title': 'Início'},
        {'path': '/login', 'title': 'Login'},
        {'path': '/painel', 'title': 'Painel'},
        {'path': '/usuarios', 'title': 'Usuários'},
        {'path': '/medicos', 'title': 'Médicos'},
        {'path': '/agendamentos', 'title': 'Agendamentos'},
    ]})


if __name__ == '__main__':
    print("--------------------------------------------------")
    port = int(os.environ.get('PORT', '3000'))
    print(f" Servidor Rodando em: http://127.0.0.1:{port} ")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', debug=False, port=port)
