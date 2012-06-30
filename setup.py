"""
Plog
====

A single-user blog using Flask, Mongoengine, and MongoDB.


Installation
------------

Install the latest version with ``pip``:

.. code-block:: bash

    $ pip install plog

Or, for the adventurous:

.. code-block:: bash

    $ pip install https://github.com/dcrosta/plog/tarball/master#egg=plog-dev
"""
from setuptools import setup, find_packages

setup(
    name='plog',
    version='0.3',
    url='https://github.com/dcrosta/plog',
    license='BSD',
    author='Dan Crosta',
    author_email='dcrosta@late.am',
    description='Single-user blog using Flask, Mongoengine, and MongoDB',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        line.strip() for line in open('requirements.txt')
        if not line.strip().startswith('#')
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    entry_points={
        'pygments.lexers': [
            'keystone = plog.markup:KeystoneLexer',
        ],
        'console_scripts': [
            'plog-admin = plog.scripts:admin',
        ],
    },
)
