__all__ = ('User', 'is_logged_in', 'login_required', 'LoginForm', 'EditUserForm')

from bcrypt import gensalt, hashpw
from functools import wraps
from urllib import urlencode, quote

from flask import redirect, request, session, url_for
from wtforms import Form, TextField, PasswordField
from wtforms.validators import EqualTo, Length, Required

from plog import app, db


class User(db.Document):
    username = db.StringField(required=True, unique=True)
    password = db.StringField(required=True)

    first_name = db.StringField()
    last_name = db.StringField()
    email = db.StringField()

    def set_password(self, raw_password):
        self.password = hashpw(raw_password, gensalt(app.config.get('BCRYPT_LOG_ROUNDS', 14)))

    meta = {
        'allow_inheritance': False,
    }

def is_logged_in():
    return session.get('authenticated', False)

def login_required(func):
    @wraps(func)
    def checkauth(*args, **kwargs):
        if is_logged_in():
            return func(*args, **kwargs)
        else:
            url = quote(request.script_root + request.path)
            if request.args:
                url += '?' + urlencode(request.args)
            return redirect(url_for('login', next=url))
    return checkauth

def authenticate(username, password):
    user = User.objects(username=username).first()
    if user and hashpw(password, user.password) == user.password:
        return user
    return None

def create_user(username, password, **kwargs):
    user = User(
        username=username,
        **kwargs)
    user.set_password(password)
    try:
        user.save()
        return user
    except:
        # probably duplicate username
        return None

class LoginForm(Form):
    username = TextField(validators=[Required(message='Required')])
    password = PasswordField(validators=[Required(message='Required')])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False
        username, password = self.username.data, self.password.data
        self.user = authenticate(username, password)
        if self.user is None:
            self.errors['__all__'] = ['Invalid login']
        return self.user is not None

class EditUserForm(Form):
    username = TextField()

    password = PasswordField(validators=[Length(min=8, message='Too short')])
    confirm = PasswordField(validators=[EqualTo('password', 'Password mismatch')])

    first_name = TextField()
    last_name = TextField()
    email = TextField()



# @app.before_request
# def set_csrf():
#     pass

