import argparse
import sys
import os
import subprocess

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp.scripts.services import ssh, execute_command
from minisecbgp import models


def create_minisecbgpuser(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password
    # argv[6] --> argv[3] = command
    argv[3] = 'echo %s | sudo -S apt install whois -y;' \
              'sudo userdel -r minisecbgpuser 2> /dev/null;' \
              'sudo useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< %s) -s /bin/bash minisecbgpuser;' \
              'echo "minisecbgpuser    ALL=NOPASSWD: ALL" | sudo tee --append /etc/sudoers;' \
              'echo "%s    ALL=(minisecbgpuser) NOPASSWD: ALL" | sudo tee --append /etc/sudoers' \
              % (argv[2], argv[2], argv[1])
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        discard, discard, node.conf_user, node.conf_user_status = ssh.ssh(argv[0], argv[1], argv[2], argv[3])
        dbsession.flush()
    except Exception as error:
        print('Database error for ssh service verification on node: %s - %s' % node.node, error)


def configure_ssh(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password
    # argv[6] --> argv[3] = command
    argv[3] = 'sudo -u minisecbgpuser ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa;' \
              'sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/id_rsa.pub | ' \
              'sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys;' \
              'sudo -u minisecbgpuser chmod 755 /home/minisecbgpuser/.ssh/authorized_keys;' \
              'echo -e "Host *\nStrictHostKeyChecking no" | sudo -u minisecbgpuser tee --append ' \
              '/home/minisecbgpuser/.ssh/config;' \
              'sudo -u minisecbgpuser chmod 400 /home/minisecbgpuser/.ssh/config'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        ssh.ssh(argv[0], argv[1], argv[2], argv[3])
        conf_ssh_status = ''
        # update of the authorized_keys file to allow remote connections via ssh of the user "minisecbgpuser" without
        # the need for a password
        if node.master == 0:
            command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                      'minisecbgpuser@%s:/home/minisecbgpuser/.ssh/authorized_keys ' \
                      '/home/minisecbgpuser/.ssh/authorized_keys.tmp' % (argv[2], argv[0])
            result = execute_command.execute_command(command)
            conf_ssh_status = str(result[2].decode()[:55])

            command = 'sudo -u minisecbgpuser cat /home/minisecbgpuser/.ssh/authorized_keys.tmp |' \
                      'sudo -u minisecbgpuser tee --append /home/minisecbgpuser/.ssh/authorized_keys'
            result = execute_command.execute_command(command)
            conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

            command = 'sudo -u minisecbgpuser sshpass -p "%s" scp -o StrictHostKeyChecking=no ' \
                      '/home/minisecbgpuser/.ssh/authorized_keys minisecbgpuser@%s:/home/minisecbgpuser/.ssh/' \
                      % (argv[2], argv[0])
            result = execute_command.execute_command(command)
            conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

        # testing ssh connection
        command = 'sudo -u minisecbgpuser ssh %s exit' % argv[0]
        result = execute_command.execute_command(command)
        conf_ssh_status = conf_ssh_status + str(result[2].decode()[:55])

        node.conf_ssh = result[0]
        node.conf_ssh_status = conf_ssh_status

        dbsession.flush()
    except Exception as error:
        print('Database error for ssh service verification on node: %s - %s' % (node.node, error))


def install_mininet(dbsession, argv):
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password
    argv[3] = 'git clone git://github.com/mininet/mininet /home/minisecbgpuser/mininet;' \
              'cd /home/minisecbgpuser/mininet;' \
              'git checkout -b 2.3.0d4 2.3.0d4;' \
              'sed -i -- "s/iproute /iproute2 /g" /home/minisecbgpuser/mininet/util/install.sh;' \
              'sudo /home/minisecbgpuser/mininet/util/install.sh -a'
    node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
    try:
        bla, ble, node.conf_mininet, node.conf_mininet_status = ssh.ssh(argv[0], 'minisecbgpuser', argv[2], argv[3])
        print(bla, ble, node.conf_mininet, node.conf_mininet_status)
        dbsession.flush()
    except Exception as error:
        print('Database error for Mininet installation on node: %s - %s' % node.node, error)


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., minisecbgp.ini',
    )
    return parser.parse_args(argv[1:])


def main(argv=sys.argv):
    # argv[0] = python program
    # argv[1] = configuration file .ini
    # argv[2] = 0 = creating node | 1 = job scheduled
    # argv[3] --> argv[0] = hostname
    # argv[4] --> argv[1] = username
    # argv[5] --> argv[2] = password
    # argv[6] --> argv[3] = command

    args = parse_args(argv[0:2])
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            if argv[2] == '0':
                create_minisecbgpuser(dbsession, argv[3:])
                configure_ssh(dbsession, argv[3:])
                install_mininet(dbsession, argv[3:])
    except OperationalError:
        print('Database error')
