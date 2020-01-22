import paramiko
from paramiko import AuthenticationException
import socket


def ssh(node, username, password, command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command(command)
    except AuthenticationException:
        pass
    except socket.error as e:
        pass
    finally:
        ssh.close()
