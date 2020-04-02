from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint, Index
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


class AutonomousSystem(Base):
    __tablename__ = 'autonomous_system'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    autonomous_system = Column(Integer, nullable=False)
    stub = Column(Integer, nullable=False)
    link_id_autonomous_system1 = relationship('Link', foreign_keys='Link.id_autonomous_system1')
    link_id_autonomous_system2 = relationship('Link', foreign_keys='Link.id_autonomous_system2')
    prefix = relationship('Prefix', foreign_keys='Prefix.id_autonomous_system')
    UniqueConstraint('id_topology', 'autonomous_system', name='autonomous_system_unique1')
    Index('IndexTopologyAS', id_topology, autonomous_system)


class RealisticTopologyAgreements(Base):
    __tablename__ = 'realistic_topology_agreement'
    id = Column(Integer, primary_key=True)
    agreement = Column(String(50), nullable=False, unique=True)
    value = Column(String(50), nullable=False, unique=True)
    link = relationship('Link')


class Link(Base):
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    id_agreement = Column(Integer, ForeignKey('realistic_topology_agreement.id'))
    id_autonomous_system1 = Column(Integer, ForeignKey('autonomous_system.id'))
    id_autonomous_system2 = Column(Integer, ForeignKey('autonomous_system.id'))
    ip_autonomous_system1 = Column(Integer)
    ip_autonomous_system2 = Column(Integer)
    mask = Column(Integer)
    description = Column(String(50))
    bandwidth = Column(Integer)  # kbps
    delay = Column(Integer)  # ms
    load = Column(Integer)  # kbps


class Prefix(Base):
    __tablename__ = 'prefix'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    prefix = Column(Integer, nullable=False)
    mask = Column(Integer, nullable=False)


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
