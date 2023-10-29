# valai/charm/database.py

import logging
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

from .models import Character, CharacterTrait, CharacterSymbol, CharacterQuest, WorldLocation, InjectionSymbol

logger  = logging.getLogger(__name__)

class DatabaseManager(object):

    @classmethod
    def from_config(cls, database_uri : str, **kwargs):
        """Create a new DatabaseManager from a config dictionary."""
        return cls(database_uri)

    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Create and return a new SQLAlchemy session."""
        return self.Session()

    def get_character(self, session, character_id : int):
        """Get a character by their ID."""
        character = session.query(Character).filter_by(id=character_id).one_or_none()
        logger.debug(f'Character, {character_id}, {character}')
        return character

    def get_character_by_name(self, session, name):
        """Get a character by their name."""
        character = session.query(Character).filter_by(name=name).one_or_none()
        return character

    def get_characters(self, session, character_ids):
        """Get multiple characters by their IDs."""
        characters = session.query(Character).filter(Character.id.in_(character_ids)).all()
        return characters

    def get_characters_at_location(self, session, location):
        """Get all characters at a specific location."""
        characters = session.query(Character).filter_by(location_id=location.id).all()
        return characters

    def get_location_by_name(self, session, name):
        """Get a location by its name."""
        location = session.query(WorldLocation).filter_by(name=name).one_or_none()
        return location
    
    def get_symbol(self, session, symbol):
        """Get a symbol by its name."""
        result = session.query(InjectionSymbol).filter_by(symbol=symbol).one_or_none()
        return result
    
    def get_character_traits(self, session, character_id):
        """Get all traits for a character."""
        traits = session.query(CharacterTrait).filter_by(character_id=character_id).all()
        return traits

    def get_character_quest_symbols(self, session, character_id):
        """Get all quests for a character."""
        quests = session.query(CharacterQuest).filter_by(character_id=character_id).all()
        return [q.get_symbol() for q in quests]

    def get_character_symbols(self, session, character_id):
        character_symbols = session.query(CharacterSymbol).filter_by(character_id=character_id).all()
        return character_symbols

    # ... more methods for other types of database interactions
