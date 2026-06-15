"""Config flow for Return and Earn."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback, HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import (
    build_choices,
    ensure_uuid_in_choices,
    fetch_all_locations,
    fetch_location_detail,
    geocode_address,
    locations_sorted_alphabetically,
    locations_sorted_by_distance,
    name_from_location_list,
)
from .const import (
    CONF_LOCATION_NAME,
    CONF_LOCATION_UUID,
    CONF_POLL_INTERVAL,
    CONF_SEARCH_ADDRESS,
    CONF_SEARCH_METHOD,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    NEARBY_RESULTS,
    SEARCH_METHOD_ADDRESS,
    SEARCH_METHOD_HOME,
    SEARCH_METHOD_UUID,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_home_coords(hass: HomeAssistant) -> tuple[float, float] | None:
    home = hass.states.get("zone.home")
    if home:
        lat = home.attributes.get("latitude")
        lon = home.attributes.get("longitude")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    if hass.config.latitude and hass.config.longitude:
        return hass.config.latitude, hass.config.longitude
    return None


def _search_method_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SEARCH_METHOD, default=SEARCH_METHOD_HOME): vol.In(
                {
                    SEARCH_METHOD_HOME: "Nearest to home",
                    SEARCH_METHOD_ADDRESS: "Nearest to an address",
                    SEARCH_METHOD_UUID: "Enter location UUID manually",
                }
            )
        }
    )


def _poll_interval_schema(default: int = DEFAULT_POLL_INTERVAL) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_POLL_INTERVAL, default=default): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=1440)
            )
        }
    )


def _picker_schema(choices: dict[str, str], default: str = vol.UNDEFINED) -> vol.Schema:
    return vol.Schema(
        {vol.Required(CONF_LOCATION_UUID, default=default): vol.In(choices)}
    )


def _uuid_schema(default: str = "") -> vol.Schema:
    return vol.Schema({vol.Required(CONF_LOCATION_UUID, default=default): str})


def _address_schema(default: str = "") -> vol.Schema:
    return vol.Schema({vol.Required(CONF_SEARCH_ADDRESS, default=default): str})


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------

class ReturnAndEarnConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Step 1 — choose search method (home / address / UUID)
    Step 2a — near_home:    show picker of 20 nearest to HA home
    Step 2b — near_address: address input → geocode → show picker
    Step 2c — manual_uuid:  UUID text input → validate → skip picker
    Step 3  — poll interval (all paths)
    """

    VERSION = 1

    def __init__(self) -> None:
        self._locations: list[dict] = []
        self._search_method: str = SEARCH_METHOD_HOME
        self._choices: dict[str, str] = {}
        self._selected_uuid: str = ""
        self._selected_name: str = ""

    # ------------------------------------------------------------------
    # Step 1 — search method
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            self._search_method = user_input[CONF_SEARCH_METHOD]

            if self._search_method == SEARCH_METHOD_HOME:
                return await self.async_step_pick_near_home()
            elif self._search_method == SEARCH_METHOD_ADDRESS:
                return await self.async_step_address()
            else:
                return await self.async_step_manual_uuid()

        return self.async_show_form(
            step_id="user",
            data_schema=_search_method_schema(),
        )

    # ------------------------------------------------------------------
    # Step 2a — near home
    # ------------------------------------------------------------------

    async def async_step_pick_near_home(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if not self._choices:
            try:
                self._locations = await fetch_all_locations()
            except Exception:
                return self.async_show_form(
                    step_id="pick_near_home",
                    data_schema=vol.Schema({}),
                    errors={"base": "cannot_connect"},
                )

            coords = _get_home_coords(self.hass)
            if coords:
                nearby = locations_sorted_by_distance(self._locations, coords[0], coords[1], NEARBY_RESULTS)
                self._choices = build_choices(nearby, coords[0], coords[1])
            else:
                # No home coords — fall back to alphabetical full list
                self._choices = build_choices(locations_sorted_alphabetically(self._locations))

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "")
            if uuid:
                self._selected_uuid = uuid
                self._selected_name = name_from_location_list(self._locations, uuid)
                return await self.async_step_poll_interval()
            errors[CONF_LOCATION_UUID] = "invalid_selection"

        return self.async_show_form(
            step_id="pick_near_home",
            data_schema=_picker_schema(self._choices),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2b — near address
    # ------------------------------------------------------------------

    async def async_step_address(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input.get(CONF_SEARCH_ADDRESS, "").strip()
            if not address:
                errors[CONF_SEARCH_ADDRESS] = "empty_address"
            else:
                # Fetch location list if we don't have it yet
                if not self._locations:
                    try:
                        self._locations = await fetch_all_locations()
                    except Exception:
                        return self.async_show_form(
                            step_id="address",
                            data_schema=_address_schema(address),
                            errors={"base": "cannot_connect"},
                        )

                coords = await geocode_address(address)
                if coords:
                    nearby = locations_sorted_by_distance(self._locations, coords[0], coords[1], NEARBY_RESULTS)
                    self._choices = build_choices(nearby, coords[0], coords[1])
                else:
                    # Geocoding failed — full alphabetical list, no distances
                    self._choices = build_choices(locations_sorted_alphabetically(self._locations))

                return await self.async_step_pick_near_address()

        return self.async_show_form(
            step_id="address",
            data_schema=_address_schema(),
            errors=errors,
        )

    async def async_step_pick_near_address(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "")
            if uuid:
                self._selected_uuid = uuid
                self._selected_name = name_from_location_list(self._locations, uuid)
                return await self.async_step_poll_interval()
            errors[CONF_LOCATION_UUID] = "invalid_selection"

        return self.async_show_form(
            step_id="pick_near_address",
            data_schema=_picker_schema(self._choices),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2c — manual UUID
    # ------------------------------------------------------------------

    async def async_step_manual_uuid(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "").strip()
            if not uuid:
                errors[CONF_LOCATION_UUID] = "invalid_uuid"
            else:
                data = await fetch_location_detail(uuid)
                if data is None:
                    errors[CONF_LOCATION_UUID] = "cannot_connect"
                else:
                    self._selected_uuid = uuid
                    self._selected_name = (
                        data.get("data", {}).get("attributes", {}).get("name", uuid)
                    )
                    return await self.async_step_poll_interval()

        return self.async_show_form(
            step_id="manual_uuid",
            data_schema=_uuid_schema(),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 3 — poll interval (all paths converge here)
    # ------------------------------------------------------------------

    async def async_step_poll_interval(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(self._selected_uuid)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=self._selected_name,
                data={
                    CONF_LOCATION_UUID: self._selected_uuid,
                    CONF_LOCATION_NAME: self._selected_name,
                    CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                },
            )

        return self.async_show_form(
            step_id="poll_interval",
            data_schema=_poll_interval_schema(),
            description_placeholders={"location_name": self._selected_name},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ReturnAndEarnOptionsFlow:
        return ReturnAndEarnOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow (reconfigure)
# ---------------------------------------------------------------------------

class ReturnAndEarnOptionsFlow(config_entries.OptionsFlow):
    """
    Same three-path structure as the config flow.
    Pre-populates with current values where relevant.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._locations: list[dict] = []
        self._choices: dict[str, str] = {}
        self._selected_uuid: str = config_entry.data.get(CONF_LOCATION_UUID, "")
        self._selected_name: str = config_entry.data.get(CONF_LOCATION_NAME, "")
        self._current_interval: int = config_entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    def _apply_changes(self) -> None:
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            title=self._selected_name,
            data={
                CONF_LOCATION_UUID: self._selected_uuid,
                CONF_LOCATION_NAME: self._selected_name,
                CONF_POLL_INTERVAL: self._current_interval,
            },
        )

    # Step 1 — search method
    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            method = user_input[CONF_SEARCH_METHOD]
            if method == SEARCH_METHOD_HOME:
                return await self.async_step_pick_near_home()
            elif method == SEARCH_METHOD_ADDRESS:
                return await self.async_step_address()
            else:
                return await self.async_step_manual_uuid()

        return self.async_show_form(
            step_id="init",
            data_schema=_search_method_schema(),
        )

    # Step 2a — near home
    async def async_step_pick_near_home(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if not self._choices:
            try:
                self._locations = await fetch_all_locations()
            except Exception:
                return self.async_show_form(
                    step_id="pick_near_home",
                    data_schema=vol.Schema({}),
                    errors={"base": "cannot_connect"},
                )

            coords = _get_home_coords(self.hass)
            if coords:
                nearby = locations_sorted_by_distance(self._locations, coords[0], coords[1], NEARBY_RESULTS)
                self._choices = build_choices(nearby, coords[0], coords[1])
            else:
                self._choices = build_choices(locations_sorted_alphabetically(self._locations))

            # Ensure current location is always present
            self._choices = ensure_uuid_in_choices(self._choices, self._selected_uuid, self._locations)

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "")
            if uuid:
                self._selected_uuid = uuid
                self._selected_name = name_from_location_list(self._locations, uuid)
                return await self.async_step_poll_interval()
            errors[CONF_LOCATION_UUID] = "invalid_selection"

        return self.async_show_form(
            step_id="pick_near_home",
            data_schema=_picker_schema(self._choices, default=self._selected_uuid),
            errors=errors,
        )

    # Step 2b — near address
    async def async_step_address(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input.get(CONF_SEARCH_ADDRESS, "").strip()
            if not address:
                errors[CONF_SEARCH_ADDRESS] = "empty_address"
            else:
                if not self._locations:
                    try:
                        self._locations = await fetch_all_locations()
                    except Exception:
                        return self.async_show_form(
                            step_id="address",
                            data_schema=_address_schema(address),
                            errors={"base": "cannot_connect"},
                        )

                coords = await geocode_address(address)
                if coords:
                    nearby = locations_sorted_by_distance(self._locations, coords[0], coords[1], NEARBY_RESULTS)
                    self._choices = build_choices(nearby, coords[0], coords[1])
                else:
                    self._choices = build_choices(locations_sorted_alphabetically(self._locations))

                self._choices = ensure_uuid_in_choices(self._choices, self._selected_uuid, self._locations)
                return await self.async_step_pick_near_address()

        return self.async_show_form(
            step_id="address",
            data_schema=_address_schema(),
            errors=errors,
        )

    async def async_step_pick_near_address(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "")
            if uuid:
                self._selected_uuid = uuid
                self._selected_name = name_from_location_list(self._locations, uuid)
                return await self.async_step_poll_interval()
            errors[CONF_LOCATION_UUID] = "invalid_selection"

        return self.async_show_form(
            step_id="pick_near_address",
            data_schema=_picker_schema(self._choices),
            errors=errors,
        )

    # Step 2c — manual UUID
    async def async_step_manual_uuid(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            uuid = user_input.get(CONF_LOCATION_UUID, "").strip()
            if not uuid:
                errors[CONF_LOCATION_UUID] = "invalid_uuid"
            else:
                data = await fetch_location_detail(uuid)
                if data is None:
                    errors[CONF_LOCATION_UUID] = "cannot_connect"
                else:
                    self._selected_uuid = uuid
                    self._selected_name = (
                        data.get("data", {}).get("attributes", {}).get("name", uuid)
                    )
                    return await self.async_step_poll_interval()

        return self.async_show_form(
            step_id="manual_uuid",
            data_schema=_uuid_schema(default=self._selected_uuid),
            errors=errors,
        )

    # Step 3 — poll interval
    async def async_step_poll_interval(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            self._current_interval = user_input[CONF_POLL_INTERVAL]
            self._apply_changes()
            return self.async_create_entry(title=self._selected_name, data={})

        return self.async_show_form(
            step_id="poll_interval",
            data_schema=_poll_interval_schema(default=self._current_interval),
            description_placeholders={"location_name": self._selected_name},
        )
