#!/bin/bash

# author: Emerson Barea (emerson.barea@gmail.com)

welcome() {
        printf '\n%s\n' 'This script installs and configures all MiniSecBGP environment.
                   Some requirements must be met:
                   - Ubuntu 18 Server LTS (Bionic Beaver)
                   - Internet access
                   - "sudo" user'
}

update() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Updating Linux ...'
        printf '[sudo] senha para '$WHOAMI':'
        read -s PASSWORD
        echo "$PASSWORD" | sudo -S apt update;
        sudo apt upgrade -y;
        sudo apt -f install -y;
        sudo apt autoremove -y;

}

install_Linux_reqs() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Linux prerequisites ...'
        sudo apt install sshpass nginx uwsgi python3-pip python3-venv postgresql postgresql-contrib postgresql-server-dev-all -y;
        printf '\n\e[1;32m%-6s\n\n%s\n%s\n%s\n%s\n%s\n\n%s\n\n\e[m' \
               'The following programs have been installed:' '    - Nginx' '    - uWsgi' '    - Python3 pip' '    - Python3 venv' '    - Postgresql'

}

create_user() {
        printf '\n\e[1;33m%-6s\e[m\n' '-- Creating "minisecbgpuser" user...'
        sudo userdel -r minisecbgpuser 2> /dev/null
        sudo useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< $PASSWORD) -s /bin/bash minisecbgpuser
        printf '%s\n' 'minisecbgpuser     ALL=NOPASSWD: ALL' | sudo tee --append /etc/sudoers
        sudo -u minisecbgpuser ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa
        sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/id_rsa.pub | \
        sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys
        sudo -u minisecbgpuser chmod 755 /home/minisecbgpuser/.ssh/authorized_keys

}

virtualenv() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Creating Python 3 Virtualenv ...'
        deactivate &> /dev/null
        rm -rf "$BUILD_DIR"/venv
        python3 -m venv "$BUILD_DIR"/venv
        source "$BUILD_DIR"/venv/bin/activate

}

install_Python_reqs() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Python 3 prerequisites ...'
        pip3 install wheel
        pip3 install -r requirements.txt;
}

configure_Postgres() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Configuring Postgres ...'

        sudo -u postgres psql -c "DROP EXTENSION adminpack;" &> /dev/null
        sudo -u postgres psql -c "REVOKE CONNECT ON DATABASE "dbminisecbgp" FROM public;" &> /dev/null
        sudo -u postgres psql -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'dbminisecbgp';" &> /dev/null
        sudo -u postgres dropdb dbminisecbgp &> /dev/null
        sudo -u postgres psql -c "DROP USER minisecbgp;" &> /dev/null

        sudo -u postgres psql -U postgres -d postgres -c "alter user postgres with password 'postgres';"
        sudo -u postgres psql -c "CREATE EXTENSION adminpack;"
        sudo -u postgres psql -c "CREATE USER minisecbgp WITH ENCRYPTED PASSWORD 'minisecbgp';"
        sudo -u postgres createdb -O minisecbgp dbminisecbgp

}

install_app() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing MiniSecBGP Application ...'
        pip3 install -e .
        rm $BUILD_DIR/minisecbgp/alembic/versions/*.py &> /dev/null
        alembic -c minisecbgp.ini revision --autogenerate -m "init"
        alembic -c minisecbgp.ini upgrade head
        initialize_minisecbgp_db minisecbgp.ini
        serv_nodes minisecbgp.ini lpttch '' '' '' ''
        pytest

}

configure_uwsgi() {

        printf '\n\e[1;33m%-6s\e[m\n' '-- Configuring uWSGI deamon ...'
        printf '%s%s%s%s%s%s%s%s%s\n' \
'[Unit]
Description=uwsgi daemon
After=network.target

[Service]
User=' $WHOAMI '
Group=www-data
WorkingDirectory=' $BUILD_DIR '
ExecStart=' $BUILD_DIR '/venv/bin/uwsgi --ini-paste-logged ' $BUILD_DIR '/minisecbgp.ini

[Install]
WantedBy=multi-user.target' | sudo tee /etc/systemd/system/uwsgi.service

}

configure_nginx() {

        printf '\n\e[1;33m%-6s\e[m\n' 'Configuring Nginx...'
        printf '%s%s%s%s%s%s%s%s%s\n' \
'upstream ' $PROJECT_NAME ' {
        server unix:///tmp/MiniSecBGP.sock;
}

server {
        listen 80;
        server_name ' $IP_ADDRESSES ';
        access_log ' $BUILD_DIR '/access.log;
        location / {
                proxy_set_header        Host $http_host;
                proxy_set_header        X-Real-IP $remote_addr;
                proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header        X-Forwarded-Proto $scheme;
                client_max_body_size    10m;
                client_body_buffer_size 128k;
                proxy_connect_timeout   60s;
                proxy_send_timeout      90s;
                proxy_read_timeout      90s;
                proxy_buffering         off;
                proxy_temp_file_write_size 64k;
                proxy_pass http://' $PROJECT_NAME ';
                proxy_redirect          off;
        }
}' | sudo tee /etc/nginx/sites-available/$PROJECT_NAME

        sudo rm /etc/nginx/sites-enabled/$PROJECT_NAME &> /dev/null
        sudo ln -s /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled
        sudo nginx -t

}

restart_services() {

        printf '\n\e[1;33m%-6s\e[m\n' 'Restarting all services...'
        sudo systemctl daemon-reload
        sudo systemctl restart uwsgi
        sudo systemctl enable uwsgi
        sudo systemctl restart nginx

}


HOSTNAME=$(hostname)
PROJECT_NAME=MiniSecBGP
BUILD_DIR=$(pwd)
IP_ADDRESSES=$(hostname --all-ip-addresses || hostname -I)
IP_ADDRESSES_EDITED=$(echo $IP_ADDRESSES | sed "s/ /', '/g")
WHOAMI=$(whoami)

welcome;
update;
install_Linux_reqs;
virtualenv;
install_Python_reqs;
configure_Postgres;
install_app;
configure_uwsgi;
configure_nginx;
restart_services;
