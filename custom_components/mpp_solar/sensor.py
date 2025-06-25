"""Sensor platform for MPP Solar integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, DEVICE_CLASSES, STATE_CLASSES, SENSOR_ICONS


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    # Get device info
    device_info = await hass.async_add_executor_job(api.get_device_info)
    
    entities = []
    
    # Create sensors for all numeric data
    if coordinator.data:
        for key, value_info in coordinator.data.items():
            if isinstance(value_info, tuple) and len(value_info) >= 2:
                value, unit = value_info[0], value_info[1]
                
                # Skip boolean values (they go to binary_sensor)
                if unit == "bool":
                    continue
                
                # Only create sensors for numeric values
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit()):
                    entities.append(
                        MPPSolarSensor(
                            coordinator=coordinator,
                            key=key,
                            name=key.replace("_", " ").title(),
                            unit=unit,
                            device_info=device_info,
                        )
                    )
    
    async_add_entities(entities)


class MPPSolarSensor(CoordinatorEntity, SensorEntity):
    """Representation of an MPP Solar sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        key: str,
        name: str,
        unit: str,
        device_info: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"MPP Solar {name}"
        self._attr_unique_id = f"mpp_solar_{key}"
        self._unit = unit
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_info.get("serial_number", "unknown"))},
            "name": "MPP Solar Inverter",
            "manufacturer": "MPP Solar",
            "model": "PIP5048MG",
            "sw_version": device_info.get("firmware_version", "Unknown"),
        }
        
        # Set unit of measurement
        if unit:
            self._attr_native_unit_of_measurement = self._get_ha_unit(unit)
        
        # Set device class
        self._attr_device_class = self._get_device_class(unit, key)
        
        # Set state class
        self._attr_state_class = self._get_state_class(unit)
        
        # Set icon
        self._attr_icon = self._get_icon(unit, key)

    def _get_ha_unit(self, unit: str) -> str:
        """Convert unit to Home Assistant unit."""
        unit_mapping = {
            "V": UnitOfElectricPotential.VOLT,
            "A": UnitOfElectricCurrent.AMPERE,
            "W": UnitOfPower.WATT,
            "VA": "VA",  # Apparent power
            "Hz": UnitOfFrequency.HERTZ,
            "°C": UnitOfTemperature.CELSIUS,
            "%": PERCENTAGE,
        }
        return unit_mapping.get(unit, unit)

    def _get_device_class(self, unit: str, key: str) -> SensorDeviceClass | None:
        """Get device class based on unit and key."""
        if unit == "W" or unit == "VA":
            return SensorDeviceClass.POWER
        elif unit == "V":
            return SensorDeviceClass.VOLTAGE
        elif unit == "A":
            return SensorDeviceClass.CURRENT
        elif unit == "°C":
            return SensorDeviceClass.TEMPERATURE
        elif unit == "Hz":
            return SensorDeviceClass.FREQUENCY
        elif unit == "%" and "battery" in key.lower():
            return SensorDeviceClass.BATTERY
        return None

    def _get_state_class(self, unit: str) -> SensorStateClass | None:
        """Get state class based on unit."""
        if unit in ["W", "VA", "V", "A", "°C", "Hz", "%"]:
            return SensorStateClass.MEASUREMENT
        return None

    def _get_icon(self, unit: str, key: str) -> str:
        """Get icon based on unit and key."""
        key_lower = key.lower()
        
        if "battery" in key_lower:
            return SENSOR_ICONS.get("battery", "mdi:battery")
        elif "pv" in key_lower or "solar" in key_lower:
            return SENSOR_ICONS.get("solar", "mdi:solar-panel")
        elif "inverter" in key_lower:
            return SENSOR_ICONS.get("inverter", "mdi:power-plug")
        elif "load" in key_lower:
            return SENSOR_ICONS.get("load", "mdi:chart-line")
        elif unit == "W" or unit == "VA":
            return SENSOR_ICONS.get("power", "mdi:flash")
        elif unit == "V":
            return SENSOR_ICONS.get("voltage", "mdi:lightning-bolt")
        elif unit == "A":
            return SENSOR_ICONS.get("current", "mdi:current-ac")
        elif unit == "°C":
            return SENSOR_ICONS.get("temperature", "mdi:thermometer")
        elif unit == "Hz":
            return SENSOR_ICONS.get("frequency", "mdi:sine-wave")
        
        return "mdi:gauge"

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        if self.coordinator.data and self._key in self.coordinator.data:
            value_info = self.coordinator.data[self._key]
            if isinstance(value_info, tuple) and len(value_info) >= 1:
                return value_info[0]
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None