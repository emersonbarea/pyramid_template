from sqlalchemy import Column, Integer, String, Date, ForeignKey
from .meta import Base
from sqlalchemy.orm import relationship


class Topology(Base):
    __tablename__ = 'topology'
    id = Column(Integer, primary_key=True)
    topology = Column(String(50), nullable=False, unique=True)
    type = Column(Integer, nullable=False)              # 0 = realistic, 1 = synthetic
    realistic_topology = relationship('RealisticTopology')
    synthetic_topology = relationship('SyntheticTopology')


class RealisticTopology(Base):
    __tablename__ = 'realistic_topology'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    as1 = Column(Integer, nullable=False)
    as2 = Column(Integer, nullable=False)
    agreement = Column(Integer, nullable=False)         # 0 = <peer-as>|<peer-as>, 1 = <provider-as>|<customer-as>


class ParametersDownload(Base):
    __tablename__ = 'parameters_download'
    id = Column(Integer, primary_key=True)
    url = Column(String(100), nullable=False)
    string_file_search = Column(String(100), nullable=False)
    c2p = Column(String(50), nullable=False)
    p2p = Column(String(50), nullable=False)


class ScheduledDownload(Base):
    __tablename__ = 'scheduled_download'
    id = Column(Integer, primary_key=True)
    loop = Column(Integer, nullable=False)              # repeat period: 1 = daily, 7 = weekly, 30 = monthly, 0 = never repeat
    date = Column(Date)


class TempCaidaDatabases(Base):
    __tablename__ = 'temp_caida_databases'
    id = Column(Integer, primary_key=True)
    updating = Column(Integer, nullable=False)          # 0 = not updating | 1 = updating now


class SyntheticTopology(Base):
    __tablename__ = 'synthetic_topology'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
