from flask import Flask, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'minha_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bootstrap = Bootstrap(app)
migrate = Migrate(app, db)


# Modelo de Função
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


# Modelo de Usuário
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


# Formulário de Nome
class NameForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    role = SelectField('Qual é a sua função?', choices=[('admin', 'Administrador'), ('user', 'Usuário'), ('mod', 'Moderador')])
    submit = SubmitField('Enviar')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


# Rota Principal
@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    users = User.query.all()  # Obtém todos os usuários cadastrados
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data, role=Role.query.filter_by(name=form.role.data).first())
            db.session.add(user)
            db.session.commit()
            session['known'] = False
        else:
            session['known'] = True
        session['name'] = form.name.data
        session['role'] = form.role.data
        return redirect(url_for('index'))

    # Criando dicionário de usuários por função
    roles = {
        'Administrador': [],
        'Usuário': [],
        'Moderador': []
    }
    for user in users:
        roles[user.role.name].append(user.username)

    return render_template('index.html', form=form, name=session.get('name'),
                           role=session.get('role'), known=session.get('known', False),
                           users=users, roles=roles)


# Rota para Reinicializar o Banco de Dados
@app.route('/reset-db')
def reset_db():
    db.drop_all()
    db.create_all()
    admin_role = Role(name='Administrator')
    moderator_role = Role(name='Moderator')
    user_role = Role(name='User')

    user_admin = User(username='Admin', role=admin_role)
    user_moderator = User(username='ModUser', role=moderator_role)
    user_guest = User(username='Guest', role=user_role)

    db.session.add_all([admin_role, moderator_role, user_role, user_admin, user_moderator, user_guest])
    db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
