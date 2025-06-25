"""Binary sensor platform for MPP Solar integration."""
from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    _LOGGER.info("🏗️ Setting up MPP Solar binary sensors")
    
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    # Get device info
    try:
        device_info = await hass.async_add_executor_job(api.get_device_info)
    except Exception as e:
        _LOGGER.warning("⚠️ Could not get device info: %s", e)
        device_info = {"serial_number": "unknown", "firmware_version": "Unknown"}
    
    entities = []
    
    # Create binary sensors for all boolean data
    if coordinator.data:
        for key, value_info in coordinator.data.items():
            # Handle different data formats
            unit = None
            value = None
            
            if isinstance(value_info, tuple) and len(value_info) >= 2:
                value, unit = value_info[0], value_info[1]
            elif isinstance(value_info, bool):
                value = value_info
                unit = "bool"
            
            # Only create binary sensors for boolean values
            if unit == "bool" or isinstance(value, bool):
                # Get friendly name
                friendly_name = key.replace("_", " ").title()
                
                # Determine device class
                device_class = None
                if any(word in key.lower() for word in ["fault", "warning", "alarm"]):
                    device_class = BinarySensorDeviceClass.PROBLEM
                elif any(word in key.lower() for word in ["charging", "load", "switched"]):
                    device_class = BinarySensorDeviceClass.RUNNING
                
                entities.append(
                    MPPSolarBinarySensor(
                        coordinator=coordinator,
                        key=key,
                        name=friendly_name,
                        device_info=device_info,
                        device_class=device_class,
                    )
                )
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info("🎉 Successfully added %d binary sensor entities", len(entities))
    else:
        _LOGGER.info("📭 No binary sensors created (no boolean data found)")

class MPPSolarBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an MPP Solar binary sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        key: str,
        name: str,
        device_info: dict,
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"MPP Solar {name}"
        self._attr_unique_id = f"mpp_solar_{key}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_info.get("serial_number", "unknown"))},
            "name": "MPP Solar Inverter",
            "manufacturer": "MPP Solar",
            "model": "PIP5048MG",
            "sw_version": device_info.get("firmware_version", "Unknown"),
        }
        
        # Set device class
        if device_class:
            self._attr_device_class = device_class
        
        # Set icon based on sensor type
        self._attr_icon = self._get_icon(key)

    def _get_icon(self, key: str) -> str:
        """Get icon based on sensor key."""
        key_lower = key.lower()
        
        if any(word in key_lower for word in ["fault", "warning", "alarm"]):
            return "mdi:alert-circle"
        elif "charging" in key_lower:
            return "mdi:battery-charging"
        elif "load" in key_lower:
            return "mdi:power-plug"
        else:
            return "mdi:checkbox-marked-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data or self._key not in self.coordinator.data:
            return None
            
        value_info = self.coordinator.data[self._key]
        
        if isinstance(value_info, tuple) and len(value_info) >= 1:
            value = value_info[0]
        else:
            value = value_info
            
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ["on", "enabled", "true", "1"]
        elif isinstance(value, int):
            return bool(value)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
