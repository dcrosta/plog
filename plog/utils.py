__all__ = ('get_or_404',)

from datetime import datetime, timedelta

from plog import app
from flask import abort, request

def get_or_404(cls, **kwargs):
    obj = cls.objects(**kwargs).first()
    if obj is None:
        abort(404)
    return obj

@app.after_request
def set_cache_headers(response):
    if not request.path.startswith('/admin'):
        response.cache_control.public = True
        response.cache_control.max_age = 6 * 60 * 60
    if response.expires is None:
        response.expires = datetime.utcnow() + timedelta(hours=6)
    return response
