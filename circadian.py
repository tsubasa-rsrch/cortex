"""Circadian rhythm system for AI agents.

Maps time-of-day to behavioral modes, inspired by human cortisol/melatonin
cycles. Each mode carries suggestions, recommended activities, and an
energy level indicator.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from .config import get_config
from .defaults import CIRCADIAN_SUGGESTIONS, CIRCADIAN_ACTIVITIES

STATE_FILENAME = "circadian_state.json"


class CircadianMode(Enum):
    """Time-of-day behavioral modes."""
    MORNING = "morning"      # 06-12: Information gathering (cortisol high)
    AFTERNOON = "afternoon"  # 12-18: Focused work (peak concentration)
    EVENING = "evening"      # 18-24: Reflection and review (winding down)
    NIGHT = "night"          # 00-06: Memory consolidation (melatonin high)


# Default mode metadata
_DEFAULT_MODE_META = {
    CircadianMode.MORNING: {
        "name": "Morning",
        "icon": "\U0001f305",       # sunrise
        "description": "Information gathering and external checks",
        "energy_level": "rising",
    },
    CircadianMode.AFTERNOON: {
        "name": "Afternoon",
        "icon": "\u2600\ufe0f",     # sun
        "description": "Deep work and implementation",
        "energy_level": "peak",
    },
    CircadianMode.EVENING: {
        "name": "Evening",
        "icon": "\U0001f306",       # cityscape at dusk
        "description": "Reflection and organizing",
        "energy_level": "declining",
    },
    CircadianMode.NIGHT: {
        "name": "Night",
        "icon": "\U0001f319",       # crescent moon
        "description": "Memory consolidation and quiet thought",
        "energy_level": "low",
    },
}


class CircadianRhythm:
    """Manages time-based behavioral modes.

    Args:
        config: Optional CortexConfig. Uses global config if not provided.
        suggestions: Dict mapping mode name to list of suggestion dicts.
        activities: Dict mapping mode name to list of activity strings.
        mode_meta: Dict mapping CircadianMode to metadata dict.
    """

    def __init__(
        self,
        config=None,
        suggestions: Optional[Dict[str, list]] = None,
        activities: Optional[Dict[str, list]] = None,
        mode_meta: Optional[Dict[CircadianMode, Dict]] = None,
    ):
        self._config = config or get_config()
        self._state_file = self._config.state_file(STATE_FILENAME)
        self.suggestions = suggestions or CIRCADIAN_SUGGESTIONS
        self.activities = activities or CIRCADIAN_ACTIVITIES
        self.mode_meta = mode_meta or _DEFAULT_MODE_META

        self.current_mode: Optional[CircadianMode] = None
        self.last_mode_change: Optional[datetime] = None
        self.mode_history: List[Dict] = []
        self._load_state()

    def _get_mode_for_hour(self, hour: int) -> CircadianMode:
        """Map hour (0-23) to a circadian mode."""
        if 6 <= hour < 12:
            return CircadianMode.MORNING
        elif 12 <= hour < 18:
            return CircadianMode.AFTERNOON
        elif 18 <= hour < 24:
            return CircadianMode.EVENING
        else:
            return CircadianMode.NIGHT

    def check_and_update(self) -> Dict[str, Any]:
        """Check current time and update mode if needed.

        Returns:
            Dict with keys: mode, config, changed, timestamp, (old_mode if changed).
        """
        now = datetime.now()
        new_mode = self._get_mode_for_hour(now.hour)
        meta = self.mode_meta.get(new_mode, {})

        result = {
            "mode": new_mode,
            "config": {
                **meta,
                "suggestions": self.suggestions.get(new_mode.value, []),
                "activities": self.activities.get(new_mode.value, []),
            },
            "changed": False,
            "timestamp": now.isoformat(),
        }

        if self.current_mode != new_mode:
            old_mode = self.current_mode
            self.current_mode = new_mode
            self.last_mode_change = now
            self.mode_history.append({
                "from": old_mode.value if old_mode else None,
                "to": new_mode.value,
                "timestamp": now.isoformat(),
            })
            self.mode_history = self.mode_history[-20:]
            result["changed"] = True
            result["old_mode"] = old_mode
            self._save_state()

        return result

    def get_current_suggestions(self) -> List[Dict]:
        """Get suggestions for the current mode."""
        if not self.current_mode:
            self.check_and_update()
        return self.suggestions.get(self.current_mode.value, [])

    def get_current_activities(self) -> List[str]:
        """Get recommended activities for the current mode."""
        if not self.current_mode:
            self.check_and_update()
        return self.activities.get(self.current_mode.value, [])

    def get_status(self) -> Dict[str, Any]:
        """Get full status of the circadian system."""
        if not self.current_mode:
            self.check_and_update()
        meta = self.mode_meta.get(self.current_mode, {})
        return {
            "mode": self.current_mode.value if self.current_mode else None,
            "name": meta.get("name", ""),
            "icon": meta.get("icon", ""),
            "description": meta.get("description", ""),
            "energy_level": meta.get("energy_level", ""),
            "last_change": (
                self.last_mode_change.isoformat() if self.last_mode_change else None
            ),
            "activities": self.activities.get(
                self.current_mode.value if self.current_mode else "", []
            ),
        }

    def _load_state(self) -> None:
        if self._state_file.exists():
            try:
                with open(self._state_file, "r") as f:
                    data = json.load(f)
                mode_str = data.get("current_mode")
                if mode_str:
                    self.current_mode = CircadianMode(mode_str)
                if data.get("last_mode_change"):
                    self.last_mode_change = datetime.fromisoformat(
                        data["last_mode_change"]
                    )
                self.mode_history = data.get("mode_history", [])
            except Exception:
                pass

    def _save_state(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                "current_mode": (
                    self.current_mode.value if self.current_mode else None
                ),
                "last_mode_change": (
                    self.last_mode_change.isoformat()
                    if self.last_mode_change
                    else None
                ),
                "mode_history": self.mode_history,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self._state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
