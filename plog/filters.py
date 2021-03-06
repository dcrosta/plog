import json
from pytz import utc, timezone
import re

from plog import app

from markup import markup
@app.template_filter('markdown')
def domarkdown(value):
    return markup(value)

nozero_re = re.compile(r'(?:^|\s)0(\d)')
@app.template_filter('nozero')
def nozero(value, strip=False):
    """
    >>> nozero("March 03, 2011")
    'March 3, 2011'
    """
    if strip:
      return nozero_re.sub(r'\1', value)
    return nozero_re.sub(r' \1', value)

@app.template_filter('nonone')
def no_none(value, default=''):
    if value is None:
        return default
    return value

@app.template_filter('json')
def to_json(value):
    return json.dumps(value, separators=(',', ':'))

@app.template_filter('datetime')
def fmt_datetime(value, fmt, tz='US/Eastern'):
    tz = timezone(tz)
    if value.tzinfo is None:
        value = value.replace(tzinfo=utc)
    value = value.astimezone(tz)
    return value.strftime(fmt)

