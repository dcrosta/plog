__all__ = ('get_or_404',)

from flask import abort

def get_or_404(cls, **kwargs):
    obj = cls.objects(**kwargs).first()
    if obj is None:
        abort(404)
    return obj

