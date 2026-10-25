import pytest

from config_loader import ConfigError, load_service_config


def test_basic_config():
    cfg = load_service_config('host = "localhost"\nport = 8080\nenabled = true\n')
    assert cfg == {"host": "localhost", "port": 8080, "enabled": True}


def test_hash_inside_quoted_string():
    cfg = load_service_config('title = "channel #ops"\n')
    assert cfg == {"title": "channel #ops"}


def test_inline_arrays():
    cfg = load_service_config('tags = ["a", "b"]\n')
    assert cfg == {"tags": ["a", "b"]}


def test_comment_after_value():
    cfg = load_service_config('host = "localhost" # server host\n')
    assert cfg == {"host": "localhost"}


def test_enabled_boolean_validation():
    # Valid booleans
    assert load_service_config("enabled = true") == {"enabled": True}
    assert load_service_config("enabled = false") == {"enabled": False}

    # Non-boolean enabled values must raise ConfigError
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config("enabled = 1")

    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config('enabled = "true"')


def test_invalid_toml_raises_config_error():
    with pytest.raises(ConfigError):
        load_service_config("broken = [")
