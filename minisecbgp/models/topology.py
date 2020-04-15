from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint, Index, BigInteger
from .meta import Base
from sqlalchemy.orm import relationship


class TopologyType(Base):
    __tablename__ = 'topology_type'
    id = Column(Integer, primary_key=True)
    topology_type = Column(String(50), nullable=False, unique=True)
    topology = relationship('Topology', foreign_keys='Topology.id_topology_type')


class Topology(Base):
    __tablename__ = 'topology'
    id = Column(Integer, primary_key=True)
    id_topology_type = Column(Integer, ForeignKey('topology_type.id'))
    topology = Column(String(50), nullable=False, unique=True)
    description = Column(String(50), nullable=False, unique=True)
    autonomous_system = relationship('AutonomousSystem', foreign_keys='AutonomousSystem.id_topology')
    Index('IndexId_topology_type', id_topology_type)


class AutonomousSystem(Base):
    __tablename__ = 'autonomous_system'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    autonomous_system = Column(BigInteger, nullable=False)
    stub = Column(Integer, nullable=False)          # 0 = not stub | 1 = stub
    link_id_autonomous_system1 = relationship('Link', foreign_keys='Link.id_autonomous_system1')
    link_id_autonomous_system2 = relationship('Link', foreign_keys='Link.id_autonomous_system2')
    prefix = relationship('Prefix', foreign_keys='Prefix.id_autonomous_system')
    UniqueConstraint('id_topology', 'autonomous_system', name='autonomous_system_unique1')
    Index('IndexTopologyAS', id_topology, autonomous_system)
    Index('IndexId_topology', id_topology)


class Link(Base):
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_agreement = Column(Integer, ForeignKey('realistic_topology_agreement.id'))
    id_autonomous_system1 = Column(Integer, ForeignKey('autonomous_system.id'))
    id_autonomous_system2 = Column(Integer, ForeignKey('autonomous_system.id'))
    ip_autonomous_system1 = Column(BigInteger)
    ip_autonomous_system2 = Column(BigInteger)
    mask = Column(Integer)
    description = Column(String(50))
    bandwidth = Column(Integer)  # kbps
    delay = Column(Integer)  # ms
    load = Column(Integer)  # kbps
    Index('IndexId_autonomous_system1', id_autonomous_system1)
    Index('IndexId_autonomous_system2', id_autonomous_system2)
    Index('IndexId_agreement', id_agreement)
    Index('IndexId_topology1', id_topology)


class Prefix(Base):
    __tablename__ = 'prefix'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    prefix = Column(BigInteger, nullable=False)
    mask = Column(Integer, nullable=False)
    Index('IndexId_autonomous_system', id_autonomous_system)


class RealisticTopologyAgreements(Base):
    __tablename__ = 'realistic_topology_agreement'
    id = Column(Integer, primary_key=True)
    agreement = Column(String(50), nullable=False, unique=True)
    value = Column(String(50), nullable=False, unique=True)
    link = relationship('Link')


class RealisticTopologyDownloadParameters(Base):
    __tablename__ = 'realistic_topology_parameters'
    id = Column(Integer, primary_key=True)
    url = Column(String(100), nullable=False)
    file_search_string = Column(String(100), nullable=False)


class RealisticTopologyScheduleDownloads(Base):
    __tablename__ = 'realistic_topology_scheduled_download'
    id = Column(Integer, primary_key=True)
    loop = Column(Integer, nullable=False)  # repeat period: 0 = never repeat, 1 = daily, 7 = weekly, 30 = monthly
    date = Column(Date, nullable=False)


class RealisticTopologyDownloadingCaidaDatabase(Base):
    __tablename__ = 'realistic_topology_downloading_caida_database'
    id = Column(Integer, primary_key=True)
    downloading = Column(Integer, nullable=False)  # 0 = not downloading | 1 = downloading now
