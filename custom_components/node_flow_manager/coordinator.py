import asyncio
from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class NodeRedCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Node-RED data."""

    def __init__(self, hass, api, scan_interval_seconds=120):
        """Initialize."""
        self.api = api
        self.hass = hass
        self.debug_data = {}  # {flow_id: [messages]}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval_seconds),
        )
        
        # Start background task for WebSocket
        self._ws_task = hass.async_create_background_task(
            self._listen_for_debug(), "node_red_comms"
        )

    async def _listen_for_debug(self):
        """Listen for debug messages in a loop."""
        while True:
            try:
                await self.api.listen_comms(self._handle_comms_message)
            except Exception as e:
                _LOGGER.error("WebSocket connection failed, retrying in 10s: %s", e)
            
            # Wait before reconnecting to avoid tight loop if connection closes immediately
            await asyncio.sleep(10)

    async def _handle_comms_message(self, message):
        """Handle incoming WebSocket message."""
        if not isinstance(message, dict):
            return

        if message.get("topic") == "debug":
            data = message.get("data", {})
            flow_id = data.get("z") # 'z' is the flow/tab ID in Node-RED
            if not flow_id:
                return
                
            if flow_id not in self.debug_data:
                self.debug_data[flow_id] = []
            
            # Keep only last 20 messages
            self.debug_data[flow_id].insert(0, {
                "timestamp": asyncio.get_event_loop().time(),
                "node_id": data.get("id"),
                "node_name": data.get("name"),
                "msg": data.get("msg")
            })
            self.debug_data[flow_id] = self.debug_data[flow_id][:20]
            
            # Trigger update for sensors
            self.async_set_updated_data(self.data)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            flows = await self.api.get_flows()
            # We want to return a dict keyed by flow ID of just the tabs (flows)
            # Node-RED /flows returns a list of all nodes. We filter for type="tab"
            flows_dict = {}
            for item in flows:
                if item.get("type") == "tab":
                    flows_dict[item["id"]] = item
            
            return flows_dict
        except Exception as exception:
            raise UpdateFailed(exception) from exception
