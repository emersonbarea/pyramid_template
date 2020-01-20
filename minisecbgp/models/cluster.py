import bcrypt
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
    password_hash = Column(String(200), nullable=False)
    master = Column(Integer, nullable=False)

    def set_password(self, pw):
        pwhash = bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt())
        self.password_hash = pwhash.decode('utf8')

    def check_password(self, pw):
        if self.password_hash is not None:
            expected_hash = self.password_hash.encode('utf8')
            return bcrypt.checkpw(pw.encode('utf8'), expected_hash)
        return False