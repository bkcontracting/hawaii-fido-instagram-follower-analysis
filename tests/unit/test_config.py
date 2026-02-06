"""Tests for src/config.py — pipeline settings with env overrides."""
import os
import importlib


def test_default_batch_size():
    import src.config as config
    importlib.reload(config)
    assert config.BATCH_SIZE == 20


def test_default_max_subagents():
    import src.config as config
    importlib.reload(config)
    assert config.MAX_SUBAGENTS == 2


def test_default_max_retries():
    import src.config as config
    importlib.reload(config)
    assert config.MAX_RETRIES == 3


def test_env_override_batch_size():
    os.environ["BATCH_SIZE"] = "50"
    try:
        import src.config as config
        importlib.reload(config)
        assert config.BATCH_SIZE == 50
    finally:
        del os.environ["BATCH_SIZE"]


def test_env_override_max_subagents():
    os.environ["MAX_SUBAGENTS"] = "4"
    try:
        import src.config as config
        importlib.reload(config)
        assert config.MAX_SUBAGENTS == 4
    finally:
        del os.environ["MAX_SUBAGENTS"]


def test_env_override_max_retries():
    os.environ["MAX_RETRIES"] = "5"
    try:
        import src.config as config
        importlib.reload(config)
        assert config.MAX_RETRIES == 5
    finally:
        del os.environ["MAX_RETRIES"]
