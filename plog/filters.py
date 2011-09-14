import re

from plog import app

from markdown2 import markdown
app.jinja_env.filters['markdown'] = markdown

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

@app.template_filter('pygments')
def pygments(value):
    # assume value is a markdown-formatted
    # text area, and we're looking for the
    # code blocks, a series of lines indented
    # by 4 spaces

    lines = value.split('\n')
    return value
