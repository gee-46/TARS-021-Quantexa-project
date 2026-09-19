"""Emergency Corridor Events and Signal Mode Enumerations.

Defines:
1. IntersectionSignalMode: Operating state for each signal (NORMAL, PREPARE, PREEMPT_ACTIVE, RECOVERY).
2. EmergencyEventType: Lifecycle events during emergency vehicle transit.
3. EmergencyEvent: Structured log entry preserving timestamps, locations, and state changes.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List


class IntersectionSignalMode(Enum):
    """Operational mode of an intersection traffic signal."""

    NORMAL = "NORMAL"
    PREPARE = "PREPARE"
    PREEMPT_ACTIVE = "PREEMPT_ACTIVE"
    RECOVERY = "RECOVERY"


class EmergencyEventType(Enum):
    """Lifecycle event types for dynamic emergency corridor operations."""

    EMERGENCY_DETECTED = "EMERGENCY_DETECTED"
    CORRIDOR_ACTIVATED = "CORRIDOR_ACTIVATED"
    PREEMPTION_ACTIVE = "PREEMPTION_ACTIVE"
    PREPARE_DOWNSTREAM = "PREPARE_DOWNSTREAM"
    CLEARED_INTERSECTION = "CLEARED_INTERSECTION"
    EMERGENCY_COMPLETED = "EMERGENCY_COMPLETED"
    CORRIDOR_RELEASED = "CORRIDOR_RELEASED"
    NORMAL_RESUMED = "NORMAL_RESUMED"
    EMERGENCY_REJECTED_BUSY = "EMERGENCY_REJECTED_BUSY"


@dataclass(frozen=True)
class EmergencyEvent:
    """Structured event log entry representing a dynamic corridor control action."""

    timestamp: int
    event_type: str
    vehicle_id: str
    intersection: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __str__(self) -> str:
        inter_str = f" [{self.intersection}]" if self.intersection else ""
        return f"[t={self.timestamp:03d}s] {self.event_type:<24}{inter_str}: {self.message}"
