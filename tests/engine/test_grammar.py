# tests/engine/test_read.py

import logging
import pytest
from valai.ioutil import CaptureFD
from valai.engine.llamaflow import FlowEngine
from valai.engine.grammar import load_grammar
from tests.config import default_config, EngineTestConfig

logger = logging.getLogger(__name__)


@pytest.fixture
def test_config() -> EngineTestConfig:
    """
    Pytest fixture to create a EngineTestConfig instance with default parameters.
    """
    return default_config()

@pytest.fixture
def default_flow_engine() -> FlowEngine:
    """
    Pytest fixture to create a FlowEngine instance with default parameters.
    """
    config = default_config()
    with CaptureFD() as co:
        flow_engine = FlowEngine.from_config(**config)
    return flow_engine

def test_grammar(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test reading a prompt from the engine using grammar.
    """
    prompt = "### Instruction: Output Goodnight Moon\n### Response:\n"
    grammar = load_grammar(**test_config)
    logger.info(f"Grammar rules: {grammar._n_rules}")
    rc = default_flow_engine.feed(prompt=prompt, **test_config)
    assert rc >= 0
    results = default_flow_engine.read(grammar=grammar, **test_config)
    logger.info(f"Results: {results}")
    assert all([a.strip() == b.strip() for a, b in zip(results, ['Hello', 'World', '\n'])])
    results = default_flow_engine.read(grammar=grammar, **test_config)
    logger.info(f"Results: {results}")
    assert len(results) == 0
    # Reset the grammar
    grammar.reset()
    results = default_flow_engine.read(grammar=grammar, **test_config)
    logger.info(f"Results: {results}")
    assert all([a.strip() == b.strip() for a, b in zip(results, ['Hello', 'World', '\n'])])
