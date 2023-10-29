# valai/charm/models/character.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base

class Character(Base):
    __tablename__ = 'characters'

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey('locations.id'))
    name = Column(String)
    symbol = Column(String)
    job = Column(String)
    description = Column(String)
    disposition = Column(Integer)
    status = Column(String)

    location = relationship("WorldLocation", back_populates="characters")
    traits = relationship("CharacterTrait", back_populates="character")
    symbols = relationship("CharacterSymbol", back_populates="character")
    quests = relationship("CharacterQuest", back_populates="character")

class CharacterTrait(Base):
    __tablename__ = 'character_traits'

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'))
    trait = Column(String)
    status = Column(String)

    character = relationship("Character", back_populates="traits")

class CharacterSymbol(Base):
    __tablename__ = 'character_symbols'

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'))
    keyword = Column(String)
    symbol = Column(String)

    character = relationship("Character", back_populates="symbols")

    __table_args__ = (UniqueConstraint('character_id', 'keyword', 'symbol', name='_character_keyword_symbol_uc'),)

class CharacterQuest(Base):
    __tablename__ = 'character_quests'

    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'))
    name = Column(String)
    complete = Column(Boolean)
    incomplete_symbol = Column(String)
    complete_symbol = Column(String)

    character = relationship("Character", back_populates="quests")

    __table_args__ = (UniqueConstraint('character_id', 'name', name='_character_quest_name_uc'),)

    def get_symbol(self):
        return self.complete_symbol if self.complete else self.incomplete_symbol

