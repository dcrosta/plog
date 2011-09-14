__all__ = ('Comment', 'Post', 'PostForm', 'User')

from datetime import date, datetime
import re

from wtforms import Form, BooleanField, DateField, TextField, TextAreaField
from wtforms.validators import Required

from plog import db


boundary = re.compile(r'\s')
nopunc = re.compile(r'[^a-z0-9]')

class Comment(db.EmbeddedDocument):
    author = db.StringField(required=True)
    body = db.StringField(required=True)

class Post(db.Document):
    pubdate = db.DateTimeField(required=True)
    published = db.BooleanField(default=True)

    title = db.StringField(required=True)

    # e.g. "2011/09/05/foo-bar-baz"
    slug = db.StringField(required=True, unique=True)

    blurb = db.StringField(required=True)
    body = db.StringField(required=False)

    comments = db.ListField(db.EmbeddedDocumentField(Comment))

    # for search
    _words = db.ListField(db.StringField())

    meta = {
        'allow_inheritance': False,
        'indexes': [
            {'fields': ['published', '_words', 'pubdate']},
            {'fields': ['slug', 'published', 'pubdate']},
        ],

    }

    def save(self):
        words = set(boundary.split(self.title.lower()))
        words.update(boundary.split(self.blurb.lower()))
        words.update(boundary.split(self.body.lower()))
        words = set(nopunc.sub('', word) for word in words)
        self._words = list(words)

        if isinstance(self.pubdate, date):
            self.pubdate = datetime(
                self.pubdate.year,
                self.pubdate.month,
                self.pubdate.day)

        super(Post, self).save()


class PostForm(Form):
    title = TextField(label='Title', validators=[Required()])
    slug = TextField(label='Slug')
    published = BooleanField(label='Published', default=True)
    pubdate = DateField(label='Date', description='Generated if left blank')
    blurb = TextAreaField(label='Blurb', validators=[Required()])
    body = TextAreaField(label='Body')


class User(db.Document):
    username = db.StringField(required=True, unique=True)
    # bcrypted, of course
    password = db.StringField(required=True)

    first_name = db.StringField()
    last_name = db.StringField()
    email = db.StringField()

    meta = {
        'allow_inheritance': False,
    }

