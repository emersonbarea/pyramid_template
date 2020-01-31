MiniSecBGP
==========

Getting Started
---------------

- Change directory into your newly created project.

    cd MiniSecBGP

- Install the project in editable mode with its testing requirements.

    env/bin/pip install -e ".[testing]"

- Initialize and upgrade the database using Alembic.

    - Generate your first revision.

        env/bin/alembic -c minisecbgp.ini revision --autogenerate -m "init"

    - Upgrade to that revision.

        env/bin/alembic -c minisecbgp.ini upgrade head

- Load default data into the database using a script.

    env/bin/initialize_minisecbgp_db minisecbgp.ini

- Run your project's tests.

    env/bin/test

- Run your project.

    env/bin/pserve minisecbgp.ini
