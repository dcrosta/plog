from os.path import dirname, join
from setuptools import setup, find_packages

README = file(join(dirname(__file__), 'README.md')).read()

# use pip install -r requirements.txt instead
requires = [
    'apesmit',
    'Flask',
    'Flask-MongoEngine',
    'markdown2',
    'py-bcrypt',
    'pygments',
    'pytz',
]

setup(
    name='plog',
    version='0.1',
    url='https://github.com/dcrosta/plog',
    license='BSD',
    author='Dan Crosta',
    author_email='dcrosta@late.am',
    description='Single-user blog using Flask, Mongoengine, and MongoDB',
    long_description=README,
    packages=find_packages(),
    test_suite='tests',
    zip_safe=False,
    platforms='any',
    install_requires=requires,
    tests_require=requires,
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    dependency_links=[
        'https://github.com/sbook/flask-mongoengine/tarball/master#egg=Flask-MongoEngine',
        'http://www.florian-diesch.de/software/apesmit/dist/apesmit-0.01.tar.gz',
    ],
)
