from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .meta import Base


class Node(Base):
    __tablename__ = 'node'
    id = Column(Integer, primary_key=True)
    node = Column(String(50), nullable=False, unique=True)
    username = Column(String(50), nullable=False)
    master = Column(Integer, nullable=False)             # 0 = 'worker', 1 = 'master'
    serv_ping = Column(Integer, nullable=False)          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    serv_ssh = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    serv_ssh_status = Column(String(255))
    serv_app = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    serv_app_status = Column(String(255))
    conf_user = Column(Integer, nullable=False)          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_user_status = Column(String(255))
    conf_ssh = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_ssh_status = Column(String(255))
    conf_mininet = Column(Integer, nullable=False)       # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_mininet_status = Column(String(255))
    conf_containernet = Column(Integer, nullable=False)  # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_containernet_status = Column(String(255))
    conf_metis = Column(Integer, nullable=False)         # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_metis_status = Column(String(255))
    conf_maxinet = Column(Integer, nullable=False)       # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_maxinet_status = Column(String(255))

