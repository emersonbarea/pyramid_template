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
	sudo apt update;
	sudo apt upgrade -y;
	sudo apt -f install -y;
	sudo apt autoremove -y;
}

install_Linux_reqs() {
	sudo apt install python3-pip postgresql postgresql-contrib postgresql-server-dev-all -y;
}

install_Python_reqs() {
	sudo pip3 install -r requirements.txt;
}


main() {

	BUILD_DIR=$(pwd)

	welcome;
	update;
	install_Linux_reqs;
	install_Python_reqs;

}
