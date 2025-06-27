"""Binary sensor platform for MPP Solar integration."""
from __future__ import annotations

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

from .const import DOMAIN, BINARY_SENSOR_MAPPING, WARNING_MAPPING


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    # Get device info
    device_info = await hass.async_add_executor_job(api.get_device_info)
    
    entities = []
    
    # Create binary sensors for all boolean data
    if coordinator.data:
        for key, value_info in coordinator.data.items():
            if isinstance(value_info, tuple) and len(value_info) >= 2:
                value, unit = value_info[0], value_info[1]
                
                # Only create binary sensors for boolean values
                if unit == "bool":
                    # Get friendly name from mapping or create from key
                    friendly_name = (
                        BINARY_SENSOR_MAPPING.get(key) or 
                        WARNING_MAPPING.get(key) or 
                        key.replace("_", " ").title()
                    )
                    
                    # Determine device class
                    device_class = None
                    if any(word in key.lower() for word in ["fault", "warning", "alarm"]):
                        device_class = BinarySensorDeviceClass.PROBLEM
                    elif any(word in key.lower() for word in ["charging", "load", "switched"]):
                        device_class = BinarySensorDeviceClass.RUNNING
                    elif any(word in key.lower() for word in ["buzzer", "lcd"]):
                        device_class = BinarySensorDeviceClass.SOUND if "buzzer" in key.lower() else None
                    
                    entities.append(
                        MPPSolarBinarySensor(
                            coordinator=coordinator,
                            key=key,
                            name=friendly_name,
                            device_info=device_info,
                            device_class=device_class,
                        )
                    )
    
    async_add_entities(entities)


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
        elif "buzzer" in key_lower:
            return "mdi:volume-high"
        elif "lcd" in key_lower:
            return "mdi:monitor"
        elif "switch" in key_lower:
            return "mdi:toggle-switch"
        elif "restart" in key_lower:
            return "mdi:restart"
        elif "bypass" in key_lower:
            return "mdi:arrow-decision"
        elif "power_saving" in key_lower:
            return "mdi:leaf"
        else:
            return "mdi:checkbox-marked-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if self.coordinator.data and self._key in self.coordinator.data:
            value_info = self.coordinator.data[self._key]
            if isinstance(value_info, tuple) and len(value_info) >= 1:
                value = value_info[0]
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
        return self.coordinator.last_update_success and self.is_on is not None