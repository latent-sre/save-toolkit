import tomllib


class ConfigError(ValueError):
    pass


def _validate_booleans(data: dict[str, object]) -> None:
    for k, v in data.items():
        if k == 'enabled' and not isinstance(v, bool):
            raise ConfigError('enabled must be a boolean')
        if isinstance(v, dict):
            _validate_booleans(v)


def load_service_config(raw_toml: str) -> dict[str, object]:
    try:
        data = tomllib.loads(raw_toml)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f'Invalid TOML: {e}') from e

    _validate_booleans(data)
    return data
