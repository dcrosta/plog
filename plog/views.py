import re
from datetime import datetime, timedelta
import unicodedata

from flask import make_response, redirect, render_template, request, session, url_for
from werkzeug.contrib.atom import AtomFeed

from plog import app
from plog.models import *
from plog.auth import *
from plog.filters import markdown

@app.route('/')
def index():
    num_posts = 10
    posts = Post.objects(published=True).order_by('-pubdate')
    return render_template(
        'index.html',
        posts=posts[:num_posts],
        archive=(posts.count() > num_posts),
        cloud=TagCloud.get(),
    )

@app.route('/feed')
def feed():
    feed = AtomFeed(
        title='late.am',
        feed_url=url_for('feed', _external=True),
        author={'name': 'Dan Crosta', 'email': 'dcrosta@late.am'},
        icon=url_for('static', filename='mug.png', _external=True),
        generator=('plog', 'https://github.com/dcrosta/plog', '0.1'),
    )

    posts = Post.objects(published=True).order_by('-pubdate')
    for post in posts[:20]:
        feed.add(
            title=post.title,
            content=markdown(post.blurb + '\n' + post.body),
            content_type='html',
            author={'name': 'Dan Crosta', 'email': 'dcrosta@late.am'},
            url=url_for('post', slug=post.slug, _external=True),
            id=url_for('permalink', post_id=post.pk, _external=True),
            published=post.pubdate,
            updated=post.updated)

    response = make_response(unicode(feed))
    response.headers['Content-Type'] = 'application/atom+xml; charset=UTF-8'
    return response

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query.strip() != '':
        pass

    query = query.lower()

    boundary = re.compile(r'\s')
    nopunc = re.compile(r'[^a-zA-Z0-9]')

    query = [nopunc.sub('', word) for word in boundary.split(query)]

    posts = Post.objects(published=True, _words__all=query).order_by('-pubdate')
    return render_template(
        'archive.html',
        posts=posts,
        cloud=TagCloud.get(),
    )


@app.route('/post/')
def full_archive():
    return archive(None, None)

@app.route('/post/<int:year>/')
def year_archive(year):
    start = datetime(year=year, month=1, day=1)
    end = datetime(year=year + 1, month=1, day=1)
    return archive(start, end, 'Posts from %Y')

@app.route('/post/<int:year>/<int:month>/')
def month_archive(year, month):
    start = datetime(year=year, month=month, day=1)
    if month == 12:
        year += 1
        month = 0
    end = datetime(year=year, month=month + 1, day=1)
    return archive(start, end, 'Posts from %B %Y')

@app.route('/post/<int:year>/<int:month>/<int:day>/')
def day_archive(year, month, day):
    start = datetime(year=year, month=month, day=day)
    end = start + timedelta(days=1)
    return archive(start, end, 'Posts from %B %d, %Y')

def archive(start, end, fmt):
    posts = Post.objects(published=True).order_by('-pubdate')
    if start and end:
        posts.filter(pubdate__gte=start, pubdate__lt=end)
    posts.only('pubdate', 'slug', 'title', 'tags')
    return render_template(
        'archive.html',
        posts=posts,
        cloud=TagCloud.get(),
        start=start,
        fmt=fmt,
    )

@app.route('/tag/<tag>')
def tag_archive(tag):
    posts = Post.objects(published=True, tags=tag).order_by('-pubdate')
    posts.only('pubdate', 'slug', 'title')
    return render_template(
        'archive.html',
        posts=posts,
        cloud=TagCloud.get(),
        tag=tag,
    )

@app.route('/post/id/<post_id>')
def permalink(post_id):
    post = Post.objects.get_or_404(pk=post_id)
    return redirect(url_for('post', slug=post.slug))

@app.route('/post/<path:slug>')
def post(slug):
    post = Post.objects.get_or_404(slug=slug, published=True)
    if not is_logged_in():
        post.update(inc__views=1)
    return render_template(
        'post.html',
        post=post,
        cloud=TagCloud.get(),
    )

@app.route('/admin/login', methods=['GET'])
def login():
    return render_template(
        'login.html',
        form=LoginForm(),
    )

@app.route('/admin/logout')
def logout():
    del session['authenticated']
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['POST'])
def do_login():
    form = LoginForm(request.form)
    if not form.validate():
        return render_template(
            'login.html',
            form=form,
        )

    session['authenticated'] = True
    session['user_id'] = form.user.pk
    return redirect(request.args.get('next', url_for('dashboard')))


@app.route('/admin')
@login_required
def dashboard():
    # moderation_queue = ...
    posts = Post.objects.order_by('-pubdate')

    # TODO: finish this
    comments = [
    #    {'post': {'title': 'Test', 'slug': '2011/09/13/test'},
    #     'author': {'full_name': 'Nice User', 'email': 'nice.user@gmail.com'},
    #     'body': """<script>alert('evil!');</script>"""},
    ]

    return render_template(
        'dashboard.html',
        posts=posts,
        comments=comments,
    )

@app.route('/admin/post/new', methods=['GET'])
@login_required
def new_post():
    form = PostForm()
    return render_template(
        'edit_post.html',
        form=form,
    )

@app.route('/admin/post/<path:slug>', methods=['GET'])
@login_required
def edit_post(slug):
    post = Post.objects.get_or_404(slug=slug)
    form = PostForm(obj=post)
    return render_template(
        'edit_post.html',
        form=form,
    )

@app.route('/admin/post/<path:slug>', methods=['POST'])
@app.route('/admin/post/new', methods=['POST'], defaults={'slug': 'new'})
@login_required
def save_post(slug):
    if slug == 'new':
        post = Post()
    else:
        post = Post.objects.get_or_404(slug=slug)

    form = PostForm(request.form)
    if not form.validate():
        return render_template(
            'edit_post.html',
            form=form,
        )

    if 'save' in request.form and post.published:
        # decrement tagcloud count on all tags in the
        # previous version of the Post
        TagCloud.objects(tag__in=post.tags).update(inc__count=-1)

    for field in form:
        setattr(post, field.name, field.data)
    if 'save' in request.form:
        post.slug = slug_for(title=post.title, pubdate=post.pubdate)
        post.save()

    if 'preview' in request.form:
        # form is validated, so errors will be highlighted
        return render_template(
            'edit_post.html',
            form=form,
            preview=True,
            post=post,
        )

    if post.published:
        # then increment tagcloud count on all tags in
        # the current version of the Post
        TagCloud.objects(tag__in=post.tags).update(inc__count=1)

    return redirect(url_for('dashboard'))

@app.route('/admin/getslug')
@login_required
def slug_for(title=None, pubdate=None):
    if title is None:
        title = request.args.get('title')
    if pubdate is None:
        pubdate = request.args.get('pubdate')

    if title is None or pubdate is None:
        return ''

    if isinstance(pubdate, basestring):
        pubdate = datetime.strptime(pubdate, '%Y-%m-%d')

    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
    title = unicode(re.sub('[^\w\s-]', '', title).strip().lower())
    title = re.sub('[\s]+', '-', title)

    return '%4d/%02d/%02d/%s' % (pubdate.year, pubdate.month, pubdate.day, title)

@app.route('/admin/user', methods=['GET'])
@login_required
def edit_user():
    user = User.objects.get_or_404(pk=session['user_id'])
    form = EditUserForm(obj=user)
    return render_template(
        'edit_user.html',
        form=form,
    )

@app.route('/admin/user', methods=['POST'])
@login_required
def save_user():
    user = User.objects.get_or_404(pk=session['user_id'])
    form = EditUserForm(formdata=request.form, obj=user)
    if not form.validate():
        return render_template(
            'edit_user.html',
            form=form,
        )

    for field in form:
        if field.name not in ('password', 'confirm'):
            setattr(user, field.name, field.data)
        elif field.name == 'password':
            user.set_password(field.data)

    user.save()
    return redirect(url_for('dashboard'))

