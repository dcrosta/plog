__all__ = ('app', 'app_factory')

from datetime import datetime, timedelta
from os.path import abspath, dirname, exists, join

from flask import *
from flaskext.mongoengine import MongoEngine, MongoSessionStore

here = dirname(__file__)
parent = abspath(join(dirname(__file__), '..'))

config = join(parent, 'plog.cfg')
private = join(parent, 'private.plog.cfg')

class SessionMixin(object):
    __slots__ = ('session_store',)

    @property
    def session_key(self):
        return app.config.get('SESSION_COOKIE_NAME', '_plog_session')

    def open_session(self, request):
        sid = request.cookies.get(self.session_key, None)
        if sid is not None:
            return self.session_store.get(sid)
        return self.session_store.new()

    def save_session(self, session, response):
        if session.should_save:
            self.session_store.save(session)

            lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(minutes=30))
            response.set_cookie(
                self.session_key,
                session.sid,
                max_age=lifetime.seconds + lifetime.days * 24 * 3600,
                expires= datetime.utcnow() + lifetime,
                secure=app.config.get('SESSION_COOKIE_SECURE', False),
                httponly=app.config.get('SESSION_COOKIE_HTTPONLY', False),
                domain=app.config.get('SESSION_COOKIE_DOMAIN', None),
                path=app.config.get('SESSION_COOKIE_PATH', '/'),
            )
        return response

class SessionFlask(SessionMixin, Flask):
    pass

app = SessionFlask('plog')

if exists(config):
    app.config.from_pyfile(config)
if exists(private):
    app.config.from_pyfile(private)

db = MongoEngine(app)
app.session_store = MongoSessionStore(db)

import plog.filters
import plog.views

import pprint
