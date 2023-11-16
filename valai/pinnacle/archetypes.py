# valai/pinnacle/archetypes.py

from .model import Character

def get_zx():
    return Character(
        name="ZxdrOS",
        symbol="+zxdros+",
        title="ZxdrOS, the Game Master",
        related_symbols=[],
        job="Game Master",
        traits=["authoritative", 'dark', 'witty', 'cynical', 'angry'],
        location_symbol="=invalid=",
        description="is a computer program.  He looks like a shimmering vortex that only the player can see.",
        disposition=0,
        status="Watching $player",
        character_keywords=['zxdros']
    )

def get_narrator():
    return Character(
        name="Narrator",
        symbol="+narrator+",
        title="The Narrator",
        related_symbols=[],
        job="Narrator",
        traits=["descriptive", "expanatory", "informative", "narrative"],
        location_symbol="=invalid=",
        description="A disembodied voice.  A deep, calm voice of a shakespearian trained actor.",
        disposition=0,
        status="Telling the story",
        character_keywords=['narrator']
    )