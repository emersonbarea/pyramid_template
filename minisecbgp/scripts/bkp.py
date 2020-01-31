import paramiko

from minisecbgp import models


def ssh(request, node, username, password, command):
    try:

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node, username=username, password=password, timeout=15)
        stdin, stdout, stderr = ssh.exec_command(command)

        # update SSH service status ("OK")
        try:
            entry = request.dbsession.query(models.Cluster).filter_by(node=node).first()
            entry.serv_ssh = 0
            request.dbsession.flush()
        except:
            pass
    except:

        # update SSH service status ("ERROR")
        try:
            entry = request.dbsession.query(models.Cluster).filter_by(node=node).first()
            entry.serv_ssh = 1
            request.dbsession.flush()
        except:
            pass

    finally:
        ssh.close()
