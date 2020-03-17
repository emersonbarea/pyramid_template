from sqlalchemy import Column, Integer, String
from .meta import Base


class Node(Base):
    __tablename__ = 'node'
    id = Column(Integer, primary_key=True)
    node = Column(String(50), nullable=False, unique=True)
    status = Column(Integer, nullable=False)                               # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    hostname = Column(Integer, nullable=False)                             # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    hostname_status = Column(String(255))
    username = Column(String(50), nullable=False)
    master = Column(Integer, nullable=False)                               # 0 = 'worker', 1 = 'master'
    service_ping = Column(Integer, nullable=False)                         # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    service_ssh = Column(Integer, nullable=False)                          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    service_ssh_status = Column(String(255))
    all_services = Column(Integer, nullable=False)
    conf_user = Column(Integer, nullable=False)
    conf_user_status = Column(String(255))
    conf_ssh = Column(Integer, nullable=False)
    conf_ssh_status = Column(String(255))
    install_remote_prerequisites = Column(Integer, nullable=False)
    install_remote_prerequisites_status = Column(String(255))
    install_containernet = Column(Integer, nullable=False)
    install_containernet_status = Column(String(255))
    install_metis = Column(Integer, nullable=False)
    install_metis_status = Column(String(255))
    install_maxinet = Column(Integer, nullable=False)
    install_maxinet_status = Column(String(255))
    all_install = Column(Integer, nullable=False)
