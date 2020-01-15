#!/bin/bash

sudo apt update
sudo apt upgrade -y
sudo apt -f install -y
sudo apt autoremove -y

sudo apt install python3-pip postgresql postgresql-contrib postgresql-server-dev-all -y

sudo pip install -r requirements.txt
