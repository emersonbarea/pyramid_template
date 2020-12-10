from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Index
from .meta import Base
from sqlalchemy.orm import relationship


class Node(Base):
    __tablename__ = 'node'
    id = Column(Integer, primary_key=True)
    node = Column(String(39), nullable=False, unique=True)                                # node IP address
    hostname = Column(String(255))
    master = Column(Boolean, nullable=False)                                              # True = 'master' | false = 'worker'
    node_service = relationship('NodeService', foreign_keys='NodeService.id_node')
    node_install = relationship('NodeInstall', foreign_keys='NodeInstall.id_node')


class Service(Base):
    __tablename__ = 'service'
    id = Column(Integer, primary_key=True)
    service = Column(String(50), nullable=False, unique=True)
    description = Column(String(50), nullable=False, unique=True)
    url = Column(String(250))
    node_service = relationship('NodeService', foreign_keys='NodeService.id_service')


class Configuration(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key=True)
    configuration = Column(String(50), nullable=False, unique=True)
    description = Column(String(50), nullable=False, unique=True)
    url = Column(String(250))
    node_configuration = relationship('NodeConfiguration', foreign_keys='NodeConfiguration.id_configuration')


class Install(Base):
    __tablename__ = 'install'
    id = Column(Integer, primary_key=True)
    install = Column(String(50), nullable=False, unique=True)
    description = Column(String(50), nullable=False, unique=True)
    url = Column(String(250))
    node_install = relationship('NodeInstall', foreign_keys='NodeInstall.id_install')


class NodeService(Base):
    __tablename__ = 'node_service'
    id = Column(Integer, primary_key=True)
    id_node = Column(Integer, ForeignKey('node.id'))
    id_service = Column(Integer, ForeignKey('service.id'))
    status = Column(Integer, nullable=False)                                              # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    log = Column(String(250))
    Index('IndexId1_node', id_node)
    Index('IndexId_service', id_service)


class NodeConfiguration(Base):
    __tablename__ = 'node_configuration'
    id = Column(Integer, primary_key=True)
    id_node = Column(Integer, ForeignKey('node.id'))
    id_configuration = Column(Integer, ForeignKey('configuration.id'))
    status = Column(Integer, nullable=False)                                              # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    log = Column(String(250))
    Index('IndexId3_node', id_node)
    Index('IndexId_configuration', id_configuration)


class NodeInstall(Base):
    __tablename__ = 'node_install'
    id = Column(Integer, primary_key=True)
    id_node = Column(Integer, ForeignKey('node.id'))
    id_install = Column(Integer, ForeignKey('install.id'))
    status = Column(Integer, nullable=False)                                              # 0 = 'OK', 1 = 'error', 2 = 'wait (installing)'
    log = Column(String(250))
    Index('IndexId2_node', id_node)
    Index('IndexId_install', id_install)
