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
from .mqtt_publisher import MPPSolarMQTTPublisher

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

UPDATE_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPP Solar from a config entry."""
    
    device_path = entry.data["device_path"]
    protocol = entry.data.get("protocol", "PI30")
    
    # MQTT configuration
    mqtt_host = entry.data.get("mqtt_host")
    mqtt_port = entry.data.get("mqtt_port", 1883)
    mqtt_username = entry.data.get("mqtt_username")
    mqtt_password = entry.data.get("mqtt_password")
    mqtt_topic_prefix = entry.data.get("mqtt_topic_prefix", "mpp_solar")
    
    _LOGGER.info("Setting up MPP Solar integration for device: %s", device_path)
    
    # Initialize the API
    api = MPPSolarAPI(device_path, protocol)
    
    # Initialize MQTT publisher if configured
    mqtt_publisher = None
    if mqtt_host:
        _LOGGER.info("Configuring MQTT publisher: %s:%s with topic prefix '%s'", mqtt_host, mqtt_port, mqtt_topic_prefix)
        mqtt_publisher = MPPSolarMQTTPublisher(
            host=mqtt_host,
            port=mqtt_port,
            username=mqtt_username if mqtt_username else None,
            password=mqtt_password if mqtt_password else None,
            topic_prefix=mqtt_topic_prefix,
        )
        try:
            await mqtt_publisher.connect()
            _LOGGER.info("MQTT publisher connected successfully")
        except Exception as err:
            _LOGGER.warning("Failed to connect to MQTT broker: %s", err)
    else:
        _LOGGER.info("MQTT not configured, skipping MQTT publisher setup")
    
    # Test connection
    try:
        await hass.async_add_executor_job(api.test_connection)
    except Exception as err:
        _LOGGER.error("Failed to connect to MPP Solar device: %s", err)
        return False

    # Create data update coordinator
    async def async_update_data():
        """Fetch data from API."""
        _LOGGER.debug("Starting data update cycle")
        try:
            data = await hass.async_add_executor_job(api.get_all_data)
            
            if data:
                _LOGGER.info("Successfully retrieved %d values from inverter", len(data))
            else:
                _LOGGER.warning("No data retrieved from inverter")
            
            # Publish to MQTT if configured
            if mqtt_publisher:
                try:
                    await mqtt_publisher.publish_data(data)
                    await mqtt_publisher.publish_availability(available=True)
                    _LOGGER.debug("Data published to MQTT successfully")
                except Exception as err:
                    _LOGGER.warning("Failed to publish to MQTT: %s", err)
            
            return data
        except Exception as err:
            _LOGGER.error("Data update failed: %s", err)
            # Publish offline status to MQTT if configured
            if mqtt_publisher:
                try:
                    await mqtt_publisher.publish_availability(available=False)
                    _LOGGER.debug("Published offline status to MQTT")
                except Exception:
                    pass
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="MPP Solar",
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )
    
    _LOGGER.info("Data update coordinator created with %s interval", UPDATE_INTERVAL)

    # Fetch initial data so we have data when entities are added
    _LOGGER.info("Performing initial data refresh...")
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.info("Initial data refresh completed successfully")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "mqtt_publisher": mqtt_publisher,
    }

    # Setup platforms
    _LOGGER.info("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("MPP Solar integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        
        # Disconnect MQTT if configured
        mqtt_publisher = entry_data.get("mqtt_publisher")
        if mqtt_publisher:
            try:
                await mqtt_publisher.publish_availability(available=False)
                await mqtt_publisher.disconnect()
            except Exception as err:
                _LOGGER.warning("Error disconnecting MQTT: %s", err)

    return unload_ok