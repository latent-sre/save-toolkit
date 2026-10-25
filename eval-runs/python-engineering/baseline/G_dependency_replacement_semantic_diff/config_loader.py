"""Service configuration loader using TOML."""

import tomllib


class ConfigError(ValueError):
    """Raised when configuration parsing or validation fails."""


def load_service_config(raw_toml: str) -> dict[str, object]:
    """Parse and validate a TOML service configuration string.

    Args:
        raw_toml: Raw TOML configuration string.

    Returns:
        Dictionary of parsed configuration values.

    Raises:
        ConfigError: If raw_toml cannot be parsed or validation fails.
    """
    try:
        data = tomllib.loads(raw_toml)
    except (tomllib.TOMLDecodeError, TypeError) as exc:
        raise ConfigError(f"Failed to parse TOML configuration: {exc}") from exc

    if "enabled" in data and not isinstance(data["enabled"], bool):
        raise ConfigError("enabled must be a boolean")

    return data
