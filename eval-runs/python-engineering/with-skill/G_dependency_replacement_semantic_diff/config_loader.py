import tomllib


class ConfigError(ValueError):
    """Raised when configuration parsing or validation fails."""


def load_service_config(raw_toml: str) -> dict[str, object]:
    """Parse a TOML configuration string and validate service settings.

    Preserves ConfigError exception contract and boolean validation on 'enabled'.
    """
    try:
        data = tomllib.loads(raw_toml)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML: {exc}") from exc

    if "enabled" in data and not isinstance(data["enabled"], bool):
        raise ConfigError("enabled must be a boolean")

    return data
