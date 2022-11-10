"""Config flow for National Rail Departure Times integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_TIME_OFFSET, DEFAULT_TIME_WINDOW

from .station_codes import STATIONS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("api_key"): str,
        vol.Required("arrival"): vol.In(STATIONS),
        vol.Required("time_offset", default=str(DEFAULT_TIME_OFFSET)): str,
    }
)

STEP_DESTINATION_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("destination"): vol.In(STATIONS),
        vol.Optional("add_another", default=False): cv.boolean,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for National Rail Departure Times."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self.data_config: dict[str, Any] = {"arrival": "", "destination": []}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            self.data_config["api_key"] = user_input["api_key"]
            self.data_config["arrival"] = user_input["arrival"]
            self.data_config["time_offset"] = user_input["time_offset"]
            self.data_config["time_window"] = str(DEFAULT_TIME_WINDOW)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return await self.async_step_destination()
            # return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_destination(self, user_input=None) -> FlowResult:
        """Target destination station configuration information"""
        if user_input is None:
            return self.async_show_form(
                step_id="destination", data_schema=STEP_DESTINATION_DATA_SCHEMA
            )

        errors = {}

        try:
            self.data_config["destination"].append(user_input["destination"])
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # If user ticked the box show this form again so they can add an additional station.
            if user_input.get("add_another", False):
                return await self.async_step_destination()

        return self.async_create_entry(
            title="National Rail Departure Times", data=self.data_config
        )
