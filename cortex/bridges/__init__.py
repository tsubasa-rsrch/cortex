"""Bridge adapters for integrating Cortex with external platforms."""

from .gemini import CortexGeminiBridge, GeminiConfig, ReasoningResult

__all__ = ["CortexGeminiBridge", "GeminiConfig", "ReasoningResult"]
