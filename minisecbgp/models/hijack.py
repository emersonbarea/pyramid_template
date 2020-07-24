from sqlalchemy import Column, Integer, String, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import relationship

from .meta import Base


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
    id_topology = Column(Integer, ForeignKey('topology.id'))
    id_topology_distribution_method = Column(Integer, ForeignKey('topology_distribution_method.id'))
    id_emulation_platform = Column(Integer, ForeignKey('emulation_platform.id'))
    id_router_platform = Column(Integer, ForeignKey('router_platform.id'))
    include_stub = Column(Boolean, nullable=False)
    realistic_analysis = Column(String(50), nullable=False, unique=True)
    Index('IndexId7_topology', id_topology)
    Index('IndexId_topology_distribution_method', id_topology_distribution_method)
    Index('IndexId_emulation_platform', id_emulation_platform)
    Index('IndexId_router_platform', id_router_platform)
