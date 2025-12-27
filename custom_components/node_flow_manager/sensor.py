import json
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Node-RED sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    known_flows = set()

    def _check_new_entities():
        """Check for new flows and add debug sensors."""
        new_entities = []
        for flow_id, flow_data in coordinator.data.items():
            if flow_id not in known_flows:
                new_entities.append(NodeRedDebugSensor(coordinator, flow_id, flow_data.get("label")))
                known_flows.add(flow_id)
        
        if new_entities:
            async_add_entities(new_entities)

    # Register listener
    entry.async_on_unload(coordinator.async_add_listener(_check_new_entities))
    
    # Initial check
    _check_new_entities()

class NodeRedDebugSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Node-RED Flow Debug sensor."""

    def __init__(self, coordinator, flow_id, flow_label):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._flow_id = flow_id
        self._attr_name = f"{flow_label} Debug"
        self._flow_label = flow_label
        self._attr_unique_id = f"node_red_flow_{flow_id}_debug"
        self._attr_icon = "mdi:bug"

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {
            "identifiers": {(DOMAIN, self._flow_id)},
            "name": self._flow_label,
            "manufacturer": "Node-RED",
            "model": "Flow",
            "configuration_url": f"{self.coordinator.api.configuration_base_url}/#flow/{self._flow_id}",
        }

    @property
    def native_value(self) -> str:
        """Return the latest debug message."""
        messages = self.coordinator.debug_data.get(self._flow_id, [])
        if messages:
            msg = messages[0].get("msg")
            if isinstance(msg, (dict, list)):
                return json.dumps(msg)
            return str(msg)
        return "No messages"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        messages = self.coordinator.debug_data.get(self._flow_id, [])
        return {
            "history": messages
        }
