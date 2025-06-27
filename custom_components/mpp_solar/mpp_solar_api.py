"""API for MPP Solar devices using external mpp-solar tool."""
from __future__ import annotations

import logging
import subprocess
import json
import re
from typing import Any, Dict

_LOGGER = logging.getLogger(__name__)


class MPPSolarAPI:
    """API for communicating with MPP Solar devices using mpp-solar tool."""

    def __init__(self, device_path: str, protocol: str = "PI30"):
        """Initialize the API."""
        self.device_path = device_path
        self.protocol = protocol
        # Try to find mpp-solar binary in common locations
        self.mpp_solar_path = self._find_mpp_solar_binary()

    def _find_mpp_solar_binary(self) -> str:
        """Find mpp-solar binary location."""
        possible_paths = [
            "/home/dell/Měniče/solar_env/bin/mpp-solar",
            "/usr/local/bin/mpp-solar",
            "/usr/bin/mpp-solar",
            "mpp-solar"  # System PATH
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, "--help"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    _LOGGER.info("Found mpp-solar binary at: %s", path)
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        _LOGGER.warning("mpp-solar binary not found, using system PATH")
        return "mpp-solar"

    def _run_mpp_command(self, command: str) -> str | None:
        """Run mpp-solar command and return output."""
        try:
            cmd = [self.mpp_solar_path, "-p", self.device_path, "-P", self.protocol, "-c", command]
            _LOGGER.debug("Running command: %s", " ".join(cmd))
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                _LOGGER.debug("Command %s successful, output length: %d", command, len(result.stdout))
                return result.stdout
            else:
                _LOGGER.error("Command %s failed with code %d: %s", command, result.returncode, result.stderr)
                return None
                
        except subprocess.TimeoutExpired:
            _LOGGER.error("Command %s timed out", command)
            return None
        except FileNotFoundError:
            _LOGGER.error("mpp-solar binary not found at %s", self.mpp_solar_path)
            return None
        except Exception as e:
            _LOGGER.error("Command %s failed: %s", command, e)
            return None

    def _parse_mpp_output(self, output: str) -> Dict[str, tuple[Any, str]]:
        """Parse mpp-solar output into structured data."""
        if not output:
            return {}
            
        data = {}
        lines = output.strip().split('\n')
        
        # Find data section (after dashes line)
        data_start = False
        for line in lines:
            if '----' in line:
                data_start = True
                continue
                
            if data_start and line.strip():
                # Parse line format: "Parameter: value unit"
                match = re.match(r'^([^:]+):\s*([^\s]+)(?:\s+(.+))?', line.strip())
                if match:
                    param_name = match.group(1).strip()
                    value_str = match.group(2).strip()
                    unit = match.group(3).strip() if match.group(3) else ""
                    
                    # Convert to appropriate type
                    try:
                        # Try int first
                        if '.' not in value_str:
                            value = int(value_str)
                        else:
                            value = float(value_str)
                    except ValueError:
                        # Keep as string for non-numeric values
                        value = value_str
                    
                    # Create entity-friendly key
                    key = param_name.lower().replace(' ', '_').replace('-', '_')
                    key = re.sub(r'[^\w_]', '', key)
                    
                    data[key] = (value, unit)
                    _LOGGER.debug("Parsed: %s = %s %s", key, value, unit)
        
        return data

    def test_connection(self) -> bool:
        """Test connection to the inverter."""
        _LOGGER.info("Testing connection to MPP Solar inverter at %s", self.device_path)
        try:
            output = self._run_mpp_command("QID")
            if output and "device_serial_number" in output.lower():
                _LOGGER.info("Connection test successful")
                return True
            else:
                _LOGGER.warning("Connection test failed - no valid response")
                return False
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            return False

    def get_device_info(self) -> Dict[str, Any]:
        """Get basic device information."""
        _LOGGER.debug("Getting device information")
        info = {}
        
        try:
            # Get serial number
            qid_output = self._run_mpp_command("QID")
            if qid_output:
                qid_data = self._parse_mpp_output(qid_output)
                for key, (value, unit) in qid_data.items():
                    if 'serial' in key or 'id' in key:
                        info["serial_number"] = str(value)
                        break
            
            # Get firmware version
            qvfw_output = self._run_mpp_command("QVFW")
            if qvfw_output:
                qvfw_data = self._parse_mpp_output(qvfw_output)
                for key, (value, unit) in qvfw_data.items():
                    if 'version' in key or 'firmware' in key:
                        info["firmware_version"] = str(value)
                        break
            
            # Get device mode
            qmod_output = self._run_mpp_command("QMOD")
            if qmod_output:
                qmod_data = self._parse_mpp_output(qmod_output)
                for key, (value, unit) in qmod_data.items():
                    if 'mode' in key:
                        info["mode"] = str(value)
                        break
                
        except Exception as e:
            _LOGGER.error("Failed to get device info: %s", e)
        
        return info

    def get_all_data(self) -> Dict[str, tuple[Any, str]]:
        """Get all available data from the device."""
        _LOGGER.info("Starting data collection from MPP Solar inverter")
        all_data = {}
        successful_commands = 0
        
        # Commands to execute
        commands = ["QPIGS", "QPIRI", "QPIWS", "QFLAG", "QMOD", "QID", "QVFW"]
        
        for command in commands:
            try:
                _LOGGER.debug("Executing command: %s", command)
                output = self._run_mpp_command(command)
                if output:
                    parsed_data = self._parse_mpp_output(output)
                    if parsed_data:
                        all_data.update(parsed_data)
                        successful_commands += 1
                        _LOGGER.debug("Command %s returned %d values", command, len(parsed_data))
                    else:
                        _LOGGER.warning("Command %s returned no parseable data", command)
                else:
                    _LOGGER.warning("Command %s returned no output", command)
            except Exception as e:
                _LOGGER.error("Failed to execute command %s: %s", command, e)
        
        _LOGGER.info("Data collection completed: %d/%d commands successful, %d total values retrieved", 
                    successful_commands, len(commands), len(all_data))
        
        # Log key readings for monitoring
        if all_data:
            key_readings = {}
            key_params = [
                'ac_output_voltage', 'battery_voltage', 'pv_input_voltage', 
                'ac_output_active_power', 'battery_capacity', 'inverter_heat_sink_temperature'
            ]
            
            for key in key_params:
                if key in all_data:
                    value, unit = all_data[key]
                    key_readings[key] = f"{value} {unit}"
            
            if key_readings:
                _LOGGER.info("Key readings: %s", key_readings)
        
        return all_data