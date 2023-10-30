# valai/charm/scene.py

from collections import defaultdict
import logging
import re
from typing import List

from .database import DatabaseManager, WorldLocation, Character
from .prompt import symbol_expansion

logger = logging.getLogger(__name__)

class CharacterSheet(object):
    def __init__(self, name, location, symbol, job, description, status, disposition, traits, symbols, quests):
        self.name = name
        self.location = location
        self.symbol = symbol
        self.job = job
        self.description = description
        self.status = status
        self.disposition = disposition
        self.traits = traits
        self.symbols = symbols
        self.quests = quests

    @classmethod
    def from_character(cls, character : Character):
        """Get a character sheet for a character."""
        sheet = {
            'name': character.name,
            'location': character.location.name,
            'symbol': character.symbol,
            'job': character.job,
            'description': character.description,
            'status': character.status,
            'disposition': character.disposition,
            'traits': [t.trait for t in character.traits],
            'symbols': {s.keyword: s.symbol for s in character.symbols},
            'quests': [q.get_symbol() for q in character.quests]
        }
        return cls(**sheet)


class Scene(object):
    """A class to manage the game state."""
    location : WorldLocation | None
    player : str | None
    characters : dict[str, CharacterSheet]
    enemies : dict[str, CharacterSheet]
    narration : dict[str, CharacterSheet]
    turns_here : int
    action_stream : list[str]
    quest_stream : list[str]
    relationship_stream : dict[str, list[str]]
    needs_stream : list[str]
    in_dungeon : bool
    dungeon : str | None
    description : str | None

    @classmethod
    def from_db(cls, db : DatabaseManager, player: str, party: List[str], location_name: str, **kwargs):
        """Factory method to create a Scene object from database URI and initial state."""
        scene = cls(db)
        with db.get_session() as session:
            scene.set_location(session, location_name)
            scene.set_player(session, player)
            scene.set_party(session, party)
            scene.update_characters(session)
        return scene

    def __init__(self, db: DatabaseManager):
        """Initialize the Scene object."""
        self.db = db
        self.location = None
        self.player = None

        # These 
        self.party = {}
        self.characters = {}
        self.enemies = {}
        self.narration = {}
        self.turns_here = 0
        self.action_stream = []
        self.quest_stream = []
        self.relationship_stream = defaultdict(list)
        self.needs_stream = []
        self.in_dungeon = False
        self.dungeon = None
        self.description = None

        # Define the format map
        self.format_map = {
            '>': self.handle_player_turn,
            r'\w+:': self.handle_character_turn,
            r'\[\w+\]': self.handle_system_info_turn,
        }

    def player_stats(self):
        return f"[{self.player} a=charming b=tricky c=dramatic d=strong e=observant]"

    def fetch_location_data(self) -> tuple[list[str], list[str], list[str]]:
        """Fetch and format the data for the current location."""
        if self.location is None:
            return [], [], []
        loc_stats = []
        loc_dialog = []
        loc_symbols = []
        loc_stats.append(f"[{self.location.name} a=city b=market c=temple d=inn e=home {self.location.symbol}]")
        loc_symbols.append(self.location.symbol)
        #loc_dialog.append(f"> I am in {self.location.name}.\nNarrator: (looking) {self.location.description}")
        return loc_stats, loc_symbols, loc_dialog

    def fetch_character_data(self, session, character_name : str) -> tuple[list[str], list[str], list[str]]:
        """Fetch and format the data for a character."""
        # Fetch the Character object
        sheet = self.characters.get(character_name, None)
        if sheet is None:
            return [], [], []
        # Format the character data
        char_stats = []
        char_symbols = []
        char_dialog = []
        character_data = f"[{sheet.name} "
        for i, trait in enumerate(sheet.traits):
            character_data += f" {chr(ord('a') + i)}={trait}"
        character_data += f" {sheet.symbol}]"
        char_stats.append(character_data)
        char_dialog.append(f"> {sheet.name}'s job?\nZxdrOS: (job) {sheet.name} is a {sheet.job}.")
        char_dialog.append(f"> I look at {sheet.name}.\nNarrator: (looking) {sheet.name} {sheet.description}")
        char_dialog.append(f"> {sheet.name} doing?\nZxdrOS: (status) {sheet.name} is {sheet.status}.")
        if (abs(sheet.disposition) - 15) < 0:
            char_dialog.append(f"> {sheet.name} feel about?\nZxdrOS: (relationship) {sheet.name} doesn't have any strong opinions about $player.")
            char_dialog.append(f'{sheet.name}: (curious) I see a new person in town. They open their mouth to speak, "...".  Perhaps they will speak to me first.')
        elif sheet.disposition > 50:
            char_dialog.append(f"> {sheet.name} feel about?\nZxdrOS: (relationship) {sheet.name} loves $player.")
        elif sheet.disposition > 15:
            char_dialog.append(f"> {sheet.name} feel about?\nZxdrOS: (relationship) {sheet.name} likes $player.")
        elif sheet.disposition > -50:
            char_dialog.append(f"> {sheet.name} feel about?\nZxdrOS: (relationship) {sheet.name} dislikes $player.")
        else:
            char_dialog.append(f"> {sheet.name} feel about?\nZxdrOS: (relationship) {sheet.name} hates $player.")

        char_dialog.append(f"> Hello, I'm $player.\n{sheet.name}: (wary) Oh, hello there.  I don't know who you are.")

        char_symbols.append(sheet.symbol)

        for i, quest_symbol in enumerate(sheet.quests):
            children_symbols = symbol_expansion(self.db, session, quest_symbol)
            logger.debug(f'Quest: {quest_symbol}, {children_symbols}')
            for depth, symbol in children_symbols:
                char_symbols.append(symbol)

        return char_stats, char_symbols, char_dialog

    def get_kw_symbol(self):
        symbol_kw_dict = {}
        for sheet in self.characters.values():
            for keyword, symbol in sheet.symbols.items():
                symbol_kw_dict[symbol] = keyword
        return symbol_kw_dict

    def handle_player_turn(self, turn):
        """Handle a player turn."""
        pass

    def handle_character_turn(self, turn):
        """Handle a character turn."""
        pass

    def handle_system_info_turn(self, turn):
        """Handle a system information turn."""
        pass

    def process_stream(self, turn_stream: List[str]):
        """Process a turn stream and update the game state."""
        for turn in turn_stream:
            for pattern, handler in self.format_map.items():
                if re.match(pattern, turn):
                    handler(turn)
                    break

    def set_location(self, session, location_name: str):
        """Sets the current location."""
        self.location = self.db.get_location_by_name(session, location_name)

    def set_player(self, session, player_name: str):
        """Sets the player character."""
        self.player = player_name

    def set_party(self, session, party_names: List[str]):
        """Sets the party members."""
        for name in party_names:
            character = self.db.get_character_by_name(session, name)
            self.party[name] = character

    def update_characters(self, session):
        """Updates the characters present in the current location."""
        if self.location is None:
            return
        characters_in_location = self.db.get_characters_at_location(session, self.location)
        for character in characters_in_location:
            self.characters[character.name] = CharacterSheet.from_character(character)
