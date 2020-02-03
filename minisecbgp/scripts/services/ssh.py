import paramiko


def ssh(node, username, password, command):
    try:
        client_ssh = paramiko.SSHClient()
        client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client_ssh.connect(node, username=username, password=password, timeout=15)
        stdin, stdout, stderr = client_ssh.exec_command(command)

        service_ssh = 0
        out_ssh = stdout.read()
        command_error = stderr.read()

        return service_ssh, out_ssh, command_error
    except Exception as error:
        service_ssh = 1
        return service_ssh, None, error
    finally:
        client_ssh.close()
