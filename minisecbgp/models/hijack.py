from sqlalchemy import Column, Integer, String, ForeignKey, Index, Boolean, TEXT
from sqlalchemy.orm import relationship

from .meta import Base


class ScenarioAttackType(Base):
    __tablename__ = 'scenario_attack_type'
    id = Column(Integer, primary_key=True)
    scenario_attack_type = Column(String(50), nullable=False, unique=True)
    description = Column(String(250), nullable=False, unique=True)
    scenario = relationship('Scenario', foreign_keys='Scenario.id_scenario_attack_type')


class Scenario(Base):
    __tablename__ = 'scenario'
    id = Column(Integer, primary_key=True)
    id_scenario_attack_type = Column(Integer, ForeignKey('scenario_attack_type.id'))
    id_topology = Column(Integer, ForeignKey('topology.id'))
    scenario_item = relationship('ScenarioItem', foreign_keys='ScenarioItem.id_scenario')
    Index('IndexId_scenario_attack_type', id_scenario_attack_type)
    Index('IndexId7_topology', id_topology)


class ScenarioItem(Base):
    __tablename__ = 'scenario_item'
    id = Column(Integer, primary_key=True)
    id_scenario = Column(Integer, ForeignKey('scenario.id'))
    attacker_as = Column(Integer, ForeignKey('autonomous_system.id'))
    affected_as = Column(Integer, ForeignKey('autonomous_system.id'))
    target_as = Column(Integer, ForeignKey('autonomous_system.id'))
    path = relationship('Path', foreign_keys='Path.id_scenario_item')
    Index('IndexId1_scenario', id_scenario)
    Index('IndexId6_autonomous_system', attacker_as)
    Index('IndexId7_autonomous_system', affected_as)
    Index('IndexId8_autonomous_system', target_as)


class VantagePointActor(Base):
    __tablename__ = 'vantage_point_actor'
    id = Column(Integer, primary_key=True)
    vantage_point_actor = Column(String(50), nullable=False, unique=True)
    description = Column(String(250), nullable=False, unique=True)


class Path(Base):
    __tablename__ = 'path'
    id = Column(Integer, primary_key=True)
    id_scenario_item = Column(Integer, ForeignKey('scenario_item.id'))
    source = Column(Integer, ForeignKey('vantage_point_actor.id'))
    destination = Column(Integer, ForeignKey('vantage_point_actor.id'))
    Index('IndexId1_scenario_item', id_scenario_item)
    Index('IndexId1_vantage_point_actor', source)
    Index('IndexId2_vantage_point_actor', destination)


class PathItem(Base):
    __tablename__ = 'path_item'
    id = Column(Integer, primary_key=True)
    id_path = Column(Integer, ForeignKey('path.id'))
    text_color = Column(Integer, nullable=False)
    id_link = Column(Integer, ForeignKey('link.id'))
    Index('IndexId1_path', id_path)
    Index('IndexId1_link', id_link)


class ScenarioStuff(Base):
    __tablename__ = 'scenario_stuff'
    id = Column(Integer, primary_key=True)
    scenario_name = Column(String(50), nullable=False, unique=True)
    scenario_description = Column(String(50))
    id_topology = Column(Integer, nullable=False)
    attacker_list = Column(TEXT, nullable=False)
    affected_area_list = Column(TEXT, nullable=False)
    target_list = Column(TEXT, nullable=False)
    attack_type = Column(Integer, nullable=False)


class TopologyDistributionMethod(Base):
    __tablename__ = 'topology_distribution_method'
    id = Column(Integer, primary_key=True)
    topology_distribution_method = Column(String(50), nullable=False, unique=True)
    realistic_analysis = relationship('RealisticAnalysis',
                                      foreign_keys='RealisticAnalysis.id_topology_distribution_method')


class EmulationPlatform(Base):
    __tablename__ = 'emulation_platform'
    id = Column(Integer, primary_key=True)
    emulation_platform = Column(String(50), nullable=False, unique=True)
    realistic_analysis = relationship('RealisticAnalysis',
                                      foreign_keys='RealisticAnalysis.id_emulation_platform')


class RouterPlatform(Base):
    __tablename__ = 'router_platform'
    id = Column(Integer, primary_key=True)
    router_platform = Column(String(50), nullable=False, unique=True)
    realistic_analysis = relationship('RealisticAnalysis',
                                      foreign_keys='RealisticAnalysis.id_router_platform')


class RealisticAnalysis(Base):
    __tablename__ = 'realistic_analysis'
    id = Column(Integer, primary_key=True)
    id_topology_distribution_method = Column(Integer, ForeignKey('topology_distribution_method.id'))
    id_emulation_platform = Column(Integer, ForeignKey('emulation_platform.id'))
    id_router_platform = Column(Integer, ForeignKey('router_platform.id'))
    topology = Column(String(50))
    include_stub = Column(Boolean)
    output_path = Column(String(250))
    number_of_autonomous_systems = Column(String(250))
    time_get_data = Column(String(250))
    time_emulate_platform_commands = Column(String(250))
    time_router_platform_commands = Column(String(250))
    time_write_files = Column(String(250))
    Index('IndexId_topology_distribution_method', id_topology_distribution_method)
    Index('IndexId_emulation_platform', id_emulation_platform)
    Index('IndexId_router_platform', id_router_platform)
