"""Bridge adapters for integrating Cortex with external platforms."""

from .gemini import CortexGeminiBridge, GeminiConfig, ReasoningResult
from .cosmos import CortexCosmosBridge, CosmosConfig, EgocentricResult

__all__ = [
    "CortexGeminiBridge", "GeminiConfig", "ReasoningResult",
    "CortexCosmosBridge", "CosmosConfig", "EgocentricResult",
]
