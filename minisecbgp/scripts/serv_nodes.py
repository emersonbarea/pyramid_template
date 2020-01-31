import argparse
import sys
import os

from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.exc import OperationalError

from minisecbgp.scripts import ping, ssh
from minisecbgp import models


def service_ping(dbsession, argv):
    # argv[2] --> argv[0] = hostname
    if argv[0]:
        node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
        entry = ping.ping(argv[0])
        if entry == 0:
            node.serv_ping = 0
        else:
            node.serv_ping = 1
        try:
            dbsession.flush()
        except Exception as error:
            print('Database error for ping service verification on node: %s - %s' % node.node, error)
    else:
        nodes = dbsession.query(models.Node).all()
        for node in nodes:
            entry = ping.ping(node.node)
            if entry == 0:
                node.serv_ping = 0
            else:
                node.serv_ping = 1
            try:
                dbsession.flush()
            except Exception as error:
                print('Database error for ping service verification on node: %s - %s' % node.node, error)


def service_ssh(dbsession, argv):
    # argv[2] --> argv[0] = hostname
    # argv[3] --> argv[1] = username
    # argv[4] --> argv[2] = password
    # argv[5] --> argv[3] = command
    if argv[0]:
        node = dbsession.query(models.Node).filter(models.Node.node == argv[0]).first()
        entry = ssh.ssh(argv[0], argv[1], argv[2], argv[3])
        if entry[0] == 0:
            node.serv_ssh = 0
            node.serv_ssh_status = ''
        else:
            node.serv_ssh = 1
            node.serv_ssh_status = str(entry[2])
        try:
            dbsession.flush()
        except Exception as error:
            print('Database error for ssh service verification on node: %s - %s' % node.node, error)
    else:
        nodes = dbsession.query(models.Node).all()
        for node in nodes:
            entry = ssh.ssh(argv[0], argv[1], argv[2], argv[3])
            if entry[0] == 0:
                node.serv_ssh = 0
                node.serv_ssh_status = ''
            else:
                node.serv_ssh = 1
                node.serv_ssh_status = str(entry[2])
            try:
                dbsession.flush()
            except Exception as error:
                print('Database error for ssh service verification on node: %s - %s' % node.node, error)


def create_remote_user(dbsession, argv):
    # argv[2] --> argv[0] = hostname
    # argv[3] --> argv[1] = username
    # argv[4] --> argv[2] = password
    # argv[5] --> argv[3] = command
    argv[3] = 'echo %s | sudo -S apt install whois -y;' \
              'sudo userdel -r minisecbgpuser 2> /dev/null;' \
              'sudo useradd -m -p $(mkpasswd -m sha-512 -S saltsalt -s <<< %s) -s /bin/bash minisecbgpuser;' \
              'echo "minisecbgpuser    ALL=NOPASSWD: ALL" | sudo tee --append /etc/sudoers;' \
              'sudo -u minisecbgpuser ssh-keygen -t rsa -N "" -f /home/minisecbgpuser/.ssh/id_rsa' % (argv[2], argv[2])
    service_ssh(dbsession, argv)



def install_minisecbgp(dbsession, argv):
    # argv[2] --> argv[0] = hostname
    # argv[3] --> argv[1] = username
    # argv[4] --> argv[2] = password
    os.system('sshpass -p "%s" scp -o StrictHostKeyChecking=no ./minisecbgp/scripts/MiniSecBGP/install.sh '
              '%s@%s:/home/%s' % (argv[2], argv[1], argv[0], argv[1]))


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
    # argv[2] --> argv[0] = hostname
    # argv[3] --> argv[1] = username
    # argv[4] --> argv[2] = password
    # argv[5] --> argv[3] = command

    args = parse_args(argv[0:2])
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)
    try:
        with env['request'].tm:
            dbsession = env['request'].dbsession
            service_ping(dbsession, argv[2:])
            service_ssh(dbsession, argv[2:])
            create_remote_user(dbsession, argv[2:])
            #install_minisecbgp(dbsession, argv[2:])
    except OperationalError:
        print('Database error')
