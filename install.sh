#!/bin/bash

apt update
apt upgrade -y
apt -f install -y
apt autoremove -y

sudo apt install python3-pip postgresql postgresql-contrib postgresql-server-dev-all -y

pip install -r requirements.txt
