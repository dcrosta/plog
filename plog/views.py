from datetime import datetime, timedelta
from pytz import timezone, utc
import re
import unicodedata

from flask import abort, flash, make_response, redirect, render_template, request, session, url_for
from gridfs import GridFS
from werkzeug.contrib.atom import AtomFeed
from werkzeug.wsgi import wrap_file

from plog import app, db
from plog.models import *
from plog.auth import *
from plog.filters import domarkdown
from plog.utils import *

eastern = timezone('US/Eastern')
uploads = GridFS(db)

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

@app.route('/tag/<tag>/feed')
@app.route('/feed', defaults={'tag': None})
def feed(tag):
    if tag and not TagCloud.objects(tag=tag, count__gt=0).first():
        return abort(404)

    title = 'late.am'
    if tag:
        title = '%s - Posts about %s' % (title, tag)

    feed = AtomFeed(
        title=title,
        feed_url=url_for('feed', _external=True),
        url=url_for('index', _external=True),
        author={'name': 'Dan Crosta', 'email': 'dcrosta@late.am'},
        icon=url_for('static', filename='mug.png', _external=True),
        generator=('plog', 'https://github.com/dcrosta/plog', '0.1'),
    )

    posts = Post.objects(published=True).order_by('-pubdate')
    if tag:
        posts.filter(tags=tag)
    for post in posts[:20]:
        feed.add(
            title=post.title,
            content=domarkdown(post.blurb + '\n' + post.body),
            content_type='html',
            author={'name': 'Dan Crosta', 'email': 'dcrosta@late.am'},
            url=url_for('post', slug=post.slug, _external=True),
            id=url_for('permalink', post_id=post.pk, _external=True),
            published=post.pubdate,
            updated=post.updated)

    response = make_response(unicode(feed))
    response.headers['Content-Type'] = 'application/atom+xml; charset=UTF-8'
    return response

@app.route('/sitemap.xml')
def sitemap():
    sitemap = render_template(
        'sitemap.xml',
        root_url=url_for('index', _external=True),
        posts=Post.objects(published=True),
        tags=TagCloud.get(),
        now=datetime.utcnow(),
        min=min,
    )

    response = make_response(sitemap)
    response.headers['Content-Type'] = 'application/xml; charset=UTF-8'
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
    start = datetime(year=year, month=1, day=1, tzinfo=eastern)
    start = start.astimezone(utc).replace(tzinfo=None)
    end = datetime(year=year + 1, month=1, day=1, tzinfo=eastern)
    end = end.astimezone(utc).replace(tzinfo=None)
    return archive(start, end, '%Y')

@app.route('/post/<int:year>/<int:month>/')
def month_archive(year, month):
    start = datetime(year=year, month=month, day=1, tzinfo=eastern)
    start = start.astimezone(utc).replace(tzinfo=None)
    if month == 12:
        year += 1
        month = 0
    end = datetime(year=year, month=month + 1, day=1)
    return archive(start, end, '%B %Y')

@app.route('/post/<int:year>/<int:month>/<int:day>/')
def day_archive(year, month, day):
    start = datetime(year=year, month=month, day=day, tzinfo=eastern)
    start = start.astimezone(utc).replace(tzinfo=None)
    end = start + timedelta(days=1)
    return archive(start, end, '%B %d, %Y')

def archive(start, end, fmt):
    posts = Post.objects(published=True).order_by('-pubdate')
    if start and end:
        posts.filter(pubdate__gte=start, pubdate__lt=end)
    return render_template(
        'archive.html',
        posts=posts,
        cloud=TagCloud.get(),
        start=start,
        fmt=fmt,
    )

@app.route('/tag/<tag>')
def tag_archive(tag):
    if not TagCloud.objects(tag=tag, count__gt=0).first():
        return abort(404)
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
    post = get_or_404(Post, pk=post_id)
    return redirect(url_for('post', slug=post.slug))

@app.route('/uploads/<path:filename>')
def serve(filename):
    try:
        fileobj = uploads.get_last_version(filename=filename)
    except:
        # no such file
        abort(404)

    # mostly copied from flask/helpers.py, with
    # modifications for GridFS
    data = wrap_file(request.environ, fileobj, buffer_size=1024*256)
    response = app.response_class(
        data,
        mimetype=fileobj.content_type,
        direct_passthrough=True)
    response.content_length = fileobj.length
    response.last_modified = fileobj.upload_date
    response.set_etag(fileobj.md5)
    response.cache_control.max_age = 31536000
    response.cache_control.s_max_age = 31536000
    response.cache_control.public = True
    response.make_conditional(request)
    return response

@app.route('/post/<path:slug>', methods=['GET'])
def post(slug):
    post = get_or_404(Post, slug=slug, published=True)
    comment_count = sum(c.approved for c in post.comments)
    comment_form = CommentForm()
    return render_template(
        'post.html',
        post=post,
        cloud=TagCloud.get(),
        comment_form=comment_form,
        comment_count=comment_count,
    )

@app.route('/post/<path:slug>', methods=['POST'])
def comment(slug):
    post = get_or_404(Post, slug=slug, published=True)
    comment_form = CommentForm(request.form)
    if not comment_form.validate():
        return render_template(
            'post.html',
            post=post,
            cloud=TagCloud.get(),
            comment_form=comment_form,
            jump_to='comment',
        )

    post.update(push__comments=Comment(
        author=comment_form.author.data,
        email=comment_form.email.data,
        body=comment_form.body.data,
        approved=False))

    # commenter data might have changed
    commenter = comment_form.commenter
    if commenter is None:
        commenter = Commenter()
    if comment_form.author.data != commenter.author:
        commenter.author = comment_form.author.data
    if comment_form.email.data != commenter.email:
        commenter.email = comment_form.email.data
    commenter.save()

    flash('success', 'Your comment will appear once approved.')
    response = redirect(url_for('post', slug=slug))

    lifetime = timedelta(days=3650)
    response.set_cookie(
        'plogcmt', commenter.cookie,
        max_age=lifetime.seconds + lifetime.days * 24 * 3600,
        expires=datetime.utcnow() + lifetime,
        httponly=True)
    return response

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

    comments = []
    for post in posts:
        for i, comment in enumerate(post.comments):
            if not comment.approved:
                comment.index = i
                comment.post = post
                comments.append(comment)

    comments.sort(key=lambda c: c['when'], reverse=True)

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
    post = get_or_404(Post, slug=slug)
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
        post = get_or_404(Post, slug=slug)

    form = PostForm(request.form)
    if not form.validate():
        return render_template(
            'edit_post.html',
            form=form,
        )

    if 'save' in request.form and post.published:
        # decrement tagcloud count on all tags in the
        # previous version of the Post
        TagCloud.objects(tag__in=post.tags, count__gte=1).update(
            inc__count=-1, set__updated=datetime.utcnow())

    for field in form:
        setattr(post, field.name, field.data)

    if 'preview' in request.form:
        # form is validated, so errors will be highlighted
        return render_template(
            'edit_post.html',
            form=form,
            preview=True,
            post=post,
        )
    elif 'save' in request.form:
        post.slug = make_slug(post.title, post.pubdate)
        post.save()

    if 'save' in request.form and post.published:
        # then increment tagcloud count on all tags in
        # the current version of the Post
        for tag in post.tags:
            TagCloud.objects(tag=tag).update(
                inc__count=1, set__updated=datetime.utcnow(), upsert=True)

    images = form.images_to_add()
    if images:
        return redirect(url_for('add_images', slug=post.slug, files=','.join(images)))

    return redirect(url_for('dashboard'))

@app.route('/admin/post/<path:slug>/uploads', methods=['GET'])
def add_images(slug):
    get_or_404(Post, slug=slug)
    images = request.args.get('files').split(',')

    form = UploadsForm(images=images)
    return render_template(
        'upload.html',
        form=form,
    )

@app.route('/admin/post/<path:slug>/uploads', methods=['POST'])
def save_images(slug):
    get_or_404(Post, slug=slug)
    images = request.args.get('files').split(',')

    form = UploadsForm(images=images, formdata=request.form)
    if form.validate():
        for upload in form.uploads:
            filename = upload.filename.data
            fieldname = upload.file.name
            if fieldname in request.files:
                fileobj = request.files[fieldname]
                uploads.put(
                    fileobj.stream,
                    filename=filename,
                    content_type=fileobj.mimetype
                )

    return redirect(url_for('dashboard'))

@app.route('/admin/delete/<path:slug>')
@login_required
def delete_post(slug):
    Post.objects(slug=slug).delete()
    return redirect(url_for('dashboard'))

@app.route('/admin/post/<path:slug>/moderate/<int:index>', methods=['POST'])
@login_required
def moderate(slug, index):
    post = get_or_404(Post, slug=slug)
    if 'approve' in request.form:
        post.comments[index].approved = True
    else:
        del post.comments[index]
    post.save(set_updated=False)
    return redirect(url_for('dashboard'))

@app.route('/admin/getslug')
@login_required
def slug_for():
    title = request.args.get('title')
    pubdate = request.args.get('pubdate')

    if title is None or pubdate is None:
        return ''

    if isinstance(pubdate, basestring):
        pubdate = datetime.strptime(pubdate, '%Y-%m-%d %H:%M')

    pubdate = pubdate.replace(tzinfo=eastern).astimezone(utc)
    return make_slug(title, pubdate)

def make_slug(title, utc_pubdate):
    pubdate = utc_pubdate.replace(tzinfo=utc).astimezone(eastern)

    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
    title = unicode(re.sub(r'[^\w\s\\/-]', '', title).strip().lower())
    title = re.sub(r'[\s\\/-]+', '-', title)

    return '%4d/%02d/%02d/%s' % (pubdate.year, pubdate.month, pubdate.day, title)

@app.route('/admin/user', methods=['GET'])
@login_required
def edit_user():
    user = get_or_404(User, pk=session['user_id'])
    form = EditUserForm(obj=user)
    return render_template(
        'edit_user.html',
        form=form,
    )

@app.route('/admin/user', methods=['POST'])
@login_required
def save_user():
    user = get_or_404(User, pk=session['user_id'])
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

@app.route('/version/<version>')
def setversion(version):
    response = redirect(request.referrer)

    if version == 'desktop':
        lifetime = timedelta(days=365 * 10)
        response.set_cookie(
            'nomobile', 'true',
            max_age=lifetime.seconds + lifetime.days * 24 * 3600,
            expires= datetime.utcnow() + lifetime,
        )
    elif 'nomobile' in request.cookies:
        response.delete_cookie('nomobile')

    return response

@app.errorhandler(404)
@app.errorhandler(500)
def notfound(error):
    try:
        cloud = TagCloud.get()
    except:
        cloud = None

    errpage = render_template(
        'error.html',
        error=error,
        cloud=cloud,
    )

    return errpage, getattr(error, 'code', 500)

