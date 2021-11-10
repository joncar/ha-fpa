"""Platform for sensor integration."""
import logging
import voluptuous as vol

from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.const import DEVICE_CLASS_TIMESTAMP, SERVICE_TURN_ON
from homeassistant.helpers import config_validation as cv, entity_platform
import pybabyfpa

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, ATTR_BOTTLE_ID

_LOGGER = logging.getLogger(__name__)

STATE_TO_ICON = {
    "requesting_bottle": "mdi:transfer-down",
    "making_bottle": "mdi:transfer-down",
    "full_bottle": "mdi:cup",
    "funnel_cleaning_needed": "mdi:liquid-spot",
    "funnel_out": "mdi:filter-off-outline",
    "lid_open": "mdi:projector-screen-variant-off-outline",
    "low_water": "mdi:water-off",
    "bottle_missing": "mdi:cup-off-outline",
    "ready": "mdi:cup-outline"
}

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

    _api: pybabyfpa.Fpa
    _device: pybabyfpa.FpaDevice

    _making_bottle_requested: bool # between start API call and making_bottle shadow update
    _full_bottle: bool # between making_bottle shadow update and bottle_missing shadow update
    _old_making_bottle: bool
    _old_bottle_missing: bool

    def __init__(self, api, device):
        """Initialize the sensor."""
        self._api = api
        self._device = device
        self._making_bottle_requested = False
        self._full_bottle = False

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""

        self._old_making_bottle = False
        self._old_bottle_missing = False

        def updated_callback(device: pybabyfpa.FpaDevice):
            if device.device_id != self._device.device_id:
                return

            if not self._old_making_bottle and device.shadow.making_bottle:
                self._making_bottle_requested = False

            if self._old_making_bottle and not device.shadow.making_bottle and not device.shadow.bottle_missing:
                self._full_bottle = True

            if not self._old_bottle_missing and device.shadow.bottle_missing:
                self._making_bottle_requested = False
                self._full_bottle = False

            self._old_making_bottle = device.shadow.making_bottle
            self._old_bottle_missing = device.shadow.bottle_missing

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
    def assumed_state(self):
        """Return if data is from assumed state."""
        return self._making_bottle_requested

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
        return STATE_TO_ICON[self.state]

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._making_bottle_requested: # only useful for testing?
            return "requesting_bottle"
        if self._making_bottle_requested or self._device.shadow.making_bottle:
            return "making_bottle"
        if self._full_bottle:
            return "full_bottle"
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

        # Cloud API will ignore a start for all cases where the attributes
        # track a disallowed state like lid open or bottle missing.
        # However it does not attempt to track if the bottle has been
        # filled and has not been removed, so guard against that
        # (and all other) disallowed states here.
        if self.state != "ready":
            _LOGGER.error(f"Cannot start bottle when in state {self.state}")
            return

        _LOGGER.info(f"Starting bottle {bottle_id}!")
        self._making_bottle_requested = True
        await self._api.start_bottle(bottle_id)
