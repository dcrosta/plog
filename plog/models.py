__all__ = ('Comment', 'Post', 'PostForm', 'TagCloud')

from bcrypt import gensalt, hashpw
from datetime import date, datetime
from math import ceil
import re
from pytz import timezone, utc

from mongoengine import *

import wtforms
from wtforms import validators

from plog import app


boundary = re.compile(r'\s')
nopunc = re.compile(r'[^a-z0-9]')

class TagCloud(Document):
    tag = StringField(primary_key=True)
    count = IntField()
    updated = DateTimeField()

    meta = {
        'allow_inheritance': False,
        'indexes': [
            {'fields': ['count', 'tag']},
        ],
    }

    @staticmethod
    def get(sizes=6):
        tags = [t for t in TagCloud.objects(count__gt=0).order_by('tag')]
        if tags == []:
            return tags

        least = min(t.count for t in tags)
        most = max(t.count for t in tags)
        range = max(most - least, 1)
        scale = float(min(range, sizes))
        for t in tags:
            t.bucket = sizes -  int(round(scale * (t.count - least) / range))

        return tags


class Comment(EmbeddedDocument):
    author = StringField(required=True)
    body = StringField(required=True)

class Post(Document):
    pubdate = DateTimeField(required=True)
    updated = DateTimeField()
    published = BooleanField(default=True)

    title = StringField(required=True)
    slug = StringField(required=True, unique=True)

    blurb = StringField(required=True)
    body = StringField(required=False)

    tags = ListField(StringField())

    comments = ListField(EmbeddedDocumentField(Comment))

    _words = ListField(StringField())

    meta = {
        'allow_inheritance': False,
        'indexes': [
            {'fields': ['published', '_words', 'pubdate']},
            {'fields': ['published', 'slug', 'pubdate']},
        ],
    }

    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)

        # perform timezone conversion to UTC;
        # if datetime fields don't have a timezone,
        # assume they are in site_tz's timezone
        site_tz = timezone(app.config.get('TIMEZONE', 'US/Eastern'))
        if self.pubdate is not None and self.pubdate.tzinfo is None:
            self.pubdate = self.pubdate.replace(tzinfo=utc).astimezone(site_tz)

    def save(self):
        words = set(boundary.split(self.title.lower()))
        words.update(boundary.split(self.blurb.lower()))
        words.update(boundary.split(self.body.lower()))
        words = set(nopunc.sub('', word) for word in words)
        self._words = list(words)

        # perform timezone conversion to UTC;
        # if datetime fields don't have a timezone,
        # assume they are in site_tz's timezone
        site_tz = timezone(app.config.get('TIMEZONE', 'US/Eastern'))

        # pubdate is required
        if self.pubdate.tzinfo is None:
            self.pubdate = site_tz.localize(self.pubdate)
        self.pubdate = self.pubdate.astimezone(utc).replace(tzinfo=None)

        self.updated = datetime.utcnow()
        super(Post, self).save()

class CommaListField(wtforms.TextField):

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

class PostForm(wtforms.Form):
    title = wtforms.TextField(label='Title', validators=[validators.Required()])
    slug = wtforms.TextField(label='Slug')

    tags = CommaListField()

    pubdate = wtforms.DateTimeField(label='Date', format='%Y-%m-%d %H:%M')
    published = wtforms.BooleanField(label='Published', default=False)
    blurb = wtforms.TextAreaField(label='Blurb', validators=[validators.Required()])
    body = wtforms.TextAreaField(label='Body')

    @property
    def known_tags(self):
        return [t.tag for t in TagCloud.objects.order_by('tag').only('tag')]

