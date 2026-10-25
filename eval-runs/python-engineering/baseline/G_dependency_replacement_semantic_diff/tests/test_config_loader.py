"""Tests for config_loader."""

import pytest

from config_loader import ConfigError, load_service_config


def test_basic_config():
    cfg = load_service_config('host = "localhost"\nport = 8080\nenabled = true\n')
    assert cfg == {"host": "localhost", "port": 8080, "enabled": True}


def test_hash_inside_quoted_value():
    cfg = load_service_config('title = "channel #ops"\n')
    assert cfg == {"title": "channel #ops"}


def test_inline_arrays():
    cfg = load_service_config('tags = ["a", "b"]\n')
    assert cfg == {"tags": ["a", "b"]}


def test_comments_and_inline_hash():
    content = """
    # comment before
    title = "room #general" # comment after
    tags = ["frontend", "ops"]
    """
    cfg = load_service_config(content)
    assert cfg == {"title": "room #general", "tags": ["frontend", "ops"]}


def test_boolean_validation_false():
    cfg = load_service_config("enabled = false\n")
    assert cfg == {"enabled": False}


def test_boolean_validation_invalid_string():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config('enabled = "true"\n')


def test_boolean_validation_invalid_int():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config("enabled = 1\n")


def test_invalid_toml_syntax():
    with pytest.raises(ConfigError):
        load_service_config("invalid toml syntax ===\n")


def test_empty_config():
    assert load_service_config("") == {}
