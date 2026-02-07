"""Cortex configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CortexConfig:
    """Central configuration for all Cortex modules.

    Args:
        data_dir: Base directory for state files. Defaults to ~/.cortex/
        name: Agent name (used in logs and notifications).
    """
    data_dir: Path = field(default_factory=lambda: Path.home() / ".cortex")
    name: str = "agent"

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def state_file(self, filename: str) -> Path:
        """Get path for a state file within data_dir."""
        return self.data_dir / filename


# Global default config (can be overridden)
_config: Optional[CortexConfig] = None


def get_config() -> CortexConfig:
    """Get the global Cortex config (creates default if needed)."""
    global _config
    if _config is None:
        _config = CortexConfig()
    return _config


def set_config(config: CortexConfig) -> None:
    """Set the global Cortex config."""
    global _config
    _config = config
