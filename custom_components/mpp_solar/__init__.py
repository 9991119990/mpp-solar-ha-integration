"""MPP Solar Inverter integration for Home Assistant."""
from __future__ import annotations

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

UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPP Solar from a config entry."""
    
    device_path = entry.data["device_path"]
    protocol = entry.data.get("protocol", "PI30")
    
    _LOGGER.info("Setting up MPP Solar integration for device: %s", device_path)
    
    # Initialize the API
    api = MPPSolarAPI(device_path, protocol)
    
    # Test connection
    try:
        await hass.async_add_executor_job(api.test_connection)
    except Exception as err:
        _LOGGER.error("Failed to connect to MPP Solar device: %s", err)
        return False

    # Create data update coordinator
    async def async_update_data():
        """Fetch data from API."""
        try:
            return await hass.async_add_executor_job(api.get_all_data)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="MPP Solar",
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    # Fetch initial data so we have data when entities are added
    await coordinator.async_config_entry_first_refresh()

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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok