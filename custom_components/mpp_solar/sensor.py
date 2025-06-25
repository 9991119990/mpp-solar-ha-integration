"""Sensor platform for MPP Solar integration."""
from __future__ import annotations

import logging
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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    _LOGGER.info("🏗️ Setting up MPP Solar sensors")
    
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    
    # Get device info
    try:
        device_info = await hass.async_add_executor_job(api.get_device_info)
        _LOGGER.info("📄 Device info: %s", device_info)
    except Exception as e:
        _LOGGER.warning("⚠️ Could not get device info: %s", e)
        device_info = {"serial_number": "unknown", "firmware_version": "Unknown"}
    
    entities = []
    
    # Pokud nemáme data, vytvořme alespoň testovací entity
    if not coordinator.data:
        _LOGGER.warning("⚠️ No coordinator data, creating basic sensors")
        
        # Vytvoř základní senzory které budou čekat na data
        basic_sensors = [
            ("ac_output_voltage", "AC Output Voltage", "V", SensorDeviceClass.VOLTAGE),
            ("battery_voltage", "Battery Voltage", "V", SensorDeviceClass.VOLTAGE),
            ("ac_output_active_power", "AC Output Power", "W", SensorDeviceClass.POWER),
            ("battery_capacity", "Battery Capacity", "%", SensorDeviceClass.BATTERY),
            ("pv_input_voltage", "PV Voltage", "V", SensorDeviceClass.VOLTAGE),
        ]
        
        for sensor_key, name, unit, device_class in basic_sensors:
            entities.append(
                MPPSolarSensor(
                    coordinator=coordinator,
                    key=sensor_key,
                    name=name,
                    unit=unit,
                    device_info=device_info,
                    device_class=device_class,
                )
            )
        
        _LOGGER.info("✅ Created %d basic sensors", len(entities))
        
    else:
        _LOGGER.info("📊 Processing coordinator data: %d items", len(coordinator.data))
        
        # Zpracovat existující data
        for key, value_info in coordinator.data.items():
            _LOGGER.debug("🔍 Processing key: %s, value: %s", key, value_info)
            
            # Zkusit různé formáty dat
            unit = None
            value = None
            
            if isinstance(value_info, tuple) and len(value_info) >= 2:
                value, unit = value_info[0], value_info[1]
            elif isinstance(value_info, (int, float)):
                value = value_info
                unit = ""
            elif isinstance(value_info, str):
                value = value_info
                unit = ""
            else:
                _LOGGER.debug("⚠️ Skipping unknown value format for %s: %s", key, value_info)
                continue
            
            # Skip boolean values (they go to binary_sensor)
            if unit == "bool" or isinstance(value, bool):
                continue
            
            # Only create sensors for numeric values
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit()):
                device_class = _get_device_class(unit, key)
                
                entities.append(
                    MPPSolarSensor(
                        coordinator=coordinator,
                        key=key,
                        name=key.replace("_", " ").title(),
                        unit=unit,
                        device_info=device_info,
                        device_class=device_class,
                    )
                )
        
        _LOGGER.info("✅ Created %d sensors from data", len(entities))
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info("🎉 Successfully added %d sensor entities", len(entities))
    else:
        _LOGGER.error("❌ No entities were created!")

def _get_device_class(unit: str, key: str) -> SensorDeviceClass | None:
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

class MPPSolarSensor(CoordinatorEntity, SensorEntity):
    """Representation of an MPP Solar sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        key: str,
        name: str,
        unit: str,
        device_info: dict,
        device_class: SensorDeviceClass | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"MPP Solar {name}"
        self._attr_unique_id = f"mpp_solar_{key}"
        self._unit = unit
        
        _LOGGER.debug("🔧 Creating sensor: %s (key: %s, unit: %s)", self._attr_name, key, unit)
        
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
            self._attr_native_unit_of_measurement = _get_ha_unit(unit)
        
        # Set device class
        if device_class:
            self._attr_device_class = device_class
        
        # Set state class
        self._attr_state_class = _get_state_class(unit)
        
        # Set icon
        self._attr_icon = _get_icon(unit, key)

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            _LOGGER.debug("📭 No coordinator data for %s", self._key)
            return None
            
        if self._key not in self.coordinator.data:
            _LOGGER.debug("🔍 Key %s not found in coordinator data", self._key)
            return None
            
        value_info = self.coordinator.data[self._key]
        
        # Handle different data formats
        if isinstance(value_info, tuple) and len(value_info) >= 1:
            return value_info[0]
        elif isinstance(value_info, (int, float, str)):
            return value_info
        
        _LOGGER.debug("⚠️ Unknown value format for %s: %s", self._key, value_info)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

def _get_ha_unit(unit: str) -> str:
    """Convert unit to Home Assistant unit."""
    unit_mapping = {
        "V": UnitOfElectricPotential.VOLT,
        "A": UnitOfElectricCurrent.AMPERE,
        "W": UnitOfPower.WATT,
        "VA": "VA",
        "Hz": UnitOfFrequency.HERTZ,
        "°C": UnitOfTemperature.CELSIUS,
        "%": PERCENTAGE,
    }
    return unit_mapping.get(unit, unit)

def _get_state_class(unit: str) -> SensorStateClass | None:
    """Get state class based on unit."""
    if unit in ["W", "VA", "V", "A", "°C", "Hz", "%"]:
        return SensorStateClass.MEASUREMENT
    return None

def _get_icon(unit: str, key: str) -> str:
    """Get icon based on unit and key."""
    key_lower = key.lower()
    
    if "battery" in key_lower:
        return "mdi:battery"
    elif "pv" in key_lower or "solar" in key_lower:
        return "mdi:solar-panel"
    elif "inverter" in key_lower:
        return "mdi:power-plug"
    elif "load" in key_lower:
        return "mdi:chart-line"
    elif unit == "W" or unit == "VA":
        return "mdi:flash"
    elif unit == "V":
        return "mdi:lightning-bolt"
    elif unit == "A":
        return "mdi:current-ac"
    elif unit == "°C":
        return "mdi:thermometer"
    elif unit == "Hz":
        return "mdi:sine-wave"
    
    return "mdi:gauge"
