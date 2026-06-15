"""Sensors for Return and Earn."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    OVERALL_ALMOST_FULL,
    OVERALL_CLOSED,
    OVERALL_FULL,
    OVERALL_OPEN,
    OVERALL_UNKNOWN,
    STATUS_CLOSED,
    STATUS_FULL,
    STATUS_OPEN,
    STATUS_SEMI_FULL,
)
from .coordinator import ReturnAndEarnCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ReturnAndEarnCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        OverallStatusSensor(coordinator, entry),
        GlassStatusSensor(coordinator, entry),
        PlasticCansStatusSensor(coordinator, entry),
    ])


def _device_info(coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> DeviceInfo:
    attrs = coordinator.data.get("data", {}).get("attributes", {})
    org = coordinator.data.get("meta", {}).get("organization", {}).get("name", "")
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.uuid)},
        name=entry.title,
        manufacturer="TOMRA" + (f" / {org}" if org else ""),
        model=attrs.get("category", "RVM"),
        configuration_url="https://returnandearn.org.au/map",
    )


def _overall_status(glass: str, plastic: str) -> str:
    if glass == STATUS_CLOSED or plastic == STATUS_CLOSED:
        return OVERALL_CLOSED
    if glass == STATUS_FULL and plastic == STATUS_FULL:
        return OVERALL_FULL
    if STATUS_FULL in (glass, plastic) or STATUS_SEMI_FULL in (glass, plastic):
        return OVERALL_ALMOST_FULL
    if glass == STATUS_OPEN and plastic == STATUS_OPEN:
        return OVERALL_OPEN
    return OVERALL_UNKNOWN


def _stream_icon(status: str) -> str:
    return {
        STATUS_OPEN: "mdi:recycle",
        STATUS_SEMI_FULL: "mdi:delete-clock",
        STATUS_FULL: "mdi:delete-alert",
        STATUS_CLOSED: "mdi:recycle-variant",
    }.get(status, "mdi:recycle")


def _overall_icon(status: str) -> str:
    return {
        OVERALL_OPEN: "mdi:recycle",
        OVERALL_ALMOST_FULL: "mdi:delete-clock",
        OVERALL_FULL: "mdi:delete-alert",
        OVERALL_CLOSED: "mdi:recycle-variant",
    }.get(status, "mdi:recycle")


class _BaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self.coordinator, self._entry)

    @property
    def _attrs(self) -> dict:
        return self.coordinator.data.get("data", {}).get("attributes", {})

    @property
    def _status(self) -> dict:
        return self.coordinator.data.get("meta", {}).get("status", {})


class OverallStatusSensor(_BaseSensor):
    _attr_name = "Status"

    def __init__(self, coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.uuid}_overall_status"

    @property
    def native_value(self) -> str:
        return _overall_status(
            self._status.get("glass", ""),
            self._status.get("plasticAndCans", ""),
        )

    @property
    def icon(self) -> str:
        return _overall_icon(self.native_value)

    @property
    def extra_state_attributes(self) -> dict:
        a = self._attrs
        meta = self.coordinator.data.get("meta", {})
        return {
            "address": f"{a.get('address', '')}, {a.get('city', '')}",
            "opening_hours": a.get("readableOpeningHours"),
            "organization": meta.get("organization", {}).get("name"),
            "location_type": a.get("locationType"),
            "category": a.get("category"),
            "max_items_per_session": a.get("maxItemsPerSession"),
            "payout_options": meta.get("payoutOptions", []),
        }


class GlassStatusSensor(_BaseSensor):
    _attr_name = "Glass Status"

    def __init__(self, coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.uuid}_glass_status"

    @property
    def native_value(self) -> str:
        return self._status.get("glass", OVERALL_UNKNOWN)

    @property
    def icon(self) -> str:
        return _stream_icon(self.native_value)


class PlasticCansStatusSensor(_BaseSensor):
    _attr_name = "Plastic & Cans Status"

    def __init__(self, coordinator: ReturnAndEarnCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.uuid}_plastic_cans_status"

    @property
    def native_value(self) -> str:
        return self._status.get("plasticAndCans", OVERALL_UNKNOWN)

    @property
    def icon(self) -> str:
        return _stream_icon(self.native_value)
