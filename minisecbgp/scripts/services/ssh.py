import paramiko


def ssh(node, username, password, command):
    try:
        client_ssh = paramiko.SSHClient()
        client_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client_ssh.connect(node, username=username, password=password, timeout=15)
        result = client_ssh.get_transport().open_session()
        result.exec_command(command)

        serv_ssh = 0
        serv_ssh_status = None
        if str(result.recv_exit_status()) != '1':               # 0 = command successful | 1 = command error
            command_result = '0'
        else:
            command_result = str(result.recv_exit_status())
        command_result_error = str(result.recv_stderr(200))     # info or error resultant from command

        return serv_ssh, serv_ssh_status, command_result, command_result_error
    except Exception as error:
        serv_ssh = 1
        serv_ssh_status = str(error)[:240]
        command_result = 2
        command_result_error = None

        return serv_ssh, serv_ssh_status, command_result, command_result_error
    finally:
        client_ssh.close()
