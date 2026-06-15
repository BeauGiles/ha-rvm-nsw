"""Binary sensor — is the RVM open right now."""
from __future__ import annotations

import logging
from datetime import time

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DOMAIN, STATUS_CLOSED
from .coordinator import ReturnAndEarnCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_opening_hours(raw: str) -> dict[int, tuple[time, time]]:
    """Parse "1:07:00:21:00,2:07:00:21:00,..." → {isoweekday: (open, close)}."""
    result = {}
    for segment in (raw or "").split(","):
        parts = segment.strip().split(":")
        if len(parts) != 5:
            continue
        try:
            day = int(parts[0])
            open_t = time(int(parts[1]), int(parts[2]))
            close_t = time(int(parts[3]), int(parts[4]))
            result[day] = (open_t, close_t)
        except (ValueError, IndexError):
            _LOGGER.warning("Could not parse opening hours segment: %s", segment)
    return result


def _is_open_now(opening_hours_raw: str, status_glass: str, status_plastic: str) -> bool:
    # If the API reports both streams closed, trust it over the schedule
    if status_glass == STATUS_CLOSED and status_plastic == STATUS_CLOSED:
        return False

    now = dt_util.now()
    hours = _parse_opening_hours(opening_hours_raw)
    today = now.isoweekday()  # 1=Mon … 7=Sun

    if today not in hours:
        return False

    current = now.time().replace(second=0, microsecond=0)
    open_t, close_t = hours[today]
    return open_t <= current < close_t


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ReturnAndEarnCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IsOpenBinarySensor(coordinator, entry)])


class IsOpenBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Open Now"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.uuid}_open_now"

    @property
    def device_info(self) -> DeviceInfo:
        attrs = self.coordinator.data.get("data", {}).get("attributes", {})
        org = self.coordinator.data.get("meta", {}).get("organization", {}).get("name", "")
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.uuid)},
            name=self._entry.title,
            manufacturer="TOMRA" + (f" / {org}" if org else ""),
            model=attrs.get("category", "RVM"),
        )

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        attrs = data.get("data", {}).get("attributes", {})
        status = data.get("meta", {}).get("status", {})
        return _is_open_now(
            attrs.get("openingHours", ""),
            status.get("glass", ""),
            status.get("plasticAndCans", ""),
        )

    @property
    def icon(self) -> str:
        return "mdi:door-open" if self.is_on else "mdi:door-closed"

    @property
    def extra_state_attributes(self) -> dict:
        attrs = self.coordinator.data.get("data", {}).get("attributes", {})
        return {"opening_hours": attrs.get("readableOpeningHours")}
