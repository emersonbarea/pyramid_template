#!/bin/bash

# author: Emerson Barea (emerson.barea@gmail.com)

welcome() {
        printf '\n%s\n' 'This script installs and configures all MiniSecBGP environment.
                   Some requirements must be met:
                   - Ubuntu 18 Server LTS (Bionic Beaver)
                   - Internet access
                   - "sudo" user
                   Note: the user "minisecbgp" will be created, so it should not exist previously.'
}

update() {

        printf '\n\e[1;32m%-6s\e[m\n' '-- Updating Linux ...'
        sudo apt update;
        sudo apt upgrade -y;
        sudo apt -f install -y;
        sudo apt autoremove -y;

}

install_Linux_reqs() {

        printf '\n\e[1;32m%-6s\e[m\n' '-- Installing Linux prerequisites ...'
        sudo apt install python3-pip python3-venv postgresql postgresql-contrib postgresql-server-dev-all -y;

}

virtualenv() {

        printf '\n\e[1;32m%-6s\e[m\n' '-- Creating Python3 Virtualenv ...'
        python3 -m venv $BUILD_DIR/venv
        source $BUILD_DIR/venv/bin/activate

}

install_Python_reqs() {

        printf '\n\e[1;32m%-6s\e[m\n' '-- Installing Python prerequisites ...'
        pip3 install wheel
        pip3 install -r requirements.txt;
}

configure_Postgres() {

        printf '\n\e[1;32m%-6s\e[m\n' '-- Configuring Postgres ...'
        sudo -u postgres psql -U postgres -d postgres -c "alter user postgres with password 'postgres';"
        sudo -u postgres psql -c "CREATE EXTENSION adminpack;"
        sudo -u postgres psql -c "CREATE USER minisecbgp WITH ENCRYPTED PASSWORD 'minisecbgp';"
        sudo -u postgres createdb -O minisecbgp dbMinisecbgp

}

BUILD_DIR=$(pwd)

welcome;
update;
install_Linux_reqs;
virtualenv;
install_Python_reqs;
configure_Postgres;
