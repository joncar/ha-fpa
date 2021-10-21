"""Platform for sensor integration."""
import logging

from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.const import DEVICE_CLASS_TIMESTAMP
import pyfpa

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, config_entry, async_add_entities, discovery_info=None
):
    """Set up the sensor platform."""

    api = hass.data[DOMAIN][config_entry.entry_id]

    if not api.has_me:
        await api.get_me()

    async_add_entities([FpaMainSensor(api, device) for device in api.devices])


class FpaSensor(SensorEntity):
    """Representation of a Fpa sensor."""

    _api: pyfpa.Fpa
    _device: pyfpa.FpaDevice

    def __init__(self, api, device):
        """Initialize the sensor."""
        self._api = api
        self._device = device

    @property
    def available(self):
        """Return if data is available."""
        return True

    @property
    def device_info(self):
        """Return device registry information for this entity."""
        return {
            "identifiers": {(DOMAIN, self._device.device_id)},
            "manufacturer": "Baby Brezza",
            "name": self._device.title,
        }

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return "mdi:baby-bottle"

    @property
    def should_poll(self):
        """No polling needed."""
        return False


class FpaMainSensor(FpaSensor):
    """Sensor for the Fpa's main state."""

    _attr_device_class = "fpa__state"

    @property
    def unique_id(self):
        """Return the unique id of the sensor."""
        return self._device.device_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._device.title

    @property
    def state(self):
        """Return the state of the sensor."""
        return "idle"

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        return {}
