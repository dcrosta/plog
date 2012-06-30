__all__ = ('app', 'app_factory')

from datetime import datetime, timedelta
from os.path import abspath, dirname, exists, join

from flask import Flask
from plog.session import SessionMixin, MongoSessionStore
from mongoengine import connect

here = dirname(__file__)
parent = abspath(join(dirname(__file__), '..'))

class SessionFlask(SessionMixin, Flask):
    pass

app = SessionFlask('plog')

app.config['DEPLOYSTAMP'] = '1234'

# set the deploy stamp from git hash
try:
    lookat = here
    while lookat != '/':
        if exists(join(lookat, '.git')):
            HEAD = file(join(lookat, '.git', 'HEAD')).read().strip()
            HEAD = HEAD[5:]
            ref = file(join(lookat, '.git', HEAD)).read().strip()
            app.config['DEPLOYSTAMP'] = ref[:6]
        lookat = dirname(lookat)
except:
    pass

config = join(parent, 'plog.cfg')
if exists(config):
    app.config.from_pyfile(config)

private = join(parent, 'private.plog.cfg')
if exists(private):
    app.config.from_pyfile(private)

mongo_config = app.config.get('MONGODB_CONFIG', {'db': 'plog'})
db_name = mongo_config['db']
conn = connect(**mongo_config)
db = conn[db_name]
app.session_store = MongoSessionStore(db)

import plog.filters
import plog.views

