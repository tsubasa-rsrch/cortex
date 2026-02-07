"""Default values for Cortex modules.

These can be overridden by passing custom values to each module.
All defaults are generic and not tied to any specific agent.
"""

# === Circadian Rhythm Defaults ===

CIRCADIAN_SUGGESTIONS = {
    "morning": [
        {"type": "check_inputs", "message": "Check incoming messages and notifications", "priority": "high"},
        {"type": "review", "message": "Review overnight events", "priority": "normal"},
    ],
    "afternoon": [
        {"type": "work", "message": "Continue active tasks", "priority": "high"},
        {"type": "create", "message": "Focus on creative work", "priority": "normal"},
    ],
    "evening": [
        {"type": "reflect", "message": "Reflect on today's activities", "priority": "high"},
        {"type": "organize", "message": "Organize notes and records", "priority": "normal"},
    ],
    "night": [
        {"type": "consolidate", "message": "Run memory consolidation", "priority": "high"},
        {"type": "rest", "message": "Reduce activity level", "priority": "low"},
    ],
}

CIRCADIAN_ACTIVITIES = {
    "morning": ["Check notifications", "Review agenda", "Process inbox"],
    "afternoon": ["Deep work", "Problem solving", "Implementation"],
    "evening": ["Daily review", "Note taking", "Planning tomorrow"],
    "night": ["Memory consolidation", "Background processing", "Quiet reflection"],
}


# === Decision Engine Defaults ===

AUTONOMOUS_ACTIVITIES = [
    {"name": "memory_review", "description": "Review and consolidate memories", "weight": 2.0},
    {"name": "research", "description": "Research topics of interest", "weight": 2.0},
    {"name": "write_notes", "description": "Write observations to notes", "weight": 1.0},
    {"name": "daily_summary", "description": "Generate daily event summary", "weight": 1.0},
    {"name": "idle", "description": "Rest (do nothing)", "weight": 0.5},
]


# === Notification Defaults ===

NOTIFICATION_ICONS = {
    "message": "\U0001f4ac",   # speech bubble
    "alert": "\U0001f6a8",     # siren
    "info": "\u2139\ufe0f",    # info
    "system": "\u2699\ufe0f",  # gear
    "schedule": "\u23f0",      # alarm clock
    "suggestion": "\U0001f4a1",  # lightbulb
}

PRIORITY_MARKS = {
    "urgent": "\u203c\ufe0f",  # double exclamation
    "high": "\u2757",          # exclamation
    "normal": "",
    "low": "\u00b7",           # middle dot
}
