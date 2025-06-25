"""The MPP Solar integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .mpp_solar_api import MPPSolarAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPP Solar from a config entry."""
    _LOGGER.info("Setting up MPP Solar integration")
    _LOGGER.debug("Config entry data: %s", entry.data)
    
    # Create API instance
    api = MPPSolarAPI(
        device_path=entry.data["device_path"],
        protocol=entry.data.get("protocol", "PI30"),
    )
    
    # Test connection
    _LOGGER.info("Testing connection to %s", entry.data["device_path"])
    try:
        connected = await hass.async_add_executor_job(api.test_connection)
        if not connected:
            _LOGGER.error("Failed to connect to device at %s", entry.data["device_path"])
            return False
        _LOGGER.info("Successfully connected to device")
    except Exception as e:
        _LOGGER.error("Connection test failed: %s", e)
        return False

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            _LOGGER.debug("Fetching data from MPP Solar device")
            data = await hass.async_add_executor_job(api.get_all_data)
            _LOGGER.debug("Received data keys: %s", list(data.keys()) if data else "No data")
            _LOGGER.info("Data update successful, got %d values", len(data) if data else 0)
            
            if not data:
                _LOGGER.warning("No data received from device")
                raise UpdateFailed("No data received from device")
                
            return data
        except Exception as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")

    # Create coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="mpp_solar",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data
    _LOGGER.info("Fetching initial data")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Initial data fetch complete")

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
