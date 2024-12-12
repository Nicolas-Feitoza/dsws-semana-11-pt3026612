import os
import requests
import logging
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

# Configuração inicial e setup de logging
basedir = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO)  # Define o nível de log como INFO
logger = logging.getLogger(__name__)  # Cria um logger nomeado

# Configuração do aplicativo Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Carrega a chave secreta de variáveis de ambiente
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')  # Banco de dados SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Desabilita notificações de modificações no SQLAlchemy

# Configuração para o serviço de envio de e-mails (Mailgun)
app.config['MAILGUN_API_KEY'] = os.getenv('MAILGUN_API_KEY')  # Chave da API do Mailgun
app.config['MAILGUN_DOMAIN'] = os.getenv('MAILGUN_DOMAIN')  # Domínio do Mailgun
app.config['MAILGUN_FROM'] = os.getenv('MAILGUN_FROM')  # Endereço de remetente do Mailgun
app.config['MAILGUN_API_URL'] = (  # URL base da API do Mailgun
    f'https://api.mailgun.net/v3/{app.config["MAILGUN_DOMAIN"]}/messages' if app.config['MAILGUN_DOMAIN'] else ''
)
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'  # Prefixo do assunto dos e-mails
app.config['FLASKY_ADMIN'] = os.getenv('FLASKY_ADMIN')  # Administrador do Flasky

# Inicialização de extensões do Flask
bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelos do banco de dados
class Role(db.Model):  # Tabela de roles (funções ou papéis)
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)  # Chave primária
    name = db.Column(db.String(64), unique=True)  # Nome único para a role
    users = db.relationship('User', backref='role', lazy='dynamic')  # Relacionamento com usuários

    def __repr__(self):
        return '<Role %r>' % self.name  # Representação para depuração


class User(db.Model):  # Tabela de usuários
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)  # Chave primária
    username = db.Column(db.String(64), unique=True, index=True)  # Nome de usuário único
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))  # Relacionamento com roles

    def __repr__(self):
        return '<User %r>' % self.username  # Representação para depuração


# Função para enviar mensagens usando o Mailgun
def send_simple_message(to, subject, new_user):
    # Verifica se as configurações do Mailgun estão completas
    if not app.config['MAILGUN_API_KEY'] or not app.config['MAILGUN_API_URL']:
        logger.warning('⚠️ Mailgun não configurado corretamente. Mensagem não enviada.')
        return

    try:
        logger.info("Enviando mensagem para %s", to)  # Loga o início do envio
        resposta = requests.post(  # Faz uma requisição POST à API do Mailgun
            app.config['MAILGUN_API_URL'],
            auth=('api', app.config['MAILGUN_API_KEY']),
            data={
                'from': f"Flasky <noreply@{app.config['MAILGUN_DOMAIN']}>",
                'to': ', '.join(to) if isinstance(to, list) else to,  # Suporta lista ou string única
                'subject': app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                'text': "Novo usuário cadastrado: " + new_user,
            }
        )
        if resposta.status_code == 200:  # Verifica se a mensagem foi enviada com sucesso
            logger.info(f"✅ Mensagem enviada com sucesso! - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:  # Loga erros de envio
            logger.error(f'⚠️ Falha ao enviar mensagem. Código: {resposta.status_code}')
    except Exception as e:
        logger.exception('Erro ao tentar enviar mensagem:', exc_info=e)  # Loga exceções


# Formulário Flask-WTF
class NameForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])  # Campo obrigatório
    submit = SubmitField('Enviar')  # Botão de envio


@app.shell_context_processor
def make_shell_context():  # Configuração para o shell do Flask
    return dict(db=db, User=User, Role=Role)


# Tratamento de erro 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Tratamento de erro 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()  # Instância do formulário
    if form.validate_on_submit():  # Validação de entrada
        user = User.query.filter_by(username=form.name.data).first()  # Busca no banco
        if user is None:  # Novo usuário
            user = User(username=form.name.data)
            db.session.add(user)  # Adiciona ao banco
            db.session.commit()  # Salva no banco
            session['known'] = False
            flash('Nome cadastrado com sucesso!')  # Mensagem de sucesso

            # Testando envio de e-mail
            if app.config['FLASKY_ADMIN']:
                send_simple_message(
                    [app.config['FLASKY_ADMIN'],'flaskaulasweb@zohomail.com'],
                    'Novo usuário',
                    form.name.data
                )

        else:  # Usuário já conhecido
            session['known'] = True
            flash('Você já está cadastrado! Quer alterar seu nome?')  # Mensagem de usuário já cadastrado
        session['name'] = form.name.data  # Armazena o nome na sessão
        return redirect(url_for('index'))  # Redireciona para evitar reenvio de formulário
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False))  # Renderiza a página


if __name__ == '__main__':
    app.run()  # Executa o servidor de desenvolvimento
