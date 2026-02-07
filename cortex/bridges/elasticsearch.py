"""Cortex-Elasticsearch Bridge.

Connects Cortex perception modules to Elasticsearch for:
1. Time-series event indexing (filtered by HabituationFilter)
2. Agent Builder context injection (CircadianRhythm + NotificationQueue)
3. Periodic ES|QL jobs via Scheduler

Architecture:
    Physical World → Cortex (filter/prioritize) → Elasticsearch (store/search)
                                                 → Agent Builder (reason/act)

Usage:
    from cortex.bridges.elasticsearch import CortexElasticBridge

    bridge = CortexElasticBridge(
        es_url="https://your-cluster.es.io:443",
        api_key="your-api-key",
        index_prefix="cortex-events"
    )

    # Index a filtered event
    bridge.index_event(event)

    # Get context for Agent Builder conversation
    context = bridge.get_agent_context()

    # Run the full perception loop
    bridge.run_perception_loop(sources=[camera, audio])
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..sources.base import Event, BaseSource
from ..habituation import HabituationFilter
from ..circadian import CircadianRhythm
from ..decision import DecisionEngine
from ..notifications import NotificationQueue
from ..scheduler import Scheduler


@dataclass
class ESConfig:
    """Elasticsearch connection configuration."""
    es_url: str = ""
    api_key: str = ""
    index_prefix: str = "cortex-events"
    kibana_url: str = ""
    mock_mode: bool = True  # True = no real ES connection


@dataclass
class IndexedEvent:
    """An event after being indexed to Elasticsearch."""
    event: Event
    doc_id: str
    index_name: str
    timestamp: str
    indexed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CortexElasticBridge:
    """Bridge between Cortex perception and Elasticsearch.

    Filters sensor events through Cortex's cognitive modules before
    indexing to Elasticsearch, reducing noise and prioritizing
    what matters.

    Integration points:
    1. HabituationFilter → Event Ingestion: Filter noisy sensors before indexing
    2. CircadianRhythm → Agent Behavior: Adjust system prompts by time of day
    3. DecisionEngine → Tool Selection: Pre-filter Agent Builder tools
    4. NotificationQueue → Conversation Context: Inject background events
    5. Scheduler → Periodic ES|QL Jobs: Generate periodic reports
    """

    def __init__(self, es_config: Optional[ESConfig] = None):
        self.es_config = es_config or ESConfig()

        # Cortex modules
        self.habituation = HabituationFilter()
        self.circadian = CircadianRhythm()
        self.circadian.check_and_update()  # Initialize mode
        self.decision = DecisionEngine()
        self.notifications = NotificationQueue()
        self.scheduler = Scheduler()

        # State
        self._indexed_events: List[IndexedEvent] = []
        self._event_counter = 0
        self._http_client = None

        # Register periodic tasks
        self.scheduler.register(
            "es_health_check", 300,  # Every 5 minutes
            self._health_check
        )

    def _get_index_name(self) -> str:
        """Generate time-based index name (e.g., cortex-events-2026.02.07)."""
        date_str = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        return f"{self.es_config.index_prefix}-{date_str}"

    def _event_to_document(self, event: Event) -> Dict[str, Any]:
        """Convert a Cortex Event to an Elasticsearch document."""
        return {
            "@timestamp": event.timestamp.isoformat() if event.timestamp else datetime.now(timezone.utc).isoformat(),
            "source": event.source,
            "type": event.type,
            "content": event.content,
            "author": event.author,
            "url": event.url,
            "priority": event.priority,
            "raw_data": event.raw_data or {},
            "cortex": {
                "circadian_mode": self.circadian.current_mode.value,
                "habituation_passed": True,  # Only indexed events passed the filter
            }
        }

    def filter_event(self, event: Event) -> Optional[Event]:
        """Apply Cortex perception filters to an event.

        Returns the event if it passes filters, None if filtered out.
        This is the core value proposition: not everything gets indexed.
        """
        # Habituation filter: is this stimulus novel enough?
        value = event.priority
        if hasattr(event, 'raw_data') and event.raw_data:
            value = event.raw_data.get('diff', event.raw_data.get('volume', event.priority))

        should_alert, reason = self.habituation.should_notify(event.source, value)
        if not should_alert:
            return None

        return event

    def index_event(self, event: Event) -> Optional[IndexedEvent]:
        """Filter and index an event to Elasticsearch.

        Returns IndexedEvent if indexed, None if filtered out.
        """
        # Apply perception filter
        filtered = self.filter_event(event)
        if filtered is None:
            return None

        # Convert to ES document
        doc = self._event_to_document(filtered)
        index_name = self._get_index_name()

        if self.es_config.mock_mode:
            # Mock mode: store locally
            self._event_counter += 1
            doc_id = f"mock-{self._event_counter}"
            indexed = IndexedEvent(
                event=filtered,
                doc_id=doc_id,
                index_name=index_name,
                timestamp=doc["@timestamp"]
            )
            self._indexed_events.append(indexed)

            # Also push to notification queue
            self.notifications.push(
                filtered.type,
                f"[ES] {filtered.content}",
                "normal" if filtered.priority < 7 else "urgent",
                {"doc_id": doc_id, "index": index_name}
            )
            return indexed
        else:
            # Real ES connection
            return self._index_to_es(filtered, doc, index_name)

    def _index_to_es(self, event: Event, doc: Dict, index_name: str) -> Optional[IndexedEvent]:
        """Index document to real Elasticsearch cluster."""
        try:
            import urllib.request
            import ssl

            url = f"{self.es_config.es_url}/{index_name}/_doc"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"ApiKey {self.es_config.api_key}",
            }

            data = json.dumps(doc).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")

            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                result = json.loads(resp.read())
                doc_id = result.get("_id", "unknown")
                return IndexedEvent(
                    event=event,
                    doc_id=doc_id,
                    index_name=index_name,
                    timestamp=doc["@timestamp"]
                )
        except Exception as e:
            self.notifications.push(
                "error",
                f"ES index failed: {e}",
                "urgent",
                {"error": str(e)}
            )
            return None

    def get_agent_context(self) -> Dict[str, Any]:
        """Build context for Agent Builder conversation injection.

        This is injected into the Agent Builder's system prompt or
        conversation context so the agent knows what Cortex has observed.
        """
        circadian_status = self.circadian.check_and_update()
        unread = self.notifications.get_unread()
        suggestions = self.circadian.get_current_suggestions()

        recent_events = self._indexed_events[-10:] if self._indexed_events else []

        context = {
            "cortex_perception": {
                "circadian_mode": self.circadian.current_mode.value,
                "suggestions": suggestions,
                "unread_notifications": len(unread),
                "recent_events": [
                    {
                        "source": ie.event.source,
                        "type": ie.event.type,
                        "content": ie.event.content,
                        "priority": ie.event.priority,
                        "timestamp": ie.timestamp,
                    }
                    for ie in recent_events
                ],
                "perception_summary": self._build_summary(recent_events),
            }
        }
        return context

    def _build_summary(self, recent_events: List[IndexedEvent]) -> str:
        """Build a natural language summary of recent perceptions."""
        if not recent_events:
            return "No recent events detected."

        event_types = {}
        for ie in recent_events:
            t = ie.event.type
            event_types[t] = event_types.get(t, 0) + 1

        parts = []
        for etype, count in event_types.items():
            parts.append(f"{count} {etype} event(s)")

        mode = self.circadian.current_mode.value
        return f"[{mode} mode] Detected: {', '.join(parts)} in recent window."

    def build_agent_system_prompt(self, base_prompt: str = "") -> str:
        """Build a system prompt for Agent Builder with Cortex context.

        Adjusts the prompt based on circadian rhythm and recent perceptions.
        """
        context = self.get_agent_context()
        perception = context["cortex_perception"]

        cortex_section = f"""
## Cortex Perception Context
- Current mode: {perception['circadian_mode']}
- Recent activity: {perception['perception_summary']}
- Unread alerts: {perception['unread_notifications']}
- Suggested behavior: {', '.join(s.get('message', str(s)) if isinstance(s, dict) else str(s) for s in perception['suggestions'][:3]) if perception['suggestions'] else 'Normal operation'}
"""
        return f"{base_prompt}\n{cortex_section}"

    def run_perception_loop(
        self,
        sources: List[BaseSource],
        interval: float = 1.0,
        max_iterations: Optional[int] = None,
    ) -> List[IndexedEvent]:
        """Run the full perception loop.

        Checks all sources, filters through Cortex, indexes to ES.

        Args:
            sources: List of BaseSource instances to check
            interval: Seconds between checks
            max_iterations: Stop after N iterations (None = forever)

        Returns:
            List of all indexed events
        """
        all_indexed = []
        iteration = 0

        while max_iterations is None or iteration < max_iterations:
            # Check all sources for new events
            for source in sources:
                try:
                    events = source.check()
                    for event in events:
                        indexed = self.index_event(event)
                        if indexed:
                            all_indexed.append(indexed)
                except Exception as e:
                    self.notifications.push(
                        "error",
                        f"Source {source.name} failed: {e}",
                        "high"
                    )

            # Run scheduled tasks (e.g., health checks)
            self.scheduler.check_and_run()

            # Decision engine: should we take any autonomous action?
            if all_indexed:
                recent = [ie.event for ie in all_indexed[-5:]]
                action = self.decision.decide(recent)
                # Action could be passed to Agent Builder or ReachyMini

            iteration += 1
            if max_iterations and iteration >= max_iterations:
                break
            time.sleep(interval)

        return all_indexed

    def _health_check(self):
        """Periodic health check for ES connection."""
        if self.es_config.mock_mode:
            return  # No check needed in mock mode

        try:
            import urllib.request
            import ssl

            url = f"{self.es_config.es_url}/_cluster/health"
            headers = {
                "Authorization": f"ApiKey {self.es_config.api_key}",
            }
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                health = json.loads(resp.read())
                status = health.get("status", "unknown")
                if status == "red":
                    self.notifications.push(
                        "system",
                        f"ES cluster health: {status}",
                        "urgent"
                    )
        except Exception:
            pass  # Silent fail for health checks

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "total_indexed": len(self._indexed_events),
            "mock_mode": self.es_config.mock_mode,
            "circadian_mode": self.circadian.current_mode.value,
            "index_prefix": self.es_config.index_prefix,
            "last_event": (
                self._indexed_events[-1].timestamp
                if self._indexed_events
                else None
            ),
        }
