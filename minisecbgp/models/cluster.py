from sqlalchemy import (
    Column,
    Integer,
    String,
)
from .meta import Base


class Cluster(Base):
    __tablename__ = 'cluster'
    id = Column(Integer, primary_key=True)
    node = Column(String(50), nullable=False, unique=True)
    username = Column(String(50), nullable=False)
    master = Column(Integer, nullable=False)             # 0 = 'worker', 1 = 'master'
    serv_ping = Column(Integer, nullable=False)          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    serv_ssh = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    serv_app = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_user = Column(Integer, nullable=False)          # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_ssh = Column(Integer, nullable=False)           # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_containernet = Column(Integer, nullable=False)  # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_metis = Column(Integer, nullable=False)         # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    conf_maxinet = Column(Integer, nullable=False)       # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'