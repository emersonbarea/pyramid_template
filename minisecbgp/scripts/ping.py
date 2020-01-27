import subprocess

from minisecbgp import models


def ping(request, node):
    result = subprocess.Popen(['ping', node, '-c', '1', "-W", "15"])
    result.wait()
    try:
        entry = request.dbsession.query(models.Cluster).filter_by(node=node).first()
        if result.poll() == 0:
            entry.serv_ping = 0
        else:
            entry.serv_ping = 1
        request.dbsession.flush()
    except:
        pass