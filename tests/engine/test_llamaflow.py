# tests/engine/test_llamaflow.py

import pytest
from valai.engine.llamaflow import FlowEngine
from tests.config import default_config, EngineTestConfig

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
    flow_engine = FlowEngine.from_config(**config)
    return flow_engine

def test_load_context(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test loading context from a file.
    """
    result = default_flow_engine.load_context(test_config['save_file'])
    assert result >= 0
    # Add more assertions here to validate the loaded context

def test_save_context(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test saving context to a file.
    """
    result = default_flow_engine.save_context(**test_config)
    assert result >= 0
    # Add more assertions here to validate the saved context

def test_clear_saved_context(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test clearing saved context.
    """
    result = default_flow_engine.clear_saved_context(**test_config)
    assert result == 0
    # Add more assertions here to validate the clearing of the saved context

# Add more tests as needed

# ... (previous code)
def test_token_clearance(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test token clearance calculation.
    """
    new_tokens = 50
    padding = 10
    clearance = default_flow_engine.token_clearance(new_tokens, padding)
    expected_clearance = default_flow_engine.n_ctx - default_flow_engine.n_past - new_tokens - padding
    assert clearance == expected_clearance

def test_reset(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test resetting the engine state.
    """
    default_flow_engine.reset()
    assert default_flow_engine.n_past == 0
    assert default_flow_engine.n_prev == 0
    assert default_flow_engine.session_tokens == []
    # Add more assertions to validate the reset state

def test_set_checkpoint(default_flow_engine, test_config):
    """
    Test setting a checkpoint.
    """
    checkpoint = "test_checkpoint"
    result = default_flow_engine.set_checkpoint(checkpoint, **test_config)
    assert result is True
    # Add more assertions to validate the checkpoint creation

def test_execute(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test executing a prompt.
    """
    prompt = "Test prompt"
    rc = default_flow_engine.execute(prompt)
    assert rc >= 0
    # Add more assertions to validate the execution result

def test_reload_turn(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test reloading a turn from a checkpoint.
    """
    checkpoint = "test_checkpoint"
    rc = default_flow_engine.reload_turn(checkpoint, **test_config)
    assert rc >= 0
    # Add more assertions to validate the reloading of the turn

def test_set_context(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test setting a context for the engine.
    """
    system_context = "test_context"
    prompt = "Test prompt for context"
    default_flow_engine.set_context(system_context, prompt)
    assert default_flow_engine.systems[system_context] == prompt

def test_prepare(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test preparing the engine with a system context.
    """
    system_context = "test_context"
    rc = default_flow_engine.prepare(system_context)
    assert rc >= 0
    # Add more assertions to validate the preparation of the engine

def test_feed(default_flow_engine : FlowEngine, test_config : EngineTestConfig):
    """
    Test feeding a prompt to the engine.
    """
    prompt = "Test prompt"
    rc = default_flow_engine.feed(prompt=prompt, **test_config)
    assert rc >= 0
