import socket
import paramiko


def ssh(request, node, username, password, command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node, username=username, password=password, timeout=15)
        stdin, stdout, stderr = ssh.exec_command(command)
    except paramiko.ssh_exception.AuthenticationException as e:
        return e
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        return e
    except socket.error as e:
        return e
    except Exception as e:
        return e

    finally:
        ssh.close()

