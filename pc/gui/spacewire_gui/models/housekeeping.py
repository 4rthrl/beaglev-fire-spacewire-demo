"""Camera housekeeping snapshot stored by the GUI.

The ROS gateway returns one coherent register bank per request. The GUI keeps
that snapshot locally so group/field selection never issues another SpaceWire
transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field


LEVEL_OK = 0
LEVEL_WARN = 1
LEVEL_ERROR = 2
LEVEL_STALE = 3

GROUP_IDENTIFICATION = "Camera/Identification"
GROUP_STATE = "Camera/State"
GROUP_IMAGE_CONFIG = "Camera/Image Configuration"
GROUP_COUNTERS = "Camera/Counters"
GROUP_MONITORS = "Camera/Monitors"
GROUP_SPACEWIRE = "Camera/SpaceWire"

GROUP_ORDER: tuple[str, ...] = (
    GROUP_IDENTIFICATION,
    GROUP_STATE,
    GROUP_IMAGE_CONFIG,
    GROUP_COUNTERS,
    GROUP_MONITORS,
    GROUP_SPACEWIRE,
)

GROUP_LABELS: dict[str, str] = {
    GROUP_IDENTIFICATION: "Identification",
    GROUP_STATE: "State",
    GROUP_IMAGE_CONFIG: "Image Configuration",
    GROUP_COUNTERS: "Counters",
    GROUP_MONITORS: "Monitors",
    GROUP_SPACEWIRE: "SpaceWire",
}


@dataclass(frozen=True)
class HousekeepingField:
    key: str
    value: str
    group_id: str


@dataclass(frozen=True)
class HousekeepingGroup:
    group_id: str
    level: int
    message: str
    fields: tuple[HousekeepingField, ...] = ()

    def as_dict(self) -> dict[str, str]:
        return {item.key: item.value for item in self.fields}


@dataclass
class HousekeepingSnapshot:
    hardware_id: str = ""
    groups: dict[str, HousekeepingGroup] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        for group in self.groups.values():
            value = group.as_dict().get(key)
            if value is not None:
                return value
        return default

    def group(self, group_id: str) -> HousekeepingGroup | None:
        return self.groups.get(group_id)

    def is_empty(self) -> bool:
        return not self.groups

    def copy(self) -> HousekeepingSnapshot:
        return HousekeepingSnapshot(
            hardware_id=self.hardware_id,
            groups=dict(self.groups),
        )
