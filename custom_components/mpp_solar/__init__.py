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
    _LOGGER.info("🚀 Setting up MPP Solar integration")
    _LOGGER.info("📍 Device path: %s", entry.data["device_path"])
    _LOGGER.info("📡 Protocol: %s", entry.data.get("protocol", "PI30"))
    
    # Create API instance
    api = MPPSolarAPI(
        device_path=entry.data["device_path"],
        protocol=entry.data.get("protocol", "PI30"),
    )
    
    # Test connection multiple times if needed
    _LOGGER.info("🔍 Testing connection to device...")
    connection_attempts = 3
    connected = False
    
    for attempt in range(connection_attempts):
        try:
            _LOGGER.info("📞 Connection attempt %d/%d", attempt + 1, connection_attempts)
            connected = await hass.async_add_executor_job(api.test_connection)
            if connected:
                _LOGGER.info("✅ Successfully connected to device on attempt %d", attempt + 1)
                break
            else:
                _LOGGER.warning("❌ Connection test returned False on attempt %d", attempt + 1)
                if attempt < connection_attempts - 1:
                    await asyncio.sleep(2)
        except Exception as e:
            _LOGGER.error("💥 Connection test failed on attempt %d: %s", attempt + 1, e)
            if attempt < connection_attempts - 1:
                await asyncio.sleep(2)
    
    if not connected:
        _LOGGER.error("🚫 Failed to connect after %d attempts", connection_attempts)
        return False

    async def async_update_data():
        """Fetch data from API endpoint."""
        try:
            _LOGGER.debug("📊 Fetching data from MPP Solar device")
            data = await hass.async_add_executor_job(api.get_all_data)
            
            if not data:
                _LOGGER.warning("📭 No data received from device")
                # Don't fail immediately, try to get at least basic info
                try:
                    device_info = await hass.async_add_executor_job(api.get_device_info)
                    if device_info:
                        _LOGGER.info("📄 Got device info: %s", device_info)
                        return {"device_info_only": (device_info, "")}
                except Exception as e:
                    _LOGGER.error("💥 Failed to get device info: %s", e)
                raise UpdateFailed("No data received from device")
            
            _LOGGER.info("📈 Data update successful! Received %d values", len(data))
            _LOGGER.debug("🔍 Data keys: %s", list(data.keys()))
            
            # Log some sample data for debugging
            for i, (key, value) in enumerate(data.items()):
                if i < 5:  # Log first 5 items
                    _LOGGER.debug("📊 Sample data [%s]: %s", key, value)
                    
            return data
        except Exception as err:
            _LOGGER.error("💥 Error communicating with API: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")

    # Create coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="mpp_solar",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    # Fetch initial data - retry if needed
    _LOGGER.info("📥 Fetching initial data...")
    initial_attempts = 3
    
    for attempt in range(initial_attempts):
        try:
            _LOGGER.info("📦 Initial data attempt %d/%d", attempt + 1, initial_attempts)
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("✅ Initial data fetch successful!")
            break
        except Exception as e:
            _LOGGER.warning("⚠️ Initial data fetch failed on attempt %d: %s", attempt + 1, e)
            if attempt < initial_attempts - 1:
                await asyncio.sleep(3)
            else:
                _LOGGER.error("🚫 Failed to get initial data after %d attempts", initial_attempts)
                return False

    # Verify we have data
    if not coordinator.data:
        _LOGGER.error("🚫 No data available after successful fetch - this shouldn't happen")
        return False
        
    _LOGGER.info("📊 Setup complete! Data available: %d items", len(coordinator.data))

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Setup platforms
    _LOGGER.info("🏗️ Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("✅ MPP Solar integration setup complete!")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("🔌 Unloading MPP Solar integration")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("✅ MPP Solar integration unloaded successfully")

    return unload_ok
