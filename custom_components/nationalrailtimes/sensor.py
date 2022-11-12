"""Platform for sensor integration."""
from __future__ import annotations
from datetime import timedelta
import logging
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import Api
from .const import (
    CONF_API_KEY,
    CONF_ARRIVAL,
    CONF_DESTINATIONS,
    CONF_TIME_OFFSET,
    CONF_TIME_WINDOW,
    DEFAULT_ICON,
    DEFAULT_NAME,
    DOMAIN,
    NATIONAL_RAIL_URL,
    SOAP_ACTION_URL,
    CONF_REFRESH_SECONDS,
)

from .station_codes import STATIONS

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=CONF_REFRESH_SECONDS)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_ARRIVAL): cv.string,
        vol.Required(CONF_TIME_OFFSET): cv.string,
        vol.Required(CONF_TIME_WINDOW): cv.string,
    }
)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    name = config[CONF_NAME] if CONF_NAME in config else DEFAULT_NAME
    station = config[CONF_ARRIVAL]
    destinations = config[CONF_DESTINATIONS]
    api_key = config[CONF_API_KEY]
    time_offset = config[CONF_TIME_OFFSET]
    time_window = config[CONF_TIME_WINDOW]

    sensors = []
    if station is not None:
        for destination in destinations:
            if destination is not None:
                sensors.append(
                    NationalrailSensor(
                        name,
                        station,
                        destination,
                        api_key,
                        time_offset,
                        time_window,
                    )
                )
    async_add_entities(sensors, update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    name = config.get(CONF_NAME)
    station = config.get[CONF_ARRIVAL]
    destinations = config.get(CONF_DESTINATIONS)
    api_key = config.get(CONF_API_KEY)
    time_offset = config.get(CONF_TIME_OFFSET)
    time_window = config.get(CONF_TIME_WINDOW)

    sensors = []
    if station is not None:
        for destination in destinations:
            if destination is not None:
                sensors.append(
                    NationalrailSensor(
                        name,
                        station,
                        destination,
                        api_key,
                        time_offset,
                        time_window,
                    )
                )

    async_add_entities(sensors, update_before_add=True)


class NationalrailSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, name, station, destination, api_key, time_offset, time_window):
        """Initialize the sensor."""
        self._platformname = name
        self._name = station + "_" + destination + "_" + time_offset
        self.time_offset = time_offset
        self.destination = destination
        self.station = station
        self._state = None

        self.api = Api(
            api_key, station, destination, NATIONAL_RAIL_URL, SOAP_ACTION_URL
        )
        self.api.set_config(CONF_TIME_OFFSET, time_offset)
        self.api.set_config(CONF_TIME_WINDOW, time_window)

    @property
    def unique_id(self):
        return self._name

    @property
    def name(self) -> str:
        station_name = self.station
        destination_name = self.destination

        if self.station in STATIONS:
            station_name = STATIONS[self.station]

        if self.destination in STATIONS:
            destination_name = STATIONS[self.destination]

        name = f"Trains {station_name} to {destination_name}"
        if int(self.time_offset):
            name = name + " (" + self.time_offset + "m walk)"
        return name

    @property
    def icon(self):
        """Icon of the sensor."""
        return DEFAULT_ICON

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        data = self.api.data

        try:
            result = await self.api.api_request()
            if not result:
                _LOGGER.warning("There was no reply from the National Rail servers")
                self._state = (
                    "There was no reply from National Rail Trains for this service"
                )
                return
        except OSError:
            _LOGGER.warning("Something broke")
            self._state = "There was an internal error for this service"
            return
        except Exception:
            _LOGGER.warning("Failed to interpret received %s", "XML", exc_info=1)
            self._state = "Cannot interpret XML for this service from National Rail"
            return

        self._state = data.get_state(self.destination)

    @property
    def extra_state_attributes(self):
        data = self.api.data
        attributes = {}
        attributes["last_refresh"] = data.get_last_update()

        if data.is_empty():
            return attributes

        attributes["message"] = data.message()
        attributes["station_name"] = data.get_station_name()
        attributes["destination_name"] = data.get_destination_name(self.destination)
        attributes["service"] = data.get_service_details(self.destination)
        attributes["calling_points"] = data.get_calling_points(self.destination)
        attributes["offset"] = self.time_offset

        attributes["station_code"] = self.station
        if self.destination in STATIONS:
            attributes["target_station_name"] = STATIONS[self.destination]
            attributes["target_station_code"] = self.destination

        return attributes
