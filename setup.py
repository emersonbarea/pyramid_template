import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

# List of dependencies installed via `pip install -e .`
# by virtue of the Setuptools `install_requires` value below.
requires = [
    'pyramid',
    'pyramid_jinja2',
    'bcrypt',
    'docutils',
    'alembic',
    'pyramid_tm',
    'pyramid_retry',
    #'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'psycopg2',
    'wtforms',
    'waitress',
    'sqlalchemy'
]

tests_require = [
    'WebTest >= 1.3.1',
    'pytest >= 3.7.4',
    'pytest-cov',
]

# List of dependencies installed via `pip install -e ".[dev]"`
# by virtue of the Setuptools `extras_require` value in the Python
# dictionary below.
dev_requires = [
    'pyramid_debugtoolbar',
    'pytest',
    'webtest',
]

setup(
    name='MiniSecBGP',
    version='0.1',
    description='A Lightweight and Distributed Testbed for Security Analysis in BGP',
    long_description=README + '\n\n' + CHANGES,
    install_requires=requires,
    author='Emerson Barea',
    author_email='emerson.barea@gmail.com',
    url='https://github.com/MiniSecBGP/MiniSecBGP',
    keywords='BGP Testbed Security',

    extras_require={
        'dev': dev_requires,
        'testing': tests_require,
    },

    entry_points={
        'paste.app_factory': [
            'main = minisecbgp:main'
        ],
        'console_scripts': [
            'initialize_minisecbgp_db = minisecbgp.scripts.initialize_db:main',
            'initialize_CAIDA_AS_Relationship = minisecbgp.scripts.initialize_CAIDA_AS_Relationship:main',
            'tests = minisecbgp.scripts.tests:main',
            'validate_hostname = minisecbgp.scripts.validate_hostname:main',
            'config = minisecbgp.scripts.config:main',
            'realistic_topology_scheduled_download = minisecbgp.scripts.realistic_topology_scheduled_download:main'
        ],
    },
)
