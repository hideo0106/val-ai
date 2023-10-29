# valai/charm/models/location.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base

class WorldLocation(Base):
    """Represents a location in the game."""

    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    descriptor = Column(String)
    symbol = Column(String)

    characters = relationship("Character", back_populates="location")

    def __repr__(self):
        return f"[{self.name} is a {self.descriptor} {self.symbol}]"
