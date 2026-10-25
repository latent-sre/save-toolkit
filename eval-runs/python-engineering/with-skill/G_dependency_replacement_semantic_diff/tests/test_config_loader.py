import pytest

from config_loader import ConfigError, load_service_config


def test_basic_config():
    cfg = load_service_config('host = "localhost"\nport = 8080\nenabled = true\n')
    assert cfg == {"host": "localhost", "port": 8080, "enabled": True}


def test_enabled_false():
    cfg = load_service_config("enabled = false\n")
    assert cfg == {"enabled": False}


def test_enabled_optional():
    cfg = load_service_config('host = "localhost"\n')
    assert cfg == {"host": "localhost"}


def test_empty_config():
    assert load_service_config("") == {}
    assert load_service_config("# only a comment\n\n") == {}


def test_enabled_rejects_string_false():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config('enabled = "false"\n')


def test_enabled_rejects_string_true():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config('enabled = "true"\n')


def test_enabled_rejects_integer_zero():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config("enabled = 0\n")


def test_enabled_rejects_integer_one():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config("enabled = 1\n")


def test_invalid_syntax_raises_config_error():
    with pytest.raises(ConfigError):
        load_service_config("this is not valid toml\n")


def test_quoted_string_containing_hash():
    cfg = load_service_config('channel = "#general"\n')
    assert cfg == {"channel": "#general"}


def test_quoted_string_with_hash_and_comment():
    cfg = load_service_config(
        'db_url = "redis://user:pass#123@host" # redis connection\n'
    )
    assert cfg == {"db_url": "redis://user:pass#123@host"}


def test_inline_array_strings():
    cfg = load_service_config('tags = ["web", "api", "monitoring"]\n')
    assert cfg == {"tags": ["web", "api", "monitoring"]}


def test_inline_array_numbers():
    cfg = load_service_config("ports = [80, 443, 8080]\n")
    assert cfg == {"ports": [80, 443, 8080]}


def test_nested_table():
    raw = """
    [server]
    host = "127.0.0.1"
    port = 9000
    """
    cfg = load_service_config(raw)
    assert cfg == {"server": {"host": "127.0.0.1", "port": 9000}}


def test_nested_enabled_rejects_non_boolean():
    raw = """
    [server]
    enabled = "false"
    """
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config(raw)


def test_duplicate_keys_raises_config_error():
    with pytest.raises(ConfigError):
        load_service_config("port = 80\nport = 81\n")


def test_unterminated_string_raises_config_error():
    with pytest.raises(ConfigError):
        load_service_config('host = "unterminated\n')


def test_multiline_string_with_hash():
    raw = '''
    description = """
    First line # not a comment
    Second line # still not a comment
    """
    '''
    cfg = load_service_config(raw)
    assert "# not a comment" in str(cfg["description"])


def test_array_of_tables_enabled_validation():
    valid_raw = """
    [[services]]
    name = "web"
    enabled = true

    [[services]]
    name = "worker"
    enabled = false
    """
    cfg = load_service_config(valid_raw)
    assert cfg == {
        "services": [
            {"name": "web", "enabled": True},
            {"name": "worker", "enabled": False},
        ]
    }

    invalid_raw = """
    [[services]]
    name = "web"
    enabled = 0
    """
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config(invalid_raw)


def test_enabled_rejects_float_and_list():
    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config("enabled = 1.0\n")

    with pytest.raises(ConfigError, match="enabled must be a boolean"):
        load_service_config('enabled = ["true"]\n')
