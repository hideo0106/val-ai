# tests/config.py

import os
from typing import TypedDict

class EngineTestConfig(TypedDict):
    grammar_file: str
    resources_path: str
    model_path: str
    save_file: str
    model_file: str
    n_ctx: int
    n_batch: int

def default_config() -> EngineTestConfig:
    resources = "./resources"
    return {
        "model_path": "../llama/gguf",
        "resources_path": resources,
        "grammar_path": os.path.join(resources, "grammar"),
        "scene_path": os.path.join(resources, "scene"),
        "grammar_file": "test_grammar.gbnf",
        "scene_name": "novara",
        "model_file": "zephyr-7b-beta.Q8_0.gguf",
        "save_file": "local/test_save.txt",
        "n_ctx": 4096,
        "n_batch": 100,
    }