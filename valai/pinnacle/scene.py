# valai/pinnacle/scene.py

from collections import defaultdict
import logging
from typing import Optional, Dict, List, Set, Any, Tuple

from .exception import DirectorError
from .roster import Actor, CharacterRoster
from .symbol import Symbolizer, Character, Location, CharacterDialog

logger = logging.getLogger(__name__)


class DirectorDialog(CharacterDialog):
    def __call__(self, character: Character, **kwargs: Any) -> List[str]:
        yield f"$player (to ZxdrOS, speak): What is {character.name}'s job?"
        yield f"ZxdrOS (to $player, explanatory): {character.name} is a {character.job}."
        yield f"$player (to ZxdrOS, look): I look at {character.name}."
        yield f"ZxdrOS (to $player, checking): You can see {character.name}."
        yield f"Narrator (to $player, descriptive): {character.description}"
        yield f"$player (to ZxdrOS, speak): What is {character.name} doing?"
        yield f"ZxdrOS (to $player, checking): {character.name} is {character.status}."

        yield f"$player (to ZxdrOS, speak): How does {character.name} feel about $player?"
        if (abs(character.disposition) - 15) < 0:
            yield f"ZxdrOS (to $player, checking): {character.name} doesn't have any strong opinions about $player."
            yield f'{character.name} (about $player, curious): I see a new person in town. They open their mouth to speak, "...".  Perhaps they will speak to me first.'
        elif character.disposition >= 100:
            yield f"ZxdrOS (to $player, checking): {character.name} loves $player."
            yield f'{character.name} (about $player, estatic): Oh my goodness, it\'s $player.  My heart is racing.'
        elif character.disposition > 50:
            yield f"ZxdrOS: (to $player, checking) {character.name} really likes $player."
            yield f'{character.name} (about $player, happy): I see $player.  I hope they are doing well.'
        elif character.disposition > 15:
            yield f"ZxdrOS (to $player, checking): {character.name} likes $player."
            yield f'{character.name} (about $player, neutral): I see $player.  I wonder what they are doing here.'
        elif character.disposition > -50:
            yield f"ZxdrOS (to $player, checking): {character.name} dislikes $player."
            yield f'{character.name} (about $player, unhappy): I see $player.  I hope they don\'t bother me.'
        else:
            yield f"ZxdrOS (to $player, checking): {character.name} hates $player"
            yield f'{character.name} (about $player, angry): I hope $player dies!'

        return []

class Scene:
    roster : CharacterRoster
    location : Location
    characters : Set[str]
    character_keywords : Dict[str, str]
    #discovered : Set[str] # TODO, this would allow for progressive discovery of information
    enemies : Dict[str, Actor]
    exits : Dict[str, Location]
    turns_here : int
    in_dungeon : bool
    dungeon : Optional[str]
    description : Optional[str]

    def __init__(self, roster : CharacterRoster,
                 location : Location,
                 characters : Set[str] = set(),
                 character_keywords : Dict[str, str] = {},
                 enemies : Dict[str, Actor] = [],
                 exits : Dict[str, Location] = [], exit_keywords : Dict[str, str] = {}
                 ):
        self.roster = roster
        self.location = location
        self.enemies = enemies
        self.characters = characters
        self.character_keywords = character_keywords
        self.exits = exits
        self.exit_keywords = exit_keywords
        self.character_dialog = DirectorDialog()

    def exit_for_keyword(self, keyword : str) -> Optional[Location]:
        keyword = keyword.lower()
        if keyword in self.exit_keywords:
            exit_key = self.exit_keywords[keyword]
            return self.exits[exit_key]
        return None

    def actor_for_keyword(self, keyword : str) -> Optional[Actor]:
        keyword = keyword.lower()
        if keyword in self.character_keywords:
            character_key = self.character_keywords[keyword]
            return self.roster.get_actor(character_key)
        return None

    def get_location_prompt(self) -> List[str]:
        exit_locs = defaultdict(list)
        for kw, sym in self.exit_keywords.items():
            exit_locs[sym].append(kw)
        
        exits = [
            f"{n} - {exit.name} {', '.join(exit_locs[n])})"
            for n, exit in self.exits.items()
        ]
        def gen_char():
            yield "### Input (exits):"
            yield "[Exits - " + ', '.join(exits) + "]"
            yield "### Input (current scene):"
            yield self.location.location_line()
            yield self.location.description_line()
            yield "### Input (characters):"
            logger.debug(f"Loading {len(self.characters)} characters: {','.join(self.characters)}.")
            for actor in self.roster.get_actors(self.characters).values():
                yield actor.sheet.character_line()
            return []
        
        return list(gen_char())
    
    def get_prices(self) -> List[Tuple[str, str, int]]:
        for actor in self.roster.get_actors(self.characters).values():
            for item, price in actor.sheet.prices.items():
                yield actor.sheet.symbol, item, price
        return []

    def get_player_prompt(self) -> List[str]:
        def gen_prompt():
            yield self.roster.player.sheet.character_line()
            yield self.roster.player.sheet.description_line()
            for eq in self.roster.player.sheet.equipment_lines():
                yield eq

        return list(gen_prompt())

    def add_item(self, actor : str, **kwargs) -> str:
        return self.characters[actor].add_item(**kwargs)

    @classmethod
    def from_symbolizer(cls, location_symbol : str, sym : Symbolizer, roster : CharacterRoster, **kwargs) -> 'Scene':
        """Factory to take and load a scene from a symbolizer."""
        if location_symbol not in sym.locations:
            raise DirectorError(f"Location {location_symbol} not found.")
        location = sym.locations[location_symbol]

        characters : Set[str] = set()
        character_keywords : Dict[str, str] = {}
        logger.debug(f"Loading {len(roster.characters)} characters.")
        roster.set_current_quest_characters(sym.quests)
        for c, actor in roster.get_actors(None).items():
            if c in roster.party:
                logger.debug(f"Loading {c} as a party member.")

                for keyword in actor.sheet.character_keywords:
                    character_keywords[keyword] = c
            elif actor.sheet.location_symbol == location.at_location:
                logger.debug(f"Loading {c} as a scene member.")
                characters.add(c)

                for keyword in actor.sheet.character_keywords:
                    character_keywords[keyword] = c

        exit_keywords : Dict[str, str] = {}
        exits : Dict[str, Location] = {}
        for l, loc in sym.locations.items():
            if location.parent_symbol == loc.symbol:
                if loc.traversable:
                    exits[l] = loc
                    for keyword in loc.travel_keywords:
                        exit_keywords[keyword] = l
            elif location.symbol == loc.parent_symbol:
                exits[l] = loc
                for keyword in loc.travel_keywords:
                    exit_keywords[keyword] = l

        return cls(roster=roster, location=location,
                   characters=characters, character_keywords=character_keywords,
                   exits=exits, exit_keywords=exit_keywords)

