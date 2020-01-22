import os

from minisecbgp import models


def ping(request, host):
    ping_str = "-c 1 -W 15"
    result = os.system("ping " + ping_str + " " + host)
    try:
        entry = request.dbsession.query(models.Cluster).filter_by(node=host).first()
        if result:
            entry.serv_ping = 1
        else:
            entry.serv_ping = 0
        request.dbsession.flush()
    except:
        pass
