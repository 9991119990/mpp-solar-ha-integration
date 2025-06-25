"""Config flow for MPP Solar integration."""
from __future__ import annotations

import logging
import os
from typing import Any
import glob

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, DEFAULT_PROTOCOL
from .mpp_solar_api import MPPSolarAPI

_LOGGER = logging.getLogger(__name__)

def find_available_devices():
    """Find available serial/HID devices."""
    devices = []
    
    # Check for hidraw devices
    for device in glob.glob("/dev/hidraw*"):
        if os.path.exists(device):
            devices.append(device)
    
    # Check for USB serial devices
    for device in glob.glob("/dev/ttyUSB*"):
        if os.path.exists(device):
            devices.append(device)
    
    # Check for serial by-id devices
    for device in glob.glob("/dev/serial/by-id/*"):
        if os.path.exists(device):
            devices.append(device)
    
    # Add socket option for ser2net
    devices.append("socket://localhost:2001")
    
    # Add manual entry option
    devices.append("manual")
    
    return devices

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    device_path = data["device_path"]
    protocol = data["protocol"]
    
    # Skip file existence check for socket connections
    if not device_path.startswith("socket://"):
        # Check if device path exists
        if not os.path.exists(device_path):
            # Try common alternatives
            alternatives = [
                device_path,
                f"/dev/{device_path}" if not device_path.startswith("/") else device_path,
                f"/dev/serial/by-id/{device_path}" if not device_path.startswith("/") else device_path,
            ]
            
            found = False
            for alt in alternatives:
                if os.path.exists(alt):
                    device_path = alt
                    data["device_path"] = alt
                    found = True
                    break
            
            if not found:
                raise CannotConnect(f"Device path {device_path} does not exist. Available devices: {', '.join(find_available_devices())}")
        
        # Check if we can read from device
        if not os.access(device_path, os.R_OK):
            _LOGGER.warning(f"Cannot read from {device_path}. Will try anyway (might need permissions)")
    
    # Test connection to the device
    api = MPPSolarAPI(device_path, protocol)
    try:
        if await hass.async_add_executor_job(api.test_connection):
            _LOGGER.info(f"Successfully connected to {device_path}")
        else:
            _LOGGER.warning(f"Connection test returned False for {device_path}")
    except Exception as err:
        _LOGGER.error("Failed to connect to MPP Solar device: %s", err)
        # Don't fail immediately, sometimes first connection fails
        _LOGGER.info("Will retry connection during setup")

    # Get device info for unique ID
    try:
        device_info = await hass.async_add_executor_job(api.get_device_info)
        serial_number = device_info.get("serial_number", "unknown")
    except Exception:
        serial_number = device_path.replace("/", "_").replace(":", "_")

    return {
        "title": data["name"],
        "serial_number": serial_number,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MPP Solar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                if user_input.get("device_selection") == "manual":
                    # Go to manual entry step
                    return await self.async_step_manual()
                elif user_input.get("device_selection"):
                    # Use selected device
                    user_input["device_path"] = user_input["device_selection"]
                
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Get available devices
        devices = await self.hass.async_add_executor_job(find_available_devices)
        
        device_schema = vol.Schema(
            {
                vol.Required("device_selection", default=devices[0] if devices else "manual"): vol.In(devices),
                vol.Optional("protocol", default=DEFAULT_PROTOCOL): vol.In(["PI30", "PI16", "PI17", "PI18"]),
                vol.Optional("name", default="MPP Solar Inverter"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=device_schema, errors=errors
        )
    
    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual device entry."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Check if already configured
                await self.async_set_unique_id(info["serial_number"])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        manual_schema = vol.Schema(
            {
                vol.Required("device_path", default="/dev/hidraw2"): str,
                vol.Optional("protocol", default=DEFAULT_PROTOCOL): vol.In(["PI30", "PI16", "PI17", "PI18"]),
                vol.Optional("name", default="MPP Solar Inverter"): str,
            }
        )

        return self.async_show_form(
            step_id="manual", data_schema=manual_schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
