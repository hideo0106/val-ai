# valai/engine/grammar.py

import llama_cpp
from llama_cpp import LlamaGrammar
import logging
import os

logger = logging.getLogger(__name__)

def load_grammar(grammar_file : str, grammar_path : str, **kwargs) -> LlamaGrammar:
    return LlamaGrammar.from_file(os.path.join(grammar_path, grammar_file), verbose=False)
    
if __name__ == "__main__":
    grammar = load_grammar()