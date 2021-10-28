"""Platform for sensor integration."""
import logging
import voluptuous as vol

from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.const import DEVICE_CLASS_TIMESTAMP, SERVICE_TURN_ON
from homeassistant.helpers import config_validation as cv, entity_platform
import pyfpa

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, ATTR_BOTTLE_ID

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, config_entry, async_add_entities, discovery_info=None
):
    """Set up the sensor platform."""

    api = hass.data[DOMAIN][config_entry.entry_id]

    if not api.has_me:
        await api.get_me()

    for device in api.devices:
        await api.connect_to_device(device.device_id)

    async_add_entities([FpaMainSensor(api, device) for device in api.devices])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_TURN_ON,
        {vol.Required(ATTR_BOTTLE_ID): cv.positive_int},
        "turn_on",
    )


class FpaSensor(SensorEntity):
    """Representation of a Fpa sensor."""

    _api: pyfpa.Fpa
    _device: pyfpa.FpaDevice

    def __init__(self, api, device):
        """Initialize the sensor."""
        self._api = api
        self._device = device

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""

        def updated_callback(device: pyfpa.FpaDevice):
            if device.device_id != self._device.device_id:
                return

            self._device = device
            self.schedule_update_ha_state()

        self.async_on_remove(self._api.add_listener(updated_callback))

    @property
    def available(self):
        """Return if data is available."""
        return self._device.connected

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
    def icon(self):
        """Return the icon of the sensor."""
        if self._device.shadow.making_bottle:
            return "mdi:cup"
        if self._device.shadow.funnel_cleaning_needed:
            return "mdi:liquid-spot"
        if self._device.shadow.funnel_out:
            return "mdi:filter-off-outline"
        if self._device.shadow.lid_open:
            return "mdi:filter-off"
        if self._device.shadow.low_water:
            return "mdi:water-off"
        if self._device.shadow.bottle_missing:
            return "mdi:cup-off-outline"
        if self._device.shadow.water_only:
            return "mdi:cup-water"
        return "mdi:coffee-maker"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._device.shadow.making_bottle:
            return "making_bottle"
        if self._device.shadow.funnel_cleaning_needed:
            return "funnel_cleaning_needed"
        if self._device.shadow.funnel_out:
            return "funnel_out"
        if self._device.shadow.lid_open:
            return "lid_open"
        if self._device.shadow.low_water:
            return "low_water"
        if self._device.shadow.bottle_missing:
            return "bottle_missing"
        if self._device.shadow.water_only:
            return "water_only"
        return "ready"

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        attr = {
            "temperature": self._device.shadow.temperature,
            "powder": self._device.shadow.powder,
            "volume": self._device.shadow.volume,
            "volume_unit": self._device.shadow.volume_unit,
            "making_bottle": self._device.shadow.making_bottle,
            "water_only": self._device.shadow.water_only,
            "bottle_missing": self._device.shadow.bottle_missing,
            "funnel_cleaning_needed": self._device.shadow.funnel_cleaning_needed,
            "funnel_out": self._device.shadow.funnel_out,
            "lid_open": self._device.shadow.lid_open,
            "low_water": self._device.shadow.low_water,
        }
        for bottle in self._device.bottles:
            attr[
                f"bottle_{bottle.id}"
            ] = f"{bottle.volume}{bottle.volume_unit} of {str(bottle.formula)}"
        return attr

    async def turn_on(self, **kwargs):
        """Service call to start making a bottle."""
        bottle_id = kwargs.get(ATTR_BOTTLE_ID)
        _LOGGER.info(f"Starting bottle {bottle_id}!")
        await self._api.start_bottle(bottle_id)
