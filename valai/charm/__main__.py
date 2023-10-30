# valai/charm/__main__.py

import logging

from .context import ContextInjection
from .database import DatabaseManager
from .scene import Scene

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    config = { 
        'database_uri': 'sqlite:///local/char.db',
        'scene_path': 'scene/verana',
        'player': '$player',
        'party': [],
        'location_name': 'Verana',
    } 
    db = DatabaseManager.from_config(**config)
    scene = Scene.from_db(db=db, **config)
    charm = ContextInjection.from_db(db, scene, **config)

    logger.info(scene.location)
    context_text = "Welcome to %verana%\n"
    context_text += "> Do you have any work for me?"
    expansion = charm.expand(context_text)
    expansion_state = expansion.get('state', 'error')
    if expansion_state == 'content' and 'content' in expansion:
        prompt =  expansion['content']
        logging.debug(f"Prompt Expanded:\n{prompt}")
    else:
        logging.warn("Non Content Response:", expansion)