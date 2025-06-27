"""Config flow for MPP Solar integration."""
from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, 
    DEFAULT_PROTOCOL, 
    DEFAULT_MQTT_HOST, 
    DEFAULT_MQTT_PORT, 
    DEFAULT_MQTT_TOPIC_PREFIX
)
from .mpp_solar_api import MPPSolarAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("device_path", default="/dev/hidraw2"): str,
        vol.Optional("protocol", default=DEFAULT_PROTOCOL): vol.In(["PI30", "PI16", "PI17", "PI18"]),
        vol.Optional("name", default="MPP Solar Inverter"): str,
    }
)

STEP_MQTT_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("mqtt_host", default=""): str,
        vol.Optional("mqtt_port", default=DEFAULT_MQTT_PORT): int,
        vol.Optional("mqtt_username", default=""): str,
        vol.Optional("mqtt_password", default=""): str,
        vol.Optional("mqtt_topic_prefix", default=DEFAULT_MQTT_TOPIC_PREFIX): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    device_path = data["device_path"]
    protocol = data["protocol"]
    
    # Check if device path exists
    if not os.path.exists(device_path):
        raise CannotConnect(f"Device path {device_path} does not exist")
    
    # Check if we can read from device
    if not os.access(device_path, os.R_OK):
        raise CannotConnect(f"Cannot read from {device_path}. Check permissions (try: sudo chmod 666 {device_path})")
    
    # Test connection to the device
    api = MPPSolarAPI(device_path, protocol)
    try:
        await hass.async_add_executor_job(api.test_connection)
    except Exception as err:
        _LOGGER.error("Failed to connect to MPP Solar device: %s", err)
        raise CannotConnect(f"Cannot connect to device: {err}")

    # Get device info for unique ID
    try:
        device_info = await hass.async_add_executor_job(api.get_device_info)
        serial_number = device_info.get("serial_number", "unknown")
    except Exception:
        serial_number = device_path.replace("/", "_")

    return {
        "title": data["name"],
        "serial_number": serial_number,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MPP Solar."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._device_config = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - device configuration."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured()
                
                # Store device config and move to MQTT step
                self._device_config = user_input.copy()
                self._device_config["title"] = info["title"]
                
                return await self.async_step_mqtt()
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle MQTT configuration step."""
        if user_input is not None:
            # Combine device and MQTT config
            final_config = self._device_config.copy()
            final_config.update(user_input)
            
            return self.async_create_entry(
                title=final_config["title"], 
                data=final_config
            )

        return self.async_show_form(
            step_id="mqtt", 
            data_schema=STEP_MQTT_DATA_SCHEMA,
            description_placeholders={
                "device": self._device_config.get("name", "MPP Solar")
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""