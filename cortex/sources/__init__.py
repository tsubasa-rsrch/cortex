"""Cortex event sources."""

from .base import Event, BaseSource

# ReachyMini sources are optional (require reachy-mini SDK)
try:
    from .reachy import ReachyCameraSource, ReachyAudioSource, ReachyIMUSource
    _REACHY_AVAILABLE = True
except ImportError:
    _REACHY_AVAILABLE = False

__all__ = ["Event", "BaseSource"]

if _REACHY_AVAILABLE:
    __all__ += ["ReachyCameraSource", "ReachyAudioSource", "ReachyIMUSource"]
