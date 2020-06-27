#!/bin/bash

# author: Emerson Barea (emerson.barea@gmail.com)

if [ "$1" == "--help" ] || [ "$1" == "-h" ] ; then
  printf "\nInvoke without any parameter for complete and unguided installation of MiniSecBGP and its dependencies.\n\n"
	exit 0
fi

if [ "$1" != "" ] ; then
	printf "\nWrong parameter '$1'.\nInvoke without any parameter for complete and unguided installation of MiniSecBGP and its dependencies.\n\n"
	exit 0
fi

welcome() {
	printf "\nMiniSecBGP 1.0 installer\n
	This script install MiniSecBGP 1.0 and all requirements to the home directory of \"minisecbgpuser\" user on Ubuntu Server 18.04 LTS
	It will automatically remove existing \"minisecbgpuser\" user and erase all data in '/home/minisecbgpuser' directory

	Execute 'install.sh -h' or 'install.sh --help' to help\n

	This installer will now configure:
	  - erase and recreate \"minisecbgpuser\" user and home directory (username = \"minisecbgpuser\" | password = <current user password>)
	  - configure user \"minisecbgpuser\" in sudoers

	This installer will now install:
	  - upgrade Operational System
	  - install MiniSecBGP requirements
	    - Containernet 2.2.1
	    - Metis 5.1
	    - Pyro 4
	    - MaxiNet 1.2
 	  - install MiniSecBGP application

	Obs.: thank you MaxiNet install program (https://raw.githubusercontent.com/MaxiNet/MaxiNet/master/installer.sh)\n\n"

	read -n1 -r -p "Press ANY key to continue or CTRL+C to abort." abort
}


network_address() {
        if [ "${#IP_ARRAY[@]}" -gt 1 ] ; then
          printf '\n\n%s\n' 'This computer has '${#IP_ARRAY[@]}' IP addresses configured on network interfaces:'
          for ip in "${IP_ARRAY[@]}"
          do
            printf '\n- %s' $ip
          done
          printf '\n\n%s' 'Choose which IP address should be used to communicate with other cluster nodes: (Ex.: '${IP_ARRAY[0]}'): '

          read temp_ip

          for i in "${IP_ARRAY[@]}"
          do
            if [ "$temp_ip" == "$i" ]; then
              var_ip="$temp_ip"
            fi
          done

          if ! [[ "$var_ip" ]] ; then
            printf '\e[1;31m%-6s\e[m\n' 'error: Choose and write only one of the valid IP addresses from the list above. (Ex.: '${IP_ARRAY[0]}')'
            network_address;
          fi
        else
          var_ip="${IP_ARRAY[0]}"
        fi
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


#configure_hosts() {
#        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Linux hosts File ...'
#        sudo sed --i '/MiniSecBGP_master/d' /etc/hosts | sudo tee --append /etc/hosts
#        echo "$var_ip MiniSecBGP_master" | sudo tee --append /etc/hosts
#}


install_Linux_reqs() {
        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Linux prerequisites ...'
        sudo apt install git aptitude whois sshpass nginx uwsgi python3-pip python3-venv postgresql postgresql-contrib postgresql-server-dev-all ansible -y;
        printf '\n\e[1;32m%-6s\n\n%s\n%s\n%s\n%s\n%s\n\n%s\n\n\e[m' \
               'The following programs have been installed:' '    - Nginx' '    - uWsgi' '    - Python3' '    - Postgresql'
}


virtualenv() {
        printf '\n\e[1;33m%-6s\e[m\n' '-- Creating Python Virtualenv ...'
        deactivate &> /dev/null
        rm -rf "$LOCAL_HOME"/venv
        python3 -m venv "$LOCAL_HOME"/venv
        source "$LOCAL_HOME"/venv/bin/activate
}


install_Python_reqs() {
        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Python prerequisites ...'
        pip3 install --upgrade --force-reinstall -U wheel
        pip3 install -r "$LOCAL_HOME"/requirements.txt;
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
        source "$LOCAL_HOME"/venv/bin/activate
        pip3 install -e .
        rm "$LOCAL_HOME"/minisecbgp/alembic/versions/*.py &> /dev/null
        alembic -c minisecbgp.ini revision --autogenerate -m "init"
        alembic -c minisecbgp.ini upgrade head

        MiniSecBGP_initialize_db --config-file="$LOCAL_HOME"/minisecbgp.ini --master-ip-address="$var_ip"

        printf '\n\e[1;33m%-6s\e[m\n' '-- Installing Sample Topologies ...'
        cp "$LOCAL_HOME"/minisecbgp/static/topology/20191201.as-rel2.txt.bz2 /tmp/
        MiniSecBGP_realistic_topology --config-file="$LOCAL_HOME"/minisecbgp.ini --file='20191201.as-rel2.txt.bz2'
        cp "$LOCAL_HOME"/minisecbgp/static/topology/Minimal-Topology-Example.MiniSecBGP /tmp/
        MiniSecBGP_manual_topology --file='/tmp/Minimal-Topology-Example.MiniSecBGP'
        cp "$LOCAL_HOME"/minisecbgp/static/topology/manual_topology1.MiniSecBGP /tmp/
        MiniSecBGP_manual_topology --file='/tmp/manual_topology1.MiniSecBGP'
        cp "$LOCAL_HOME"/minisecbgp/static/topology/manual_topology2.MiniSecBGP /tmp/
        MiniSecBGP_manual_topology --file='/tmp/manual_topology2.MiniSecBGP'
        cp "$LOCAL_HOME"/minisecbgp/static/topology/manual_topology3.MiniSecBGP /tmp/
        MiniSecBGP_manual_topology --file='/tmp/manual_topology3.MiniSecBGP'

        printf '\n\e[1;33m%-6s\e[m\n' '-- Configuring MiniSecBGP Application ...'
        MiniSecBGP_tests --config-file=minisecbgp.ini --execution-type='manual' --target-ip-address=$var_ip --username=$WHOAMI --password=$PASSWORD

	      printf '%s%s%s%s%s%s%s%s%s\n' $'# Start job every 1 minute (monitor '$HOSTNAME')
* * * * * minisecbgpuser '$LOCAL_HOME'/venv/bin/MiniSecBGP_tests --config-file='$LOCAL_HOME'/minisecbgp.ini --execution-type="scheduled" --hostname="'$HOSTNAME'" --username="" --password=""' | sudo tee /etc/cron.d/minisecbgp_tests_$HOSTNAME

	      printf '%s%s%s%s%s%s%s%s%s\n' $'# Scheduled realistic topology update (verify every day if today is the day for update)
0 3 * * * minisecbgpuser '$LOCAL_HOME'/venv/bin/MiniSecBGP_realistic_topology_scheduled_download --config-file='$LOCAL_HOME'/minisecbgp.ini --topology-path='$LOCAL_HOME'/' | sudo tee /etc/cron.d/minisecbgp_realistic_topology_scheduled_download

	      MiniSecBGP_config --config-file=minisecbgp.ini --target-ip-address=$var_ip --username=$WHOAMI --password=$PASSWORD
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
WorkingDirectory=' $LOCAL_HOME '
ExecStart=' $LOCAL_HOME '/venv/bin/uwsgi --ini-paste-logged ' $LOCAL_HOME '/minisecbgp.ini
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
        server_name [::]:80 default_server;
        access_log ' $LOCAL_HOME '/access.log;
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
	sudo rm /etc/nginx/sites-enabled/default &> /dev/null
	sudo rm /etc/nginx/sites-available/default &> /dev/null
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
IP_ADDRESSES=$(hostname --all-ip-addresses || hostname -I)
IP_ARRAY=($IP_ADDRESSES)
WHOAMI=$(whoami)
LOCAL_HOME=$(pwd)
PROJECT_NAME=MiniSecBGP

welcome;
network_address;
update;
#configure_hosts;
install_Linux_reqs;
virtualenv;
install_Python_reqs;
configure_Postgres;
install_app;
configure_uwsgi;
configure_nginx;
restart_services;
