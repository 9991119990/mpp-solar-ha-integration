"""Constants for the MPP Solar integration."""

DOMAIN = "mpp_solar"

# Default values
DEFAULT_PROTOCOL = "PI30"
DEFAULT_UPDATE_INTERVAL = 30

# MQTT Configuration
DEFAULT_MQTT_HOST = "localhost"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_TOPIC_PREFIX = "mpp_solar"

# Commands to monitor
COMMANDS_TO_MONITOR = [
    "QPIGS",  # General status
    "QPIRI",  # Device rating information
    "QPIWS",  # Device warning status
    "QFLAG",  # Device flag status
    "QMOD",   # Device mode
    "QID",    # Device serial number
    "QVFW",   # Main CPU firmware version
]

# Device classes for sensors
DEVICE_CLASSES = {
    "W": "power",
    "V": "voltage", 
    "A": "current",
    "°C": "temperature",
    "Hz": "frequency",
    "%": None,  # Will be determined by sensor name
}

# State classes for sensors
STATE_CLASSES = {
    "W": "measurement",
    "V": "measurement",
    "A": "measurement", 
    "°C": "measurement",
    "Hz": "measurement",
    "%": "measurement",
}

# Icons for different sensor types
SENSOR_ICONS = {
    "power": "mdi:flash",
    "voltage": "mdi:lightning-bolt",
    "current": "mdi:current-ac",
    "temperature": "mdi:thermometer",
    "frequency": "mdi:sine-wave",
    "battery": "mdi:battery",
    "solar": "mdi:solar-panel",
    "inverter": "mdi:power-plug",
    "load": "mdi:chart-line",
}

# Binary sensor mappings
BINARY_SENSOR_MAPPING = {
    "is_load_on": "Load Status",
    "is_charging_on": "Charging Status", 
    "is_scc_charging_on": "SCC Charging Status",
    "is_ac_charging_on": "AC Charging Status",
    "is_battery_voltage_to_steady_while_charging": "Battery Steady Status",
    "is_charging_to_float": "Float Charging Status",
    "is_switched_on": "Switch Status",
    "overload_restart": "Overload Restart",
    "over_temperature_restart": "Over Temperature Restart",
    "lcd_backlight": "LCD Backlight",
    "primary_source_interrupt_alarm": "Primary Source Alarm",
    "record_fault_code": "Record Fault Code",
    "buzzer": "Buzzer",
    "overload_bypass": "Overload Bypass",
    "power_saving": "Power Saving",
    "lcd_reset_to_default": "LCD Reset Default",
}

# Warning/fault status mappings
WARNING_MAPPING = {
    "inverter_fault": "Inverter Fault",
    "bus_over_fault": "Bus Over Fault",
    "bus_under_fault": "Bus Under Fault", 
    "bus_soft_fail_fault": "Bus Soft Fail",
    "line_fail_warning": "Line Fail Warning",
    "opv_short_warning": "OPV Short Warning",
    "inverter_voltage_too_low_fault": "Inverter Voltage Low",
    "inverter_voltage_too_high_fault": "Inverter Voltage High",
    "over_temperature_fault": "Over Temperature",
    "fan_locked_fault": "Fan Locked",
    "battery_voltage_too_high_fault": "Battery Voltage High",
    "battery_low_alarm_warning": "Battery Low Alarm",
    "battery_under_shutdown_warning": "Battery Under Shutdown",
    "overload_fault": "Overload Fault",
    "eeprom_fault": "EEPROM Fault",
    "inverter_over_current_fault": "Inverter Over Current",
    "inverter_soft_fail_fault": "Inverter Soft Fail",
    "self_test_fail_fault": "Self Test Fail",
    "op_dc_voltage_over_fault": "OP DC Voltage Over",
    "battery_open_fault": "Battery Open",
    "current_sensor_fail_fault": "Current Sensor Fail",
    "battery_short_fault": "Battery Short",
    "power_limit_warning": "Power Limit Warning",
    "pv_voltage_high_warning": "PV Voltage High",
    "mppt_overload_fault": "MPPT Overload Fault",
    "mppt_overload_warning": "MPPT Overload Warning",
    "battery_too_low_to_charge_warning": "Battery Too Low to Charge",
}