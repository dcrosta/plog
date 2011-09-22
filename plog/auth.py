__all__ = ('User', 'is_logged_in', 'login_required', 'LoginForm', 'EditUserForm')

from bcrypt import gensalt, hashpw
from functools import wraps
from urllib import urlencode, quote

from mongoengine import *

from flask import abort, g, redirect, request, session, url_for
import wtforms
from wtforms import validators

from plog import app, db
from plog.utils import randstring


class User(Document):
    username = StringField(required=True, unique=True)
    password = StringField(required=True)

    first_name = StringField()
    last_name = StringField()
    email = StringField()

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

class LoginForm(wtforms.Form):
    username = wtforms.TextField(validators=[validators.Required(message='Required')])
    password = wtforms.PasswordField(validators=[validators.Required(message='Required')])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False
        username, password = self.username.data, self.password.data
        self.user = authenticate(username, password)
        if self.user is None:
            self.errors['__all__'] = ['Invalid login']
        return self.user is not None

class EditUserForm(wtforms.Form):
    username = wtforms.TextField()

    password = wtforms.PasswordField(validators=[validators.Length(min=8, message='Too short')])
    confirm = wtforms.PasswordField(validators=[validators.EqualTo('password', 'Password mismatch')])

    first_name = wtforms.TextField()
    last_name = wtforms.TextField()
    email = wtforms.TextField()



@app.before_request
def csrf_dance():
    def newcsrf():
        mycsrf = randstring()
        session['csrf'] = mycsrf

    if 'csrf' not in session:
        newcsrf()

    if request.method not in ('HEAD', 'GET'):
        if 'csrf' not in request.form or 'csrf' not in session:
            newcsrf()
            abort(403)
        if request.form['csrf'] != session['csrf']:
            newcsrf()
            abort(403)

