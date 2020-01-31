import subprocess


def ping(node):
    result = subprocess.Popen(['ping', node, '-c', '1', "-W", "15"])
    result.wait()
    service_ping = result.poll()
    return service_ping
