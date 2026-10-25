import tomllib


class ConfigError(ValueError):
    pass


def _validate_booleans(data: dict[str, object]) -> None:
    for k, v in data.items():
        if k == "enabled" and not isinstance(v, bool):
            raise ConfigError("enabled must be a boolean")
        if isinstance(v, dict):
            _validate_booleans(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    _validate_booleans(item)


def load_service_config(raw_toml: str) -> dict[str, object]:
    try:
        result = tomllib.loads(raw_toml)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(str(exc)) from exc

    _validate_booleans(result)
    return result
