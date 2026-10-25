import pytest

from config_loader import ConfigError, load_service_config


def test_basic_config():
    cfg = load_service_config('host = "localhost"\nport = 8080\nenabled = true\n')
    assert cfg == {'host': 'localhost', 'port': 8080, 'enabled': True}


def test_quoted_string_containing_hash():
    cfg = load_service_config('channel = "#general"\nkey = "val#123"\n')
    assert cfg == {'channel': '#general', 'key': 'val#123'}


def test_inline_arrays():
    cfg = load_service_config('servers = ["srv-1", "srv-2"]\nports = [80, 443]\n')
    assert cfg == {'servers': ['srv-1', 'srv-2'], 'ports': [80, 443]}


def test_comments_and_blank_lines():
    toml_str = """
    # Service settings
    host = "127.0.0.1" # local host

    enabled = false
    """
    cfg = load_service_config(toml_str)
    assert cfg == {'host': '127.0.0.1', 'enabled': False}


def test_strict_boolean_validation_rejects_string():
    with pytest.raises(ConfigError, match='enabled must be a boolean'):
        load_service_config('enabled = "false"\n')

    with pytest.raises(ConfigError, match='enabled must be a boolean'):
        load_service_config('enabled = "true"\n')


def test_strict_boolean_validation_rejects_integer():
    with pytest.raises(ConfigError, match='enabled must be a boolean'):
        load_service_config('enabled = 1\n')

    with pytest.raises(ConfigError, match='enabled must be a boolean'):
        load_service_config('enabled = 0\n')


def test_syntax_error_raises_config_error():
    with pytest.raises(ConfigError):
        load_service_config('invalid toml syntax ===\n')
