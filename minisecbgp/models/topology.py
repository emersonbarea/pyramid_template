from sqlalchemy import Column, Integer, String, Date, ForeignKey, UniqueConstraint, Index, BigInteger, Boolean
from .meta import Base
from sqlalchemy.orm import relationship


class TopologyType(Base):
    __tablename__ = 'topology_type'
    id = Column(Integer, primary_key=True)
    topology_type = Column(String(50), nullable=False, unique=True)
    description = Column(String(250), nullable=False, unique=True)
    topology = relationship('Topology', foreign_keys='Topology.id_topology_type')


class Topology(Base):
    __tablename__ = 'topology'
    id = Column(Integer, primary_key=True)
    id_topology_type = Column(Integer, ForeignKey('topology_type.id'))
    topology = Column(String(50), nullable=False, unique=True)
    description = Column(String(50), nullable=False)
    autonomous_system = relationship('AutonomousSystem', foreign_keys='AutonomousSystem.id_topology')
    link = relationship('Link', foreign_keys='Link.id_topology')
    region = relationship('Region', foreign_keys='Region.id_topology')
    internet_exchange_point = relationship('InternetExchangePoint', foreign_keys='InternetExchangePoint.id_topology')
    type_of_user = relationship('TypeOfUser', foreign_keys='TypeOfUser.id_topology')
    type_of_service = relationship('TypeOfService', foreign_keys='TypeOfService.id_topology')
    scenario = relationship('Scenario', foreign_keys='Scenario.id_topology')
    event_behaviour = relationship('EventBehaviour', foreign_keys='EventBehaviour.id_topology')
    realistic_analysis = relationship('RealisticAnalysis', foreign_keys='RealisticAnalysis.id_topology')
    Index('IndexId_topology_type', id_topology_type)


class AutonomousSystem(Base):
    __tablename__ = 'autonomous_system'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_region = Column(Integer, ForeignKey('region.id'))
    autonomous_system = Column(BigInteger, nullable=False)
    stub = Column(Boolean, nullable=False)                                                      # True = 'stub' | false = 'full'
    router_id = relationship('RouterId', foreign_keys='RouterId.id_autonomous_system')
    prefix = relationship('Prefix', foreign_keys='Prefix.id_autonomous_system')
    link_id_autonomous_system1 = relationship('Link', foreign_keys='Link.id_autonomous_system1')
    link_id_autonomous_system2 = relationship('Link', foreign_keys='Link.id_autonomous_system2')
    UniqueConstraint('id_topology', 'autonomous_system', name='autonomous_system_unique1')
    type_of_user_autonomous_system = relationship('TypeOfUserAutonomousSystem', foreign_keys='TypeOfUserAutonomousSystem.id_autonomous_system')
    type_of_service_autonomous_system = relationship('TypeOfServiceAutonomousSystem', foreign_keys='TypeOfServiceAutonomousSystem.id_autonomous_system')
    autonomous_system_internet_exchange_point = relationship('AutonomousSystemInternetExchangePoint', foreign_keys='AutonomousSystemInternetExchangePoint.id_autonomous_system')
    Index('IndexTopologyAS', id_topology, autonomous_system)
    Index('IndexId1_topology', id_topology)
    Index('IndexId1_region', id_region)


class RouterId(Base):
    __tablename__ = 'router_id'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    router_id = Column(String(39), nullable=False)
    Index('IndexId1_autonomous_system', id_autonomous_system)


class Prefix(Base):
    __tablename__ = 'prefix'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    prefix = Column(String(39), nullable=False)
    mask = Column(Integer, nullable=False)
    Index('IndexId2_autonomous_system', id_autonomous_system)


class Link(Base):
    __tablename__ = 'link'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_link_agreement = Column(Integer, ForeignKey('link_agreement.id'))
    id_autonomous_system1 = Column(Integer, ForeignKey('autonomous_system.id'))
    id_autonomous_system2 = Column(Integer, ForeignKey('autonomous_system.id'))
    ip_autonomous_system1 = Column(String(39))
    ip_autonomous_system2 = Column(String(39))
    mask = Column(Integer)
    description = Column(String(50))
    bandwidth = Column(Integer)  # kbps
    delay = Column(Integer)  # ms
    load = Column(Integer)  # kbps
    path_item = relationship('PathItem', foreign_keys='PathItem.id_link')
    Index('IndexId2_topology', id_topology)
    Index('IndexId1_link_agreement', id_link_agreement)
    Index('IndexId_autonomous_system1', id_autonomous_system1)
    Index('IndexId_autonomous_system2', id_autonomous_system2)


class LinkAgreement(Base):
    __tablename__ = 'link_agreement'
    id = Column(Integer, primary_key=True)
    agreement = Column(String(50), nullable=False, unique=True)
    description = Column(String(250), nullable=False, unique=True)
    link = relationship('Link')
    realistic_topology_link_agreement = relationship('RealisticTopologyLinkAgreement', foreign_keys='RealisticTopologyLinkAgreement.id_link_agreement')


class RealisticTopologyLinkAgreement(Base):
    __tablename__ = 'realistic_topology_link_agreement'
    id = Column(Integer, primary_key=True)
    id_link_agreement = Column(Integer, ForeignKey('link_agreement.id'))
    value = Column(String(50), nullable=False, unique=True)
    Index('IndexId2_link_agreement', id_link_agreement)


class RealisticTopologyDownloadParameter(Base):
    __tablename__ = 'realistic_topology_parameter'
    id = Column(Integer, primary_key=True)
    url = Column(String(100), nullable=False)
    file_search_string = Column(String(100), nullable=False)


class RealisticTopologyScheduleDownload(Base):
    __tablename__ = 'realistic_topology_scheduled_download'
    id = Column(Integer, primary_key=True)
    loop = Column(Integer, nullable=False)  # repeat period: 0 = never repeat, 1 = daily, 7 = weekly, 30 = monthly
    date = Column(Date, nullable=False)


class DownloadingTopology(Base):
    __tablename__ = 'downloading_topology'
    id = Column(Integer, primary_key=True)
    downloading = Column(Integer, nullable=False)  # 0 = not downloading | 1 = downloading now


class TypeOfUser(Base):
    __tablename__ = 'type_of_user'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    type_of_user = Column(String(50), nullable=False)
    type_of_user_autonomous_system = relationship('TypeOfUserAutonomousSystem', foreign_keys='TypeOfUserAutonomousSystem.id_type_of_user')
    Index('IndexId3_topology', id_topology)


class TypeOfUserAutonomousSystem(Base):
    __tablename__ = 'type_of_user_autonomous_system'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    id_type_of_user = Column(Integer, ForeignKey('type_of_user.id'))
    number = Column(Integer)
    Index('IndexId3_autonomous_system', id_autonomous_system)
    Index('IndexId_type_of_user', id_type_of_user)


class TypeOfService(Base):
    __tablename__ = 'type_of_service'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    type_of_service = Column(String(50), nullable=False)
    type_of_service_autonomous_system = relationship('TypeOfServiceAutonomousSystem', foreign_keys='TypeOfServiceAutonomousSystem.id_type_of_service')
    Index('IndexId4_topology', id_topology)


class TypeOfServiceAutonomousSystem(Base):
    __tablename__ = 'type_of_service_autonomous_system'
    id = Column(Integer, primary_key=True)
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    id_type_of_service = Column(Integer, ForeignKey('type_of_service.id'))
    Index('IndexId4_autonomous_system', id_autonomous_system)
    Index('IndexId_type_of_service', id_type_of_service)


class Region(Base):
    __tablename__ = 'region'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_color = Column(Integer, ForeignKey('color.id'))
    region = Column(String(50), nullable=False)
    autonomous_system = relationship('AutonomousSystem', foreign_keys='AutonomousSystem.id_region')
    internet_exchange_point = relationship('InternetExchangePoint', foreign_keys='InternetExchangePoint.id_region')
    UniqueConstraint('id_topology', 'region', name='region_unique1')
    Index('IndexId5_topology', id_topology)
    Index('IndexId_color', id_color)


class InternetExchangePoint(Base):
    __tablename__ = 'internet_exchange_point'
    id = Column(Integer, primary_key=True)
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_region = Column(Integer, ForeignKey('region.id'))
    internet_exchange_point = Column(String(50), nullable=False)
    autonomous_system_internet_exchange_point = relationship('AutonomousSystemInternetExchangePoint', foreign_keys='AutonomousSystemInternetExchangePoint.id_internet_exchange_point')
    Index('IndexId6_topology', id_topology)
    Index('IndexId2_region', id_region)


class AutonomousSystemInternetExchangePoint(Base):
    __tablename__ = 'autonomous_system_internet_exchange_point'
    id = Column(Integer, primary_key=True)
    id_internet_exchange_point = Column(Integer, ForeignKey('internet_exchange_point.id'))
    id_autonomous_system = Column(Integer, ForeignKey('autonomous_system.id'))
    Index('IndexId_internet_exchange_point', id_internet_exchange_point)
    Index('IndexId5_autonomous_system', id_autonomous_system)


class Color(Base):
    __tablename__ = 'color'
    id = Column(Integer, primary_key=True)
    background_color = Column(String(50), nullable=False)
    text_color = Column(String(50), nullable=False)
    region = relationship('Region', foreign_keys='Region.id_color')

