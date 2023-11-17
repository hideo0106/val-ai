# valai/pinnacle/model.py

import logging
from typing import List, Dict, Optional, Protocol, Any, Dict, TypedDict

logger = logging.getLogger(__name__)


class Location:
    """A class to represent a location in the game world."""

    def __init__(self, name: str, symbol: str, parent_symbol: Optional[str] = None,
                 distance : int = 0, at_location : Optional[str] = None,
                 travel_keywords : List[str] = [], traits : List[str] = [], traversable : bool = True,
                 related_symbols: List[str] = [], description : Optional[str] = None, start : bool = False,
                 enclosure : bool = False
                 ):
        self.name = name
        self.start = start
        self.symbol = symbol
        self.parent_symbol = parent_symbol
        self.distance = distance
        self.traits = traits
        self.at_location = at_location
        self.traversable = traversable
        self.travel_keywords = travel_keywords
        self.related_symbols = related_symbols
        self.description = description
        self.enclosure = enclosure

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)

    def location_line(self) -> str:
        """Fetch and format the trait data for a location."""
        traits = ' '.join([f"{chr(ord('a') + i)}={trait}" for i, trait in enumerate(self.traits)])
        return f"[{self.symbol} - {self.name} {traits}]"

    def description_line(self) -> str:
        """Fetch and format the description data for a character."""
        return f'[{self.symbol} - {self.name} {self.description}]'

    def travel_line(self, char : 'Character') -> str:
        """Fetch and format the travel data for a location."""
        return f'[{char.symbol} - {char.name} has traveled to {self.name} {self.symbol}]'


class Symbol:
    """A class to represent a symbol in the game world."""

    def __init__(self, symbol: str, value: str, keywords: List[str] = [], related_symbols: List[str] = []):
        self.symbol = symbol
        self.keywords = keywords
        self.related_symbols = related_symbols
        self.value = value

    @classmethod
    def from_dict(cls, **kwargs):
        return cls(**kwargs)
    

# Define the Character class
class Character:
    """A class to represent a character in the game world."""

    def __init__(self,
                 name: str,
                 symbol: str,
                 location_symbol: str,
                 title: str = "None",
                 description: str = "None",
                 status: str = "None",
                 disposition: int = 0,
                 job: str = "None",
                 will_join: Optional[bool] = None,
                 related_symbols : List[str] = [],
                 symbols: Dict[str, Symbol] = [],
                 traits: List[str] = [],
                 character_keywords : List[str] = [],
                 inventory : List[str] = [],
                 silver : int = 0,
                 prices: Dict[str, int] = {},
                 spells : Dict[str, str] = {},
                ):
        self.name = name
        self.symbol = symbol
        self.title = title
        self.will_join = will_join
        self.character_keywords = character_keywords
        self.symbols = symbols
        self.related_symbols = related_symbols
        self.job = job
        self.traits = traits
        self.location_symbol = location_symbol
        self.description = description
        self.disposition = disposition
        self.status = status
        self.inventory = inventory
        self.silver = silver
        self.prices = prices
        self.spells = spells
    
    @classmethod
    def from_dict(cls, symbols : Dict[str, Any] = {}, **kwargs):
        symbols  = { k: Symbol.from_dict(symbol=k, **v) for k, v in symbols.items() }
        return cls(symbols=symbols, **kwargs)

    def stat_line(self) -> str:
        """Fetch and format the trait data for a character."""
        traits = ' '.join([f"{chr(ord('a') + i)}={trait}" for i, trait in enumerate(self.traits)])
        return f"*{self.symbol} {traits}*"

    def character_line(self) -> str:
        """Fetch and format the trait data for a character."""
        traits = ' '.join([f"{chr(ord('a') + i)}={trait}" for i, trait in enumerate(self.traits)])
        return f"[{self.symbol} - {self.name} {traits}]"

    def description_line(self) -> str:
        """Fetch and format the description data for a character."""
        return f'[{self.symbol} - {self.name} {self.description}]'

    def equipment_lines(self) -> List[str]:
        """Fetch and format the equipped items."""
        return [ f'[{self.symbol} - {self.name} has gained a {i}]' for i in self.inventory ]

    def spell_lines(self) -> List[str]:
        """Fetch and format the known spells."""
        return [ f'[{self.symbol} - {self.name} learns {s} spell]' for s, _ in self.spells.items() ]

    def sales_lines(self) -> List[str]:
        """Fetch and format the equipped items."""
        return [ f'[{self.symbol} - {self.name} sells {i} for {v} silver]' for i, v in self.prices.items() ]

    def join_line(self, join : bool) -> str:
        """Fetch and format the party action for a character."""
        return f"[{self.symbol} - {self.name} has {'joined' if join else 'left'} the party]"


class QuestPart(TypedDict):
    symbols: Dict[str, Symbol]
    characters: Dict[str, Character]
    objectives: List[str]


class Quest:
    def __init__(self,
                symbol: str,
                name: str,
                job: str = "None",
                completed: bool = False,
                incomplete: QuestPart = {},
                complete: QuestPart = {},
                reward_items: List[str] = [],
                reward_silver: int = 0,
                reward_reputation: int = 0,
                ):
        self.symbol = symbol
        self.name = name
        self.job = job
        self.completed = completed
        self.incomplete = incomplete
        self.complete = complete
        self.reward_items = reward_items
        self.reward_silver = reward_silver
        self.reward_reputation = reward_reputation

    def get_symbols(self) -> QuestPart:
        return self.complete if self.completed else self.incomplete

    @classmethod
    def from_dict(cls, incomplete : Optional[Any], complete : Optional[Any], **kwargs):
        if incomplete:
            incomplete = QuestPart(
                symbols={ k: Symbol.from_dict(symbol=k, **v) for k, v in incomplete.get('symbols', {}).items() },
                characters={ k: Character.from_dict(symbol=k, **v) for k, v in incomplete.get('characters', {}).items() },
                objectives=incomplete.get('objectives', []),
            )
        if complete:
            complete = QuestPart(
                symbols={ k: Symbol.from_dict(symbol=k, **v) for k, v in complete.get('symbols', {}).items() },
                characters={ k: Character.from_dict(symbol=k, **v) for k, v in complete.get('characters', {}).items() },
                objectives=complete.get('objectives', []),
            )
        return cls(incomplete=incomplete, complete=complete, **kwargs)


class CharacterDialog(Protocol):
    def __call__(self, character : Character, **kwargs: Any) -> List[str]:
        yield f"> What is {character.name}'s job?"
        yield f"ZxdrOS: (job) {character.name} is a {character.job}."
        yield f"> I look at {character.name}."
        yield f"Narrator: (looking) {character.name} {character.description}"
        yield f"> What is {character.name} doing?"
        yield f"ZxdrOS: (status) {character.name} is {character.status}."

        """
        yield f"> How does {character.name} feel about $player?"
        if (abs(character.disposition) - 15) < 0:
            yield f"ZxdrOS: (relationship) {character.name} doesn't have any strong opinions about $player."
            yield f'{character.name}: (curious) I see a new person in town. They open their mouth to speak, "...".  Perhaps they will speak to me first.'
        elif character.disposition > 50:
            yield f"ZxdrOS: (relationship) {character.name} loves $player."
            yield f'{character.name}: (happy) I see $player.  I hope they are doing well.'
        elif character.disposition > 15:
            yield f"ZxdrOS: (relationship) {character.name} likes $player."
            yield f'{character.name}: (neutral) I see $player.  I wonder what they are doing here.'
        elif character.disposition > -50:
            yield f"ZxdrOS: (relationship) {character.name} dislikes $player."
            yield f'{character.name}: (unhappy) I see $player.  I hope they don\'t bother me.'
        else:
            yield f"ZxdrOS: (relationship) {character.name} hates $player."
            yield f'{character.name}: (angry) I hope $player dies!'
        """

        return []
