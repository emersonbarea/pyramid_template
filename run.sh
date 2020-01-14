#!/bin/bash

pip install -e ".[testing]"
pserve development.ini --reload

