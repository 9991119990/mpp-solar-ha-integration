"""API for MPP Solar devices."""
from __future__ import annotations

import logging
import struct
import time
from typing import Any

import serial

_LOGGER = logging.getLogger(__name__)

# MPP Solar PI30 Protocol Commands
COMMANDS = {
    "QPIGS": "General Status Parameters",
    "QPIRI": "Device Rating Information", 
    "QPIWS": "Device Warning Status",
    "QFLAG": "Device Flag Status",
    "QMOD": "Device Mode",
    "QID": "Device Serial Number",
    "QVFW": "Main CPU Firmware Version",
}


class MPPSolarAPI:
    """API for communicating with MPP Solar devices."""

    def __init__(self, device_path: str, protocol: str = "PI30"):
        """Initialize the API."""
        self.device_path = device_path
        self.protocol = protocol
        self._device = None

    def _calculate_crc(self, command: str) -> bytes:
        """Calculate CRC for PI30 protocol."""
        crc = 0
        for char in command:
            crc = crc ^ ord(char)
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return struct.pack('<H', crc)

    def _send_command(self, command: str) -> str:
        """Send command to device and return response."""
        if self._device is None:
            # Try HID interface first
            try:
                with open(self.device_path, 'rb+') as device:
                    # PI30 protocol: command + CRC + \r
                    crc = self._calculate_crc(command)
                    full_command = command.encode() + crc + b'\r'
                    
                    # Send command
                    device.write(full_command)
                    device.flush()
                    
                    # Read response
                    time.sleep(0.1)  # Give device time to respond
                    response = device.read(8192)  # Read up to 8KB
                    
                    if response:
                        # Parse response (should start with '(' and end with CRC + '\r')
                        if response.startswith(b'(') and len(response) > 3:
                            # Remove leading '(' and trailing CRC + '\r'
                            data = response[1:-3].decode('utf-8', errors='ignore')
                            return data
                    
                    return ""
            except Exception as e:
                _LOGGER.error("HID communication failed: %s", e)
                # Fallback to serial communication
                try:
                    with serial.Serial(self.device_path, 2400, timeout=2) as ser:
                        crc = self._calculate_crc(command)
                        full_command = command.encode() + crc + b'\r'
                        
                        ser.write(full_command)
                        ser.flush()
                        
                        response = ser.read(1024)
                        if response and response.startswith(b'('):
                            data = response[1:-3].decode('utf-8', errors='ignore')
                            return data
                        
                        return ""
                except Exception as e2:
                    _LOGGER.error("Serial communication also failed: %s", e2)
                    raise

    def test_connection(self) -> bool:
        """Test connection to device."""
        try:
            response = self._send_command("QID")
            return bool(response and len(response) > 0)
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            return False

    def get_device_info(self) -> dict[str, Any]:
        """Get basic device information."""
        info = {}
        
        try:
            # Get serial number
            serial_response = self._send_command("QID")
            if serial_response:
                info["serial_number"] = serial_response.strip()
            
            # Get firmware version
            fw_response = self._send_command("QVFW")
            if fw_response:
                info["firmware_version"] = fw_response.strip()
            
            # Get device mode
            mode_response = self._send_command("QMOD")
            if mode_response:
                info["mode"] = mode_response.strip()
                
        except Exception as e:
            _LOGGER.error("Failed to get device info: %s", e)
        
        return info

    def _parse_qpigs(self, data: str) -> dict[str, tuple[Any, str]]:
        """Parse QPIGS command response."""
        if not data:
            return {}
            
        values = data.split()
        if len(values) < 21:
            _LOGGER.warning("QPIGS response too short: %s", data)
            return {}
        
        parsed = {
            "ac_input_voltage": (float(values[0]), "V"),
            "ac_input_frequency": (float(values[1]), "Hz"),
            "ac_output_voltage": (float(values[2]), "V"),
            "ac_output_frequency": (float(values[3]), "Hz"),
            "ac_output_apparent_power": (int(values[4]), "VA"),
            "ac_output_active_power": (int(values[5]), "W"),
            "ac_output_load": (int(values[6]), "%"),
            "bus_voltage": (int(values[7]), "V"),
            "battery_voltage": (float(values[8]), "V"),
            "battery_charging_current": (int(values[9]), "A"),
            "battery_capacity": (int(values[10]), "%"),
            "inverter_heat_sink_temperature": (int(values[11]), "°C"),
            "pv_input_current_for_battery": (float(values[12]), "A"),
            "pv_input_voltage": (float(values[13]), "V"),
            "battery_voltage_from_scc": (float(values[14]), "V"),
            "battery_discharge_current": (int(values[15]), "A"),
        }
        
        # Parse boolean flags (if available)
        if len(values) > 16:
            flags = values[16] if len(values) > 16 else "00000000"
            if len(flags) >= 8:
                parsed.update({
                    "is_sbu_priority_version_added": (bool(int(flags[0])), "bool"),
                    "is_configuration_changed": (bool(int(flags[1])), "bool"),
                    "is_scc_firmware_updated": (bool(int(flags[2])), "bool"),
                    "is_load_on": (bool(int(flags[3])), "bool"),
                    "is_battery_voltage_to_steady_while_charging": (bool(int(flags[4])), "bool"),
                    "is_charging_on": (bool(int(flags[5])), "bool"),
                    "is_scc_charging_on": (bool(int(flags[6])), "bool"),
                    "is_ac_charging_on": (bool(int(flags[7])), "bool"),
                })
        
        # Calculate additional derived values
        if "pv_input_voltage" in parsed and "pv_input_current_for_battery" in parsed:
            pv_voltage = parsed["pv_input_voltage"][0]
            pv_current = parsed["pv_input_current_for_battery"][0]
            parsed["pv_input_power"] = (int(pv_voltage * pv_current), "W")
        
        return parsed

    def _parse_qpiws(self, data: str) -> dict[str, tuple[Any, str]]:
        """Parse QPIWS (warning status) command response."""
        if not data or len(data) < 32:
            return {}
        
        warnings = {
            "inverter_fault": (bool(int(data[0])), "bool"),
            "bus_over_fault": (bool(int(data[1])), "bool"),
            "bus_under_fault": (bool(int(data[2])), "bool"),
            "bus_soft_fail_fault": (bool(int(data[3])), "bool"),
            "line_fail_warning": (bool(int(data[4])), "bool"),
            "opv_short_warning": (bool(int(data[5])), "bool"),
            "inverter_voltage_too_low_fault": (bool(int(data[6])), "bool"),
            "inverter_voltage_too_high_fault": (bool(int(data[7])), "bool"),
            "over_temperature_fault": (bool(int(data[8])), "bool"),
            "fan_locked_fault": (bool(int(data[9])), "bool"),
            "battery_voltage_too_high_fault": (bool(int(data[10])), "bool"),
            "battery_low_alarm_warning": (bool(int(data[11])), "bool"),
            "battery_under_shutdown_warning": (bool(int(data[13])), "bool"),
            "overload_fault": (bool(int(data[14])), "bool"),
            "eeprom_fault": (bool(int(data[15])), "bool"),
            "inverter_over_current_fault": (bool(int(data[16])), "bool"),
            "inverter_soft_fail_fault": (bool(int(data[17])), "bool"),
            "self_test_fail_fault": (bool(int(data[18])), "bool"),
            "op_dc_voltage_over_fault": (bool(int(data[19])), "bool"),
            "battery_open_fault": (bool(int(data[20])), "bool"),
            "current_sensor_fail_fault": (bool(int(data[21])), "bool"),
            "battery_short_fault": (bool(int(data[22])), "bool"),
            "power_limit_warning": (bool(int(data[23])), "bool"),
            "pv_voltage_high_warning": (bool(int(data[24])), "bool"),
            "mppt_overload_fault": (bool(int(data[25])), "bool"),
            "mppt_overload_warning": (bool(int(data[26])), "bool"),
            "battery_too_low_to_charge_warning": (bool(int(data[27])), "bool"),
        }
        
        return warnings

    def get_all_data(self) -> dict[str, Any]:
        """Get all available data from the device."""
        all_data = {}
        
        # Get QPIGS data (main status)
        try:
            qpigs_response = self._send_command("QPIGS")
            if qpigs_response:
                qpigs_data = self._parse_qpigs(qpigs_response)
                all_data.update(qpigs_data)
        except Exception as e:
            _LOGGER.error("Failed to get QPIGS data: %s", e)
        
        # Get warning status
        try:
            qpiws_response = self._send_command("QPIWS")
            if qpiws_response:
                qpiws_data = self._parse_qpiws(qpiws_response)
                all_data.update(qpiws_data)
        except Exception as e:
            _LOGGER.error("Failed to get QPIWS data: %s", e)
        
        # Get device mode
        try:
            mode_response = self._send_command("QMOD")
            if mode_response:
                all_data["device_mode"] = (mode_response.strip(), "")
        except Exception as e:
            _LOGGER.error("Failed to get device mode: %s", e)
        
        return all_data