__all__ = ('SessionMixin', 'MongoSessionStore')

from datetime import datetime, timedelta

from werkzeug.contrib.sessions import SessionStore

from mongoengine import Document, DictField, StringField

class SessionMixin(object):
    __slots__ = ('session_store',)

    @property
    def session_key(self):
        return self.config.get('SESSION_COOKIE_NAME', '_plog_session')

    def open_session(self, request):
        sid = request.cookies.get(self.session_key, None)
        if sid is not None:
            return self.session_store.get(sid)
        return self.session_store.new()

    def save_session(self, session, response):
        if session.should_save:
            self.session_store.save(session)

            lifetime = self.config.get('PERMANENT_SESSION_LIFETIME', timedelta(minutes=30))
            response.set_cookie(
                self.session_key,
                session.sid,
                max_age=lifetime.seconds + lifetime.days * 24 * 3600,
                expires= datetime.utcnow() + lifetime,
                secure=self.config.get('SESSION_COOKIE_SECURE', False),
                httponly=self.config.get('SESSION_COOKIE_HTTPONLY', False),
                domain=self.config.get('SESSION_COOKIE_DOMAIN', None),
                path=self.config.get('SESSION_COOKIE_PATH', '/'),
            )
        return response

class MongoSessionStore(SessionStore):
    """Subclass of :class:`werkzeug.contrib.sessions.SessionStore`
    which stores sessions using MongoDB documents.
    """

    def __init__(self, db, collection='session'):
        super(MongoSessionStore, self).__init__()

        if not isinstance(collection, basestring):
            raise ValueError('collection argument should be string or unicode')

        class DBSession(Document):
            sid = StringField(primary_key=True)
            data = DictField()
            meta = {
                'allow_inheritance': False,
                'collection': collection,
            }

        self.cls = DBSession

    def save(self, session):
        doc = self.cls(
            sid=session.sid,
            data=dict(session))
        doc.save()

    def delete(self, session):
        self.cls.objects(sid=session.sid).delete()

    def get(self, sid):
        doc = self.cls.objects(sid=sid).first()
        if doc:
            return self.session_class(dict(doc.data), sid, False)
        else:
            return self.session_class({}, sid, True)

