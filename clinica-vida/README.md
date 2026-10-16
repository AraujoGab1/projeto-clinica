# Clínica Vida — agendamentos

Projeto Flask e SQLite da atividade. A página nova fica em `templates/agendamentos.html` e é acessada em `/agendamentos`.

## Executar localmente

1. Instale Python 3.10 ou superior.
2. No terminal, entre na pasta que contém `app.py`.
3. Instale a dependência com `python -m pip install -r requirements.txt`.
4. Inicie com `python app.py`.
5. Abra `http://127.0.0.1:3000/agendamentos` no navegador.

O banco `clinica.db` é criado automaticamente na pasta do projeto. Se você já possui um banco, coloque uma cópia de `clinica.db` junto a `app.py`; a inicialização mantém as tabelas existentes e acrescenta a tabela de agendamentos quando necessário. O app aceita o esquema legado enviado no ZIP e o esquema de perfis (com `id_usuario`) criado na Questão 2.

O formulário usa os pacientes e médicos cadastrados no banco. No esquema legado, a página inclui pacientes de demonstração e conserva os médicos de exemplo já existentes no `app.py`. O status inicial dos novos atendimentos é `Agendado`.

## Regras implementadas

- Criar, listar, editar e cancelar agendamentos; cancelar remove o registro e libera o horário para uma nova consulta.
- Paciente, médico, data, horário e descrição são obrigatórios.
- A aplicação verifica conflitos dentro de uma transação SQLite; um índice `UNIQUE` também protege contra duplicidade no banco. Se um banco antigo já tiver duplicidades, os registros são preservados e a aplicação mantém a verificação transacional para novas gravações.
- O horário é salvo em `data_hora`, no formato `AAAA-MM-DD HH:MM`.

## Evidências

As capturas solicitadas estão na pasta `evidence/`: `captura_agendamentos.png` mostra o formulário e a listagem; `captura_edicao.png` mostra um agendamento preenchido no modo de edição.

## Banco de demonstração

O arquivo `clinica.db` não é versionado nem incluído no pacote de código. Ao iniciar a aplicação, ela cria uma base local quando não encontra uma existente. Para trocar o caminho, configure `CLINICA_DB_PATH`. A chave de sessão pode ser definida em `FLASK_SECRET_KEY`; o valor embutido no código é apenas um fallback de desenvolvimento.
