# valai/pinnacle/roster.py

from typing import Dict, List, Optional, Set

from .archetypes import get_narrator, get_zx
from .model import Character, Quest
from .symbol import Symbolizer


class Stats:
    health : int
    stamina : int
    awake : bool
    mood : str

    def __init__(self, health : int, stamina : int, awake : bool, mood : str) -> None:
        self.health = health
        self.stamina = stamina
        self.awake = awake
        self.mood = mood


class Actor:
    inventory : Dict[str, str]
    def __init__(self, sheet : Character, inventory : List[str] = []) -> None:
        self.sheet = sheet
        self.stats = Stats(100, 100, True, "neutral")
        self.inventory = {**{k: 'owned' for k in sheet.inventory}, **{k: 'owned' for k in inventory}}
        self.silver = int(sheet.silver)

    def add_item(self, item : str, **kwargs) -> str:
        if item in self.inventory:
            return 'duplicate'
        self.inventory[item] = 'new'
        return self.inventory[item]

    def remove_item(self, item : str, **kwargs) -> Optional[str]:
        if item not in self.inventory:
            return None
        return self.inventory.pop(item)

    def can_afford(self, cost : int, **kwargs) -> bool:
        return self.silver >= int(cost)
    
    def gain(self, silver : int, **kwargs) -> None:
        self.silver += silver

    def spend(self, silver : int, **kwargs) -> None:
        self.silver -= silver


class CharacterRoster:
    def __init__(self, player : Actor, game_master : Actor, narrator : Actor, characters : Dict[str, Actor]) -> None:
        self.game_master = game_master
        self.narrator = narrator
        self.player = player
        self.party : Set[str] = set()
        self.characters = characters
        self.quest_characters : Dict[str, Actor] = {}
        self.player_name = self.player.sheet.name
        self.game_master_name = self.game_master.sheet.name
        self.narrator_name = self.narrator.sheet.name

    def reset_scene(self):
        self.party = set()

    def get_actors(self, symbols : Optional[Set[str]]) -> Dict[str, Actor]:
        if symbols is None:
            return {**self.characters, **self.quest_characters}
        
        actors = {k: self.characters[k] for k in symbols if k in self.characters}
        actors.update({k: self.quest_characters[k] for k in symbols if k in self.quest_characters})
        return actors

    def get_actor(self, symbol) -> Optional[Actor]:
        return self.characters.get(symbol) if symbol in self.characters else self.quest_characters.get(symbol, None)
    
    def get_party(self) -> Dict[str, Actor]:
        return self.get_actors(self.party)
    
    def add_to_party(self, character_symbol : str) -> None:
        actor = self.get_actor(character_symbol)
        if actor is None:
            raise ValueError(f"Character {character_symbol} not in roster.")
        self.party.add(character_symbol)

    def remove_from_party(self, character_symbol : str) -> None:
        if character_symbol not in self.party:
            raise ValueError(f"Character {character_symbol} not in roster.")
        self.party.remove(character_symbol)

    def set_current_quest_characters(self, quests : Dict[str, Quest], **kwargs) -> None:
        for q, quest in quests.items():
            if quest.completed:
                for k, v in quest.complete.get('characters', {}).items():
                    if k not in self.quest_characters:
                        self.quest_characters[k] = Actor(v)
                    else:
                        self.quest_characters[k].sheet = v
            else:
                for k, v in quest.incomplete.get('characters', {}).items():
                    if k not in self.quest_characters:
                        self.quest_characters[k] = Actor(v)
                    else:
                        self.quest_characters[k].sheet = v

    @classmethod
    def from_symbolizer(cls, sym : Symbolizer) -> 'CharacterRoster':
        player = Actor(sym.player)
        game_master = Actor(get_zx())
        narrator = Actor(get_narrator())
        characters = {k: Actor(c) for k,c in sym.characters.items()}
        self = cls(player, game_master, narrator, characters)
        self.set_current_quest_characters(sym.quests)
        return self
