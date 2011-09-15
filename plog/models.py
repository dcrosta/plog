__all__ = ('Comment', 'Post', 'PostForm', 'User', 'TagCloud')

from bcrypt import gensalt, hashpw
from datetime import date, datetime
from math import ceil
import re

from wtforms import Form, BooleanField, DateField, TextField, TextAreaField
from wtforms.validators import Required

from plog import app, db


boundary = re.compile(r'\s')
nopunc = re.compile(r'[^a-z0-9]')

class TagCloud(db.Document):
    tag = db.StringField(primary_key=True)
    count = db.IntField()

    meta = {
        'allow_inheritance': False,
        'indexes': [
            {'fields': ['tag', '-count']},
        ],
    }

    @staticmethod
    def update():
        results = Post.objects(published=True).map_reduce(
            map_f="""
            function() {
                var tags = this.tags || [];
                tags.forEach(function(tag) {
                    emit(tag, 1);
                });
            }""",
            reduce_f="""
            function(key, values) {
                return values.length;
            }""",
            output="tagcloud_tmp"
        )
        seen = set()
        for result in results:
            TagCloud(tag=result.key, count=int(result.value)).save()
            seen.add(result.key)
        TagCloud.objects(tag__nin=seen).delete()

    @staticmethod
    def get(sizes=6):
        tags = [t for t in TagCloud.objects.order_by('tag')]
        if tags == []:
            return tags

        least = min(t.count for t in tags)
        most = max(t.count for t in tags)
        range = max(most - least, 1)
        scale = float(min(range, sizes))
        for t in tags:
            t.bucket = sizes -  int(round(scale * (t.count - least) / range))

        return tags


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

    tags = db.ListField(db.StringField())

    comments = db.ListField(db.EmbeddedDocumentField(Comment))

    # analytics
    views = db.IntField()

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

        # additionally, update the tag cloud
        # map-reduce
        TagCloud.update()

class CommaListField(TextField):

    def _value(self):
        if self.data:
            return ', '.join(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',')]
            self.data = [x for x in self.data if x != '']
        else:
            self.data = []

class PostForm(Form):
    title = TextField(label='Title', validators=[Required()])
    slug = TextField(label='Slug')

    tags = CommaListField()

    pubdate = DateField(label='Date')
    published = BooleanField(label='Published', default=True)
    blurb = TextAreaField(label='Blurb', validators=[Required()])
    body = TextAreaField(label='Body')

    @property
    def known_tags(self):
        return [t.tag for t in TagCloud.objects.order_by('tag').only('tag')]


class User(db.Document):
    username = db.StringField(required=True, unique=True)
    password = db.StringField(required=True)

    first_name = db.StringField()
    last_name = db.StringField()
    email = db.StringField()

    def set_password(self, raw_password):
        self.password = hashpw(password, gensalt(app.config.get('BCRYPT_LOG_ROUNDS', 14)))

    meta = {
        'allow_inheritance': False,
    }

