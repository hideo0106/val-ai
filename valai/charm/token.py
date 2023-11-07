# valai/charm/token.py

from collections import defaultdict
import logging
import numpy as np
import pandas as pd
import re
from typing import Set, Dict, List, Tuple

logger = logging.getLogger(__name__)

def tokenize_history(history : List[str], offset : int = 0, **kwargs) -> List[Tuple[int, str, str, str, str, str]]:
    return list(generate_tokens(history, offset, **kwargs))

def generate_tokens(history : List[str], offset : int = 0, **kwargs) -> List[Tuple[int, str, str, str, str, str]]:
    for i, h in enumerate(history):
        # Match a symbol, player indicator, value without sentiment, or value with sentiment
        symbols = re.match(r'\[([^\s]+) - (.+)\]', h)
        player = re.match(r'> (.+)', h)
        codex = re.match(r'Codex: ```(.+)```', h)
        dialog = re.match(r'(.+):\s*\((.*?)\)\s*(.+)', h)
        dialog_nd = re.match(r'(.+):\s*(.+)', h)

        source, token, name, sentiment, value = None, None, None, None, None

        if symbols is not None:
            source = 'symbol'
            token = symbols.group(1)
            value = symbols.group(2).strip()
        elif codex is not None:
            source = 'codex'
            sentiment = None
            token = '#codex#'
            value = codex.group(1)
        elif player is not None:
            source = 'player'
            sentiment = None
            token = '$player$'
            name = '$player'
            value = player.group(1).strip()
        elif dialog is not None:
            source = 'dialog'
            name = dialog.group(1)
            sentiment = dialog.group(2)
            token = f'+{name.lower()}+'
            value = dialog.group(3).strip()
        elif dialog_nd is not None:
            source = 'dialog'
            sentiment = None
            name = dialog_nd.group(1)
            token = f'+{name.lower()}+'
            value = dialog_nd.group(2).strip()

        if source:
            yield i + offset, source, token, name, sentiment, value
        else:
            print("Unmatched", h)
        
    return []

class TokenFeatures:
    """TokenFeatures tokenizes our history"""
    def __init__(self, history : List[str], tokens : Tuple[int, str, str, str, str, str], 
                 characters : Set[str], cflow : Dict[str, List[int]], mflow : Dict[str, List[int]], 
                 pflow : Dict[str, List[int]], dflow : Dict[str, List[float]]):
        self.history = history
        self.characters = characters
        self.cflow = cflow
        self.mflow = mflow
        self.pflow = pflow
        self.dflow = dflow
        self.filter_characters = ['$player', 'ZxdrOS', 'Narrator']

    def get_scores(self, **kwargs) -> Dict[str, int]:
        score = defaultdict(int)
        for c in self.characters:
            score[c] = np.max(self.dflow[c])

        return score

    def get_scenes(self, scene_min_lines : int = 4, scene_max_gap : int = 15, **kwargs) -> Dict[str, List[Tuple[int, int]]]:
        # This is a vector that contains if a particular character is relevant in the current scene
        # Our objective is to determine clean scene cutlines.  Each scene needs to be scanned for continuous segments where this vector is true.
        df = pd.DataFrame({c: self.dflow[c] > 0 for c in self.characters})

        filtered_characters = [c for c in self.characters if c not in self.filter_characters]

        # First, we need to find the indices where the scene changes
        ed = defaultdict(list)
        for c in filtered_characters:
            # Find the line segments for our vector.  We want to find the indices where the vector changes from 0 to 1 or 1 to 0
            last = False
            last_ix = None
            row = []
            for i, present in enumerate(df[c]):
                if last != present:
                    if present == True:
                        last_ix = i
                        last = present
                    else:
                        row.append((last_ix, i))
                        last = present
                        last_ix = None
            if last_ix is not None:
                row.append((last_ix, i))
            # Now that we have our list, we need to merge any segments with small gaps
            def merge_gaps(rowdata : List[Tuple[int, int]]):
                skip = False
                cs = 0
                ce = 0
                for i in range(len(rowdata)):
                    s, e = rowdata[i]
                    if cs == 0:
                        cs = s
                        ce = e
                        continue
                    if ce <= (s - scene_max_gap):
                        # This scene is too far away, yield the last one
                        yield (cs, ce)
                        cs = s
                        ce = e
                        continue
                    elif (ce - cs) < scene_min_lines:
                        # Throw the last scene away
                        logger.debug(f"Skipping small scene {cs} {ce}")
                    else:
                        # Continue to let this scene grow
                        ce = e
                if (ce - cs) >= scene_min_lines:
                    yield (cs, ce)
            
            updated = row.copy()
            last = updated
            while True:
                updated = list(merge_gaps(last))
                if len(updated) == len(last):
                    logger.debug(f"Scene {c} converged: {len(updated)}")
                    break
                last = updated

            ed[c] = updated
            
        return ed

    def scene_documents(self, **kwargs) -> Dict[str, Tuple[str, int, int, int, float, float, float]]:
        char_score = defaultdict(lambda: defaultdict(list))
        char_matches = defaultdict(list)
        char_documents = defaultdict(list)
        char_scenes = defaultdict(list)

        scores = self.get_scores()

        for char, scene in self.get_scenes().items():
            for i, (start, end) in enumerate(scene):
                char_scenes[char].append((start, end))
                score = 0
                for ix in range(start, end):
                    matches = len(tuple(re.finditer(char, self.history[ix])))
                    score += matches
                    char_score[char][i].append(matches)
                char_matches[char].append(score)
                char_documents[char].append(end - start)

        scored_documents = list()
        for k, v in char_documents.items():
            for d, c in enumerate(v):
                score = scores[k]
                m = char_matches[k][d]
                s, e = char_scenes[k][d]
                scored_documents.append((k, d, s, e, float(m), float(c), score))

        return scored_documents
            
    @classmethod
    def from_history(cls, history : List[str],
                    w_conversations : int = 5, w_mentions : int = 3, **kwargs):
        tokens = tokenize_history(history, **kwargs)
        characters = set()
        cflow : Dict[str, List[float]]= {}
        mflow : Dict[str, List[float]]= {}
        pflow : Dict[str, List[float]]= {}
        dflow : Dict[str, List[float]]= {}

        # Determine our characters
        for h in tokens:
            ix, source, token, name, sentiment, value = h
            if source in ['dialog', 'player']:
                characters.add(name)
            
        # Build our feature vectors
        for c in characters:
            conversation = [1 if h[3] == c else 0 for h in tokens]
            mentions = [1 if h[1] != 'symbol' and re.search(c, h[5]) is not None else 0 for h in tokens]
            cflow[c] = conversation
            mflow[c] = mentions
            if len(conversation) == 0:
                dflow[c] = []
            else:
                sc = np.convolve(cflow[c], np.ones(w_conversations), 'same')
                sm = np.convolve(mflow[c], np.ones(w_mentions), 'same')
                dflow[c] = sc + sm

        # Pflow is our player and who he is talking to.  Edges for '$player' denote turn start.
        pflow['$player'] = [1 if h[1] == 'player' else 0 for h in tokens]
        for c in characters:
            pflow[c] = [1 if dflow[c][i] > 0 else 0 for i in range(len(dflow[c]))]

        return cls(history, tokens, characters, cflow, mflow, pflow, dflow)