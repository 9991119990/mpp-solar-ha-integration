"""MQTT Publisher for MPP Solar integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class MPPSolarMQTTPublisher:
    """MQTT Publisher for MPP Solar data."""

    def __init__(
        self,
        host: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "mpp_solar",
    ):
        """Initialize MQTT publisher."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.rstrip("/")
        
        self.client = mqtt.Client()
        self.connected = False
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        
        # Setup authentication if provided
        if username and password:
            self.client.username_pw_set(username, password)

    def _on_connect(self, client, userdata, flags, rc):
        """Called when MQTT client connects."""
        if rc == 0:
            self.connected = True
            _LOGGER.info("Connected to MQTT broker at %s:%s", self.host, self.port)
        else:
            self.connected = False
            _LOGGER.error("Failed to connect to MQTT broker: %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        """Called when MQTT client disconnects."""
        self.connected = False
        _LOGGER.warning("Disconnected from MQTT broker: %s", rc)

    def _on_publish(self, client, userdata, mid):
        """Called when message is published."""
        _LOGGER.debug("Message %s published successfully", mid)

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.connect, self.host, self.port, 60
            )
            # Start the loop in a separate thread
            self.client.loop_start()
            return True
        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            self.client.loop_stop()
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.disconnect
            )
        except Exception as err:
            _LOGGER.error("Error disconnecting from MQTT broker: %s", err)

    async def publish_data(self, data: Dict[str, Any], device_name: str = "inverter"):
        """Publish sensor data to MQTT."""
        if not self.connected:
            _LOGGER.warning("Not connected to MQTT broker, skipping publish")
            return

        try:
            # Publish individual sensor values
            for key, value in data.items():
                if value is not None:
                    topic = f"{self.topic_prefix}/{device_name}/{key}"
                    payload = str(value)
                    
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.client.publish, topic, payload, 0, True
                    )
                    
            # Publish complete data as JSON
            json_topic = f"{self.topic_prefix}/{device_name}/all"
            json_payload = json.dumps(data, default=str)
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.publish, json_topic, json_payload, 0, True
            )
            
            _LOGGER.debug("Published %d values to MQTT", len(data))
            
        except Exception as err:
            _LOGGER.error("Error publishing to MQTT: %s", err)

    async def publish_availability(self, device_name: str = "inverter", available: bool = True):
        """Publish device availability."""
        if not self.connected:
            return
            
        try:
            topic = f"{self.topic_prefix}/{device_name}/availability"
            payload = "online" if available else "offline"
            
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.publish, topic, payload, 0, True
            )
            
        except Exception as err:
            _LOGGER.error("Error publishing availability: %s", err)