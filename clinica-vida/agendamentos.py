from datetime import date, datetime
import sqlite3

from flask import flash, redirect, render_template, request, url_for


def registrar_rotas_agendamentos(app, get_db_connection):
    """Inicializa o esquema da agenda e registra suas rotas Flask."""

    def colunas(conn, tabela):
        return {row['name'] for row in conn.execute(f'PRAGMA table_info({tabela})')}

    def tabela_existe(conn, tabela):
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (tabela,),
        ).fetchone()
        return row is not None

    def inserir_usuario_perfil(conn, tipo, indice):
        """Cria um usuário de demonstração quando o banco usa perfis vinculados."""
        nome = ('Paciente', 'Demonstração') if tipo == 'PACIENTE' else ('Médico', 'Demonstração')
        nome = f'{nome[0]} {indice}'
        email = f'demo.{tipo.lower()}{indice}@clinica.test'
        existente = conn.execute(
            'SELECT id_usuario FROM usuario WHERE email = ?', (email,)
        ).fetchone()
        if existente:
            return existente['id_usuario']
        cursor = conn.execute(
            'INSERT INTO usuario (nome, email, senha_hash, tipo_usuario) VALUES (?, ?, ?, ?)',
            (nome, email, 'hash-de-demonstracao', tipo),
        )
        return cursor.lastrowid

    def semear_perfis_vinculados(conn, tabela, tipo):
        """Preenche opções de demonstração se a tabela de perfil vinculada estiver vazia."""
        profile_columns = colunas(conn, tabela)
        user_columns = colunas(conn, 'usuario')
        count = conn.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0]
        if count or 'id_usuario' not in profile_columns:
            return
        if not {'nome', 'email', 'senha_hash', 'tipo_usuario'}.issubset(user_columns):
            return

        exemplos = (
            [
                ('data_nascimento', '1990-04-12'),
                ('telefone', '(11) 99999-1001'),
                ('endereco', 'Rua das Flores, 100'),
            ]
            if tabela == 'paciente'
            else [
                ('crm', 'CRM-SP-DEMO-101'),
                ('especialidade', 'Clínica geral'),
                ('telefone', '(11) 98888-2001'),
            ]
        )
        for indice in range(1, 4):
            id_usuario = inserir_usuario_perfil(conn, tipo, indice)
            dados = {'id_usuario': id_usuario}
            for campo, valor in exemplos:
                if campo in profile_columns:
                    if campo == 'crm':
                        valor = f'CRM-SP-DEMO-{100 + indice}'
                    elif campo == 'telefone':
                        valor = f'(11) 98888-{2000 + indice}' if tabela == 'medico' else f'(11) 99999-{1000 + indice}'
                    dados[campo] = valor
            campos = list(dados)
            marcadores = ', '.join('?' for _ in campos)
            conn.execute(
                f"INSERT INTO {tabela} ({', '.join(campos)}) VALUES ({marcadores})",
                tuple(dados[campo] for campo in campos),
            )

    def inicializar_agendamentos():
        conn = get_db_connection()
        try:
            if not tabela_existe(conn, 'paciente'):
                conn.execute(
                    '''CREATE TABLE paciente (
                        id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        telefone TEXT,
                        email TEXT
                    )'''
                )
                conn.executemany(
                    'INSERT INTO paciente (nome, telefone, email) VALUES (?, ?, ?)',
                    [
                        ('Mariana Costa', '(11) 97777-3001', 'mariana@example.test'),
                        ('Pedro Almeida', '(11) 97777-3002', 'pedro@example.test'),
                        ('Beatriz Santos', '(11) 97777-3003', 'beatriz@example.test'),
                    ],
                )

            if not tabela_existe(conn, 'agendamento'):
                conn.execute(
                    '''CREATE TABLE agendamento (
                        id_agendamento INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_paciente INTEGER NOT NULL,
                        id_medico INTEGER NOT NULL,
                        data_hora TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'Agendado'
                            CHECK (status IN ('Agendado', 'Confirmado', 'Realizado', 'Cancelado')),
                        motivo TEXT,
                        FOREIGN KEY (id_paciente) REFERENCES paciente (id_paciente)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
                        FOREIGN KEY (id_medico) REFERENCES medico (id_medico)
                            ON UPDATE CASCADE ON DELETE RESTRICT
                    )'''
                )

            # Compatibilidade com o esquema de perfis da Questão 2.
            if tabela_existe(conn, 'usuario'):
                if tabela_existe(conn, 'paciente') and 'id_usuario' in colunas(conn, 'paciente'):
                    semear_perfis_vinculados(conn, 'paciente', 'PACIENTE')
                if tabela_existe(conn, 'medico') and 'id_usuario' in colunas(conn, 'medico'):
                    semear_perfis_vinculados(conn, 'medico', 'MEDICO')

            # O índice UNIQUE protege contra conflitos também fora da aplicação.
            # Se o banco legado já tiver duplicidades, preservamos os dados e
            # mantemos o bloqueio transacional no fluxo de gravação abaixo.
            try:
                conn.execute(
                    '''CREATE UNIQUE INDEX IF NOT EXISTS uq_agendamento_medico_data_hora
                       ON agendamento (id_medico, data_hora)'''
                )
            except sqlite3.IntegrityError:
                app.logger.warning(
                    'Há horários duplicados legados; índice único não aplicado. '
                    'Novos conflitos continuam bloqueados nas rotas de gravação.'
                )
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_agendamento_paciente ON agendamento (id_paciente)'
            )
            conn.commit()
        finally:
            conn.close()

    inicializar_agendamentos()

    def consulta_pacientes(conn):
        patient_columns = colunas(conn, 'paciente')
        if 'nome' in patient_columns:
            return '''SELECT id_paciente, nome FROM paciente ORDER BY nome'''
        if 'id_usuario' in patient_columns:
            return '''SELECT p.id_paciente, u.nome
                      FROM paciente p JOIN usuario u ON u.id_usuario = p.id_usuario
                      ORDER BY u.nome'''
        return '''SELECT id_paciente, 'Paciente ' || id_paciente AS nome
                  FROM paciente ORDER BY id_paciente'''

    def consulta_medicos(conn):
        doctor_columns = colunas(conn, 'medico')
        if 'nome' in doctor_columns:
            specialty = 'especialidade' if 'especialidade' in doctor_columns else "'' AS especialidade"
            return f'''SELECT id_medico, nome, {specialty} FROM medico ORDER BY nome'''
        if 'id_usuario' in doctor_columns:
            specialty = 'm.especialidade' if 'especialidade' in doctor_columns else "'' AS especialidade"
            return f'''SELECT m.id_medico, u.nome, {specialty}
                       FROM medico m JOIN usuario u ON u.id_usuario = m.id_usuario
                       ORDER BY u.nome'''
        return '''SELECT id_medico, 'Médico ' || id_medico AS nome, '' AS especialidade
                  FROM medico ORDER BY id_medico'''

    def linhas_agendamentos(conn):
        pacientes = consulta_pacientes(conn)
        medicos = consulta_medicos(conn)
        rows = conn.execute(
            f'''SELECT a.id_agendamento, a.id_paciente, a.id_medico,
                       a.data_hora, a.status, a.motivo,
                       p.nome AS paciente_nome, m.nome AS medico_nome,
                       COALESCE(m.especialidade, '') AS especialidade
                FROM agendamento a
                LEFT JOIN ({pacientes}) p ON p.id_paciente = a.id_paciente
                LEFT JOIN ({medicos}) m ON m.id_medico = a.id_medico
                ORDER BY a.data_hora DESC, a.id_agendamento DESC'''
        ).fetchall()
        resultado = []
        for row in rows:
            item = dict(row)
            try:
                instante = datetime.fromisoformat(item['data_hora'])
                item['data_formatada'] = instante.strftime('%d/%m/%Y')
                item['hora_formatada'] = instante.strftime('%H:%M')
            except (TypeError, ValueError):
                item['data_formatada'] = item['data_hora']
                item['hora_formatada'] = ''
            resultado.append(item)
        return resultado

    def obter_edicao(conn, id_agendamento):
        if id_agendamento is None:
            return None
        row = conn.execute(
            'SELECT * FROM agendamento WHERE id_agendamento = ?', (id_agendamento,)
        ).fetchone()
        return dict(row) if row else None

    def valores_form(editing=None, submitted=None):
        if submitted is not None:
            return {
                'id_paciente': submitted.get('id_paciente', ''),
                'id_medico': submitted.get('id_medico', ''),
                'data': submitted.get('data', ''),
                'horario': submitted.get('horario', ''),
                'descricao': submitted.get('descricao', ''),
            }
        if editing:
            try:
                instante = datetime.fromisoformat(editing['data_hora'])
                data = instante.strftime('%Y-%m-%d')
                horario = instante.strftime('%H:%M')
            except (TypeError, ValueError):
                data, horario = '', ''
            return {
                'id_paciente': str(editing['id_paciente']),
                'id_medico': str(editing['id_medico']),
                'data': data,
                'horario': horario,
                'descricao': editing.get('motivo') or '',
            }
        return {'id_paciente': '', 'id_medico': '', 'data': date.today().isoformat(), 'horario': '', 'descricao': ''}

    def renderizar(conn, editing=None, submitted=None, status=200):
        pacientes = conn.execute(consulta_pacientes(conn)).fetchall()
        medicos = conn.execute(consulta_medicos(conn)).fetchall()
        return render_template(
            'agendamentos.html',
            pacientes=pacientes,
            medicos=medicos,
            agendamentos=linhas_agendamentos(conn),
            editing=editing,
            valores=valores_form(editing, submitted),
        ), status

    def salvar(id_agendamento=None):
        conn = get_db_connection()
        editing = obter_edicao(conn, id_agendamento) if id_agendamento else None
        if id_agendamento and not editing:
            conn.close()
            flash('O agendamento que você tentou editar não foi encontrado.', 'erro')
            return redirect(url_for('agendamentos'))

        try:
            id_paciente = int(request.form.get('id_paciente', ''))
            id_medico = int(request.form.get('id_medico', ''))
            data = date.fromisoformat(request.form.get('data', ''))
            horario = datetime.strptime(request.form.get('horario', ''), '%H:%M').time()
            descricao = request.form.get('descricao', '').strip()
            if not descricao:
                raise ValueError('Informe uma descrição para a consulta.')
            if len(descricao) > 500:
                raise ValueError('A descrição deve ter no máximo 500 caracteres.')
        except (TypeError, ValueError):
            flash('Confira paciente, médico, data, horário e descrição antes de salvar.', 'erro')
            resposta = renderizar(conn, editing=editing, submitted=request.form, status=400)
            conn.close()
            return resposta

        data_hora = f'{data.isoformat()} {horario.strftime("%H:%M")}'
        # Serializa escritores para que duas requisições simultâneas não passem
        # pela pré-verificação do mesmo horário antes que uma delas grave.
        conn.execute('BEGIN IMMEDIATE')
        conflito = conn.execute(
            '''SELECT 1 FROM agendamento
               WHERE id_medico = ? AND data_hora = ?
                 AND id_agendamento != COALESCE(?, -1)
               LIMIT 1''',
            (id_medico, data_hora, id_agendamento),
        ).fetchone()
        if conflito:
            flash('Este médico já tem uma consulta marcada nessa data e horário. Escolha outro horário.', 'erro')
            resposta = renderizar(conn, editing=editing, submitted=request.form, status=409)
            conn.close()
            return resposta

        try:
            if id_agendamento:
                conn.execute(
                    '''UPDATE agendamento
                       SET id_paciente = ?, id_medico = ?, data_hora = ?, motivo = ?
                       WHERE id_agendamento = ?''',
                    (id_paciente, id_medico, data_hora, descricao, id_agendamento),
                )
                mensagem = 'Agendamento atualizado com sucesso.'
            else:
                conn.execute(
                    '''INSERT INTO agendamento (id_paciente, id_medico, data_hora, motivo)
                       VALUES (?, ?, ?, ?)''',
                    (id_paciente, id_medico, data_hora, descricao),
                )
                mensagem = 'Consulta agendada com sucesso.'
            conn.commit()
            flash(mensagem, 'sucesso')
        except sqlite3.IntegrityError:
            flash('Não foi possível salvar: verifique se o médico já está ocupado nesse horário.', 'erro')
            resposta = renderizar(conn, editing=editing, submitted=request.form, status=409)
            conn.close()
            return resposta
        finally:
            # A conexão pode já ter sido encerrada nos retornos acima.
            try:
                conn.close()
            except sqlite3.Error:
                pass
        return redirect(url_for('agendamentos'))

    @app.route('/agendamentos', methods=['GET', 'POST'])
    def agendamentos():
        if request.method == 'POST':
            return salvar()
        conn = get_db_connection()
        editing = obter_edicao(conn, request.args.get('editar', type=int))
        resposta = renderizar(conn, editing=editing)
        conn.close()
        return resposta

    @app.post('/agendamentos/<int:id_agendamento>/editar')
    def salvar_edicao_agendamento(id_agendamento):
        return salvar(id_agendamento)

    @app.post('/agendamentos/<int:id_agendamento>/cancelar')
    def cancelar_agendamento(id_agendamento):
        conn = get_db_connection()
        cursor = conn.execute(
            'DELETE FROM agendamento WHERE id_agendamento = ?', (id_agendamento,)
        )
        conn.commit()
        conn.close()
        if cursor.rowcount:
            flash('Agendamento cancelado.', 'sucesso')
        else:
            flash('O agendamento já não existe.', 'erro')
        return redirect(url_for('agendamentos'))
