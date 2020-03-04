from sqlalchemy import Column, Integer, String, Date, ForeignKey
from .meta import Base
from sqlalchemy.orm import relationship


class Topology(Base):
    __tablename__ = 'topology'
    id = Column(Integer, primary_key=True)
    topology = Column(String(50), nullable=False, unique=True)
    realistic_topology = relationship('RealisticTopology')


class RealisticTopology(Base):
    __tablename__ = 'realistic_topology'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    num_as = Column(Integer, nullable=False)
    num_stub = Column(Integer, nullable=False)
    num_p2c = Column(Integer, nullable=False)
    num_c2c = Column(Integer, nullable=False)


class UrlDownload(Base):
    __tablename__ = 'url_download'
    id = Column(Integer, primary_key=True)
    url = Column(String(100), nullable=False)
    string_file_search = Column(String(100), nullable=False)


class ScheduledDownload(Base):
    __tablename__ = 'scheduled_download'
    id = Column(Integer, primary_key=True)
    loop = Column(Integer, nullable=False)              # repeat period: 1 = daily, 7 = weekly, 30 = monthly, 0 = never repeat
    date = Column(Date)
