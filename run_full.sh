#!/bin/bash

pip3 install -e ".[testing]"
alembic -c development.ini revision --autogenerate -m "init"
alembic -c development.ini upgrade head
initialize_minisecbgp_db development.ini
pytest
pserve development.ini --reload

