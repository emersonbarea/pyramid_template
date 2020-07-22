import ipaddress

import paramiko


def ssh(node, username, password, command):
    try:
        client_ssh = paramiko.SSHClient()
        client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client_ssh.connect(str(ipaddress.ip_address(node)),
                           username=username,
                           password=password,
                           timeout=15,
                           allow_agent=False,
                           look_for_keys=True)
        stdin, stdout, stderr = client_ssh.exec_command(command)
        service_ssh = 0
        service_ssh_status = ''
        command_output = stdout.read().decode('utf-8').replace('\n', '')
        command_error_warning = stderr.read().decode('utf-8').replace('\n', '')
        if stdout.channel.recv_exit_status() == 0:
            command_status = 0
        else:
            command_status = 1
        return service_ssh, service_ssh_status, command_output, command_error_warning, command_status
    except Exception as error:
        service_ssh = 1
        service_ssh_status = str(error)
        command_output = ''
        command_error_warning = ''
        command_status = 2
        return service_ssh, service_ssh_status, command_output, command_error_warning, command_status
    finally:
        client_ssh.close()
