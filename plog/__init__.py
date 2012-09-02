__all__ = ('app', 'app_factory')

from datetime import datetime, timedelta
from os.path import abspath, dirname, exists, join
from subprocess import check_output

from flask import Flask
from plog.session import SessionMixin, MongoSessionStore
from mongoengine import connect

here = dirname(__file__)
parent = abspath(join(dirname(__file__), '..'))

class SessionFlask(SessionMixin, Flask):
    pass

app = SessionFlask('plog')

try:
    git_hash = check_output(['git', 'rev-parse', 'HEAD'], cwd=parent)
    app.config['DEPLOYSTAMP'] = git_hash[:6]
except:
    app.config['DEPLOYSTAMP'] = '1234'

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

