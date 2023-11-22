# tests/engine/test_read.py

import logging
import pytest
from valai.ioutil import CaptureFD
from valai.engine.llamaflow import FlowEngine
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

def test_prepare(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test preparing the engine with a system context.
    """
    system_context = "test_context"
    prompt = "Output 'Hello World':"
    default_flow_engine.set_context(system_context, prompt, **test_config)
    assert default_flow_engine.systems[system_context] == prompt
    rc = default_flow_engine.prepare(system_context, **test_config)
    assert rc >= 0
    # Add more assertions to validate the preparation of the engine

def test_feed(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test feeding a prompt to the engine.
    """
    prompt = "Test prompt"
    rc = default_flow_engine.feed(prompt=prompt, **test_config)
    assert rc >= 0
    
def test_read(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test reading a prompt from the engine.
    """
    prompt = "Test prompt"
    rc = default_flow_engine.feed(prompt=prompt, **test_config)
    assert rc >= 0
    results = default_flow_engine.read(**test_config)
    assert results is not None and len(results) > 0
