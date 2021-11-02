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
            'MiniSecBGP_initialize_db = minisecbgp.scripts.initialize_db:main',
            'MiniSecBGP_realistic_topology_scheduled_download = minisecbgp.scripts.realistic_topology_scheduled_download:main',
            'MiniSecBGP_node_create = minisecbgp.scripts.node_create:main',
            'MiniSecBGP_node_service = minisecbgp.scripts.node_service:main',
            'MiniSecBGP_node_configuration = minisecbgp.scripts.node_configuration:main',
            'MiniSecBGP_node_install = minisecbgp.scripts.node_install:main',
            'MiniSecBGP_realistic_topology = minisecbgp.scripts.realistic_topology:main',
            'MiniSecBGP_delete_topology = minisecbgp.scripts.delete_topology:main',
            'MiniSecBGP_duplicate_topology = minisecbgp.scripts.duplicate_topology:main',
            'MiniSecBGP_manual_topology = minisecbgp.scripts.manual_topology:main',
            'MiniSecBGP_bgplay_topology = minisecbgp.scripts.bgplay_topology:main',
            'MiniSecBGP_hijack_realistic_analysis = minisecbgp.scripts.hijack_realistic_analysis:main',
            'MiniSecBGP_hijack_attack_scenario = minisecbgp.scripts.hijack_attack_scenario:main',
            'MiniSecBGP_hijack_events_restrictive_mode = minisecbgp.scripts.hijack_events_restrictive_mode:main',
            'MiniSecBGP_hijack_events_permissive_mode = minisecbgp.scripts.hijack_events_permissive_mode:main'
        ],
    },
)
