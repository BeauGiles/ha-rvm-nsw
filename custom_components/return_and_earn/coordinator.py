"""DataUpdateCoordinator for Return and Earn."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import fetch_location_detail
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ReturnAndEarnCoordinator(DataUpdateCoordinator):
    """Polls /details/{uuid} for a single location on a configurable interval."""

    def __init__(self, hass: HomeAssistant, uuid: str, poll_interval_minutes: int) -> None:
        self.uuid = uuid
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{uuid}",
            update_interval=timedelta(minutes=poll_interval_minutes),
        )

    async def _async_update_data(self) -> dict:
        data = await fetch_location_detail(self.uuid)
        if data is None:
            raise UpdateFailed(f"Failed to fetch data for location {self.uuid}")
        return data
