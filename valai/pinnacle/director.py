# valai/pinnacle/director.py

import logging
import random
import re
from typing import Optional, List, Dict

from .exception import DirectorError
from .roster import Actor, CharacterRoster
from .scene import Scene
from .symbol import Symbolizer

logger = logging.getLogger(__name__)


class SceneDirector:
    def __init__(self, sym : Symbolizer, roster : CharacterRoster):
        self.sym = sym
        self.roster = roster
        self.location_symbol = None
        self.scene = None

        # Speech rules
        self.narration = False
        self.rules = False
        self.converse = False
        self.converse_party = False
        self.trait = None
        
        self.speaker : Optional[Actor] = None
        self.audience : Optional[Actor] = None

        # Post-processing lines
        self.residue_messages = []
        self.chatter_messages = []

    def reset_scene(self):
        self.roster.reset_scene()
        self.narration = False
        self.rules = False
        self.converse = False
        self.converse_party = False
        self.trait = None
        self.speaker : Optional[Actor] = None
        self.audience : Optional[Actor] = None
        self.residue_messages = []
        self.chatter_messages = []

    def add_residue(self, message : str):
        self.residue_messages.append(message)

    def add_chatter(self, message : str):
        self.chatter_messages.append(message)

    def flush_residue(self) -> List[str]:
        result = self.residue_messages
        self.residue_messages = []
        return result

    def flush_chatter(self) -> List[str]:
        result = self.chatter_messages
        self.chatter_messages = []
        return result

    def set_scene(self, location_symbol : str, **kwargs):
        scene = Scene.from_symbolizer(location_symbol, roster=self.roster, sym=self.sym, **kwargs)
        self.location_symbol = location_symbol
        self.scene = scene
        logger.debug(f"Scene: {location_symbol} loaded with {len(scene.exits)} exits and {len(scene.characters)} characters.")

    def reload(self):
        pass

    def exit_keywords(self) -> List[str]:
        return list(self.scene.exit_keywords.keys())

    def character_keywords(self) -> List[str]:
        return list(self.scene.character_keywords.keys())

    def party_keywords(self) -> List[str]:
        return list([k for k, v in self.scene.character_keywords.items() if v in self.roster.party])

    def speaker_turn(self) -> Optional[str]:
        # The order of the turn should go:
        # -  The player (has already gone)
        # -  The game master, if rules
        # -  The other characters, if converse
        # -  Someone from the player's party, if converse_party
        # -  The narrator, if narration

        audience = self.roster.player_name
        if self.rules:
            speaker = self.roster.game_master_name
            format = f"{speaker} (to {audience}, "
            if self.trait is not None:
                format += f"{self.trait}): {self.roster.player.sheet.character_line()}"
                self.trait = None
        elif self.converse == True and self.audience is not None:
            speaker = self.audience.sheet.name
            format = f"{speaker} (to {audience}, "
            if self.trait is not None:
                format += f"{self.trait}): "
                self.trait = None
        elif self.converse_party == True and len(self.roster.party) > 0:
            member = random.choice(list(self.roster.party))
            actor = self.roster.get_actor(member)
            speaker = actor.sheet.name
            to_target = random.choice([audience, self.roster.player_name])
            audience = to_target
            format = f"{speaker} (to {audience}, "
            if self.trait is not None:
                format += f"{self.trait}): "
                self.trait = None
        elif self.narration:
            speaker = self.roster.narrator_name
            format = f"{speaker} (to {audience}, "
            if self.trait is not None:
                format += f"{self.trait}): "
                self.trait = None
        else:
            return None
        self.tick_speaker()
        return format
    
    def tick_speaker(self):
        if self.rules:
            self.rules = False
            self.narration = True
            self.trait = "descriptive"
        elif self.converse and self.audience is not None:
            self.converse = False
            self.trait = "observational"
        elif self.converse_party:
            self.converse_party = False
            self.trait = None
        elif self.narration:
            self.narration = False
            self.trait = None

    def look(self, target : Optional[str], **kwargs) -> str:
        if target is None:
            player_input = f"{self.roster.player_name} (to ZxdrOS, look): I look around.  Can you present me a long, detailed visual scene about the things and people I see?"
            self.narration = True
        else:
            player_input = f"{self.roster.player_name} (to ZxdrOS, look): I look {target}.  What do I see?"
            self.narration = True
        return player_input

    def search(self, target : str, **kwargs) -> str:
        player_input = f"{self.roster.player_name} (to ZxdrOS, search): I search {target}."
        self.rules = True
        self.narration = True
        return player_input

    def buy(self, item : str, price : int, **kwargs) -> str:
        # We need to check the price of the item, and if we have enough money, we can buy it.
        if self.roster.player.can_afford(price):
            player_input = f"{self.roster.player_name} (to ZxdrOS, buy): I buy {item} for {price} silver."
            self.roster.player.spend(price)
            self.roster.player.add_item(item)
            self.narration = True
        else:
            player_input = f"{self.roster.player_name} (to ZxdrOS, buy): I can't afford {item} for {price} silver."
            self.narration = True

    def cast(self, spell : str, target : Optional[str] = None, description : Optional[str] = None, **kwargs) -> str:
        if description is not None:
            player_input = f"{self.roster.player_name} (to ZxdrOS, cast): I open my spellbook and cast {spell} {description}.  Can I do it?"
        elif target is not None:
            player_input = f"{self.roster.player_name} (to ZxdrOS, cast): I open my spellbook and cast {spell} at {target}.  Can I do it?"
        else:
            player_input = f"{self.roster.player_name} (to ZxdrOS, cast): I open my spellbook and cast {spell}.  Can I do it?"
        if spell not in self.roster.player.sheet.spells:
            self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, checking): {self.roster.player.sheet.stat_line()} You don't know the {spell} spell.")
            self.trait = 'fizzled'
        elif description is not None:
            self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, checking): {self.roster.player.sheet.stat_line()} ZxdrOS (to $player, checking): You are a wizard, and know the {spell} spell.  You can {description}.")
            self.trait = 'spellcast'
        else:
            self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, checking): {self.roster.player.sheet.stat_line()} ZxdrOS (to $player, checking): You are a wizard, and know the {spell} spell.")
            self.trait = 'spellcast'
        self.narration = True
        return player_input

    def attack(self, target : str, **kwargs) -> str:
        player_input = f"{self.roster.player_name} (to ZxdrOS, attack): I attack {target}.  Do I succeed?"
        self.narration = True
        return player_input

    def use(self, target : str, **kwargs) -> str:
        player_input = f"{self.roster.player_name} (to ZxdrOS, use): I use {target}.  What happens?"
        self.narration = True
        return player_input

    def rest(self, target : Optional[str] = None, **kwargs) -> str:
        if target is None:
            player_input = f"{self.roster.player_name} (to ZxdrOS, tired): I want to camp for the night."
        else:
            player_input = f"{self.roster.player_name} (to ZxdrOS, tired): I want to sleep using {target}."
        self.converse_party = True
        self.narration = True
        return player_input

    def speak(self, target : str, dialog : str, override : Optional[Actor] = None, **kwargs) -> str:
        if override is not None:
            player_input = f"{self.roster.player_name} (to {override.sheet.name}, talk): {dialog}"
            self.converse = True
            self.audience = override
        else:
            actor = self.scene.actor_for_keyword(target)
            if actor is None:
                raise DirectorError(f"Character {target} not found.")
            player_input = f"{self.roster.player_name} (to {actor.sheet.name}, talk): {dialog}"
            self.converse = True
            self.audience = actor
            self.narration = True
        return player_input

    def travel(self, target : str, **kwargs) -> str:
        exit = self.scene.exit_for_keyword(target)
        if exit is None:
            raise DirectorError(f"Location {target} not found.")
        # TODO add the ability to mark a location as visited
        player_input = f"""{self.roster.player_name} (to ZxdrOS, travel):  I leave {self.scene.location.name} and I travel to {exit.name}.  What do I see?"""
        self.add_residue(exit.travel_line(self.roster.player.sheet))
        self.narration = True
        return player_input
    
    def party(self, target : str, did_join : bool, **kwargs) -> str:
        actor = self.scene.actor_for_keyword(target)
        if actor is None:
            raise DirectorError(f"Character {target} not found.")
        if did_join:
            player_input = f"{self.roster.player_name} (to ZxdrOS, party): I want {actor.sheet.name} to join my party."
            if actor.sheet.will_join or actor.sheet.disposition >= 50:
                logger.debug(f"Party Join: {actor.sheet.name} joins {self.roster.player_name}'s party.")
                self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, join): {actor.sheet.name} joins your party.  I wonder how they feel about that?")
                self.add_residue(actor.sheet.join_line(join=True))
                self.narration = True
                self.converse = True
                self.audience = actor
            else:
                self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, reject): {actor.sheet.name} won't join your party.")
                self.converse = True
                self.audience = actor
        else:
            player_input = f"{self.roster.player_name} (to ZxdrOS, party): I want {actor.sheet.name} out of my party."
            try:
                self.roster.remove_from_party(actor.sheet.symbol)
                self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, leave): {actor.sheet.name} left your party.")
                self.add_residue(actor.sheet.join_line(join=False))
                self.converse = True
                self.audience = actor
                self.narration = True
            except ValueError as e:
                self.add_chatter(f"{self.roster.game_master_name} (to {self.roster.player_name}, reject): {actor.sheet.name} isn't in your party.")

        return player_input

    @classmethod
    def from_config(cls, **kwargs):
        sym = Symbolizer.from_config(**kwargs)
        roster = CharacterRoster.from_symbolizer(sym)
        return cls(sym=sym, roster=roster)

def sample_response(line : Optional[str], **kwargs) -> Dict[str, str]:
    """Discritize the action from the line, returning our best guess as to what happened."""
    # Several things can happen on a response.
    # -  A character is noted to have spoken to a second.
    # -  The location can be changed.
    # -  The player can gain or lose an item.

    if line is None or len(line) == 0:
        return {"match": "empty"}

    dialogv1 = re.compile(r"(.*): \((.*)\) (.*)")
    dialogv2 = re.compile(r"(.*)\((.*)\): (.*)")
    dialogv3 = re.compile(r"(.*)\((.*), (.*)\): (.*)")
    locationv1 = re.compile(r"\[(.*) - (.*) has traveled (to|from) (.*) (\^.*\^)\]")
    itemv1 = re.compile(r"\[(.*) - (.*) (has gained|lost|owns) (?:a|an) (.*)\]")
    partyv1 = re.compile(r"\[(.*) - (.*) (has joined|has left|is in) the party\]")
    symbolv1 = re.compile(r"\[(.*) - (.*)\]")
    commv1 = re.compile(r"\[(.*)\]")
    sysv1 = re.compile(r"###(.*)")
    if dialogv3.match(line):
        match = dialogv3.match(line)
        speaker = match.group(1)
        audience = match.group(2)
        trait = match.group(3)
        said = match.group(4)
        if 'to ' in audience:
            audience = audience.replace("to ", '')
        return {"match": "dialog", "speaker": speaker, "audience": audience, "trait": trait, "said": said}
    elif dialogv1.match(line):
        match = dialogv1.match(line)
        speaker = match.group(1)
        trait = match.group(2)
        said = match.group(3)
        return {"match": "dialog", "speaker": speaker, "trait": trait, "said": said}
    elif dialogv2.match(line):
        match = dialogv2.match(line)
        speaker = match.group(1)
        audience = match.group(2)
        said = match.group(3)
        if 'to ' in audience:
            audience = audience.replace("to ", '')
            return {"match": "dialog", "speaker": speaker, "audience": audience, "said": said}
        else:
            return {"match": "dialog", "speaker": speaker, "trait": audience, "said": said}
    elif locationv1.match(line):
        logger.debug(f"Location Match: {line}")
        match = locationv1.match(line)
        actor = match.group(1)
        actor_name = match.group(2)
        direction = match.group(3)
        location_name = match.group(4)
        location = match.group(5)
        return {"match": "location", "actor": actor, "name": actor_name, "location_name": location_name, 
                "location": location, "direction": direction}
    elif itemv1.match(line):
        match = itemv1.match(line)
        actor = match.group(1)
        actor_name = match.group(2)
        gained_lost = match.group(3)
        item = match.group(4)
        return {"match": "item", "actor": actor, "name": actor_name, "gained_lost": gained_lost, "item": item}
    elif partyv1.match(line):
        match = partyv1.match(line)
        actor = match.group(1)
        actor_name = match.group(2)
        join = match.group(3)
        return {"match": "party", "actor": actor, "name": actor_name, "join": join}
    elif symbolv1.match(line):
        match = symbolv1.match(line)
        symbol = match.group(1)
        statement = match.group(2)
        return {"match": "symbol", "symbol": symbol, "statement": statement.strip()}
    elif commv1.match(line):
        match = commv1.match(line)
        statement = match.group(1)
        return {"match": "statement", "statement": statement.strip()}
    elif sysv1.match(line):
        match = sysv1.match(line)
        statement = match.group(1)
        return {"match": "system", "statement": statement.strip()}
    else:
        return {"match": "unmatched", "unknown": line}


