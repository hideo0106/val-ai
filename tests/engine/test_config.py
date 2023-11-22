# tests/engine/test_config.py

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
def default_flow_engine():
    """
    Pytest fixture to create a FlowEngine instance with default parameters.
    """
    config = default_config()
    flow_engine = FlowEngine.from_config(**config)
    return flow_engine

def test_get_mparams_default():
    """
    Test the get_mparams method with default parameters.
    """
    mparams = FlowEngine.get_mparams()
    assert mparams is not None

def test_get_mparams_custom():
    """
    Test the get_mparams method with custom parameters.
    """
    custom_params = {
        'n_gpu_layers': 2,
        'main_gpu': 1,
    }
    mparams = FlowEngine.get_mparams(**custom_params)
    assert mparams is not None
    assert mparams.n_gpu_layers == custom_params['n_gpu_layers']
    assert mparams.main_gpu == custom_params['main_gpu']

def test_get_cparams_default():
    """
    Test the get_cparams method with default parameters.
    """
    cparams = FlowEngine.get_cparams()
    assert cparams is not None

def test_get_cparams_custom():
    """
    Test the get_cparams method with custom parameters.
    """
    custom_params = {
        'seed': 12345,
        'n_ctx': 2048,
    }
    cparams = FlowEngine.get_cparams(**custom_params)
    assert cparams is not None
    assert cparams.seed == custom_params['seed']
    assert cparams.n_ctx == custom_params['n_ctx']

def test_from_config(test_config):
    """
    Test creating a FlowEngine instance using from_config method.
    """
    flow_engine = FlowEngine.from_config(**test_config)
    assert flow_engine is not None
    assert flow_engine.model is not None
    assert flow_engine.ctx is not None
