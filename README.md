# ha-fpa
Home Assistant integration to control Baby Brezza's Formula Pro Advanced WiFi.

**:red_square: NOTE: This is an unofficial community project which is not affiliated with Baby Brezza. :red_square:**

## Installation and Usage

1. [Download](https://github.com/joncar/ha-fpa/archive/refs/heads/main.zip) and extract into the folder `custom_components/fpa` in your configuration folder.
2. Restart Home Assistant.
3. Setup the integration using the UI. [![My: Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=fpa)
4. `sensor.my_baby_brezza` (unless you've renamed the device in the app) will appear. And the service `fpa.turn_on` will start it making a bottle. The attributes of the sensor includes the bottle IDs accepted by the service.
