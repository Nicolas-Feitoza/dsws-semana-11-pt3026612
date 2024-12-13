import os
import requests
import logging
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Regexp, ValidationError
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

# Configuração inicial e setup de logging
basedir = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO)  # Define o nível de log como INFO
logger = logging.getLogger(__name__)  # Cria um logger nomeado

# Configuração do aplicativo Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'uma-chave-secreta'  # Chave secreta para desenvolvimento
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')  # Banco de dados SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do Mailgun
app.config['MAILGUN_API_KEY'] = os.getenv('MAILGUN_API_KEY')
app.config['MAILGUN_DOMAIN'] = os.getenv('MAILGUN_DOMAIN')
app.config['MAILGUN_FROM'] = os.getenv('MAILGUN_FROM')
app.config['MAILGUN_API_URL'] = (
    f'https://api.mailgun.net/v3/{app.config["MAILGUN_DOMAIN"]}/messages' if app.config['MAILGUN_DOMAIN'] else ''
)
app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_ADMIN'] = os.getenv('FLASKY_ADMIN')

# Inicialização de extensões do Flask
bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelos do banco de dados
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    prontuario = db.Column(db.String(10), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return f'<User {self.username} - Prontuário {self.prontuario}>'


# Função para enviar mensagens usando o Mailgun
def send_simple_message(to, subject, new_user):
    if not app.config['MAILGUN_API_KEY'] or not app.config['MAILGUN_API_URL']:
        logger.warning('⚠️ Mailgun não configurado corretamente. Mensagem não enviada.')
        return

    try:
        logger.info("Enviando mensagem para %s", to)
        resposta = requests.post(
            app.config['MAILGUN_API_URL'],
            auth=('api', app.config['MAILGUN_API_KEY']),
            data={
                'from': f"Flasky <noreply@{app.config['MAILGUN_DOMAIN']}>",
                'to': ', '.join(to) if isinstance(to, list) else to,
                'subject': app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                'text': "Novo usuário cadastrado: " + new_user,
            }
        )
        if resposta.status_code == 200:
            logger.info(f"✅ Mensagem enviada com sucesso! - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            logger.error(f'⚠️ Falha ao enviar mensagem. Código: {resposta.status_code}')
    except Exception as e:
        logger.exception('Erro ao tentar enviar mensagem:', exc_info=e)


# Formulário Flask-WTF
class NameForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    prontuario = StringField(
        'Digite seu prontuário',
        validators=[
            DataRequired(),
            Regexp(r'^[a-zA-Z]{3}\d{7}$', message='O prontuário deve ter 3 letras seguidas de 7 números.')
        ]
    )
    notificar_admin = BooleanField('Deseja enviar e-mail para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Enviar')

    def validate_prontuario(self, field):
        if User.query.filter_by(prontuario=field.data).first():
            raise ValidationError('Este prontuário já está cadastrado.')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(prontuario=form.prontuario.data).first()
        if user is None:
            user = User(username=form.name.data, prontuario=form.prontuario.data)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            recipients = [app.config['FLASKY_ADMIN']]
            if form.notificar_admin.data:
                recipients.append('flaskaulasweb@zohomail.com')

            send_simple_message(
                to=recipients,
                subject='Novo usuário',
                new_user=f"Nome: {form.name.data}, Prontuário: {form.prontuario.data}"
            )
        else:
            session['known'] = True
            flash('Prontuário já cadastrado!')
        session['name'] = form.name.data
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False), users=users)


if __name__ == '__main__':
    app.run()
