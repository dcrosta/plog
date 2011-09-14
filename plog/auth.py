__all__ = ('login_required', 'LoginForm')

from bcrypt import gensalt, hashpw
from functools import wraps
from urllib import urlencode, quote

from flask import redirect, request, session, url_for
from wtforms import Form, TextField, PasswordField
from wtforms.validators import Required

from plog import app
from plog.models import User

def login_required(func):
    @wraps(func)
    def checkauth(*args, **kwargs):
        if session.get('authenticated', False):
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
    username = TextField(
        label='Username',
        validators=[
            Required(message='Required')
    ])
    password = PasswordField(
        label='Password',
        validators=[
            Required(message='Required')
    ])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False
        username, password = self.username.data, self.password.data
        self.user = authenticate(username, password)
        if self.user is None:
            self.errors['__all__'] = ['Invalid login']
        return self.user is not None

# @app.before_request
# def set_csrf():
#     pass

