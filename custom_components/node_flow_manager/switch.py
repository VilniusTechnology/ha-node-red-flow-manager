from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_TAB_ID

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Node-RED switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    known_flows = set()

    def _check_new_entities():
        """Check for new flows and add them."""
        new_entities = []
        for flow_id, flow_data in coordinator.data.items():
            if flow_id not in known_flows:
                new_entities.append(NodeRedFlowSwitch(coordinator, flow_id, flow_data))
                known_flows.add(flow_id)
        
        if new_entities:
            async_add_entities(new_entities)

    # Register listener
    entry.async_on_unload(coordinator.async_add_listener(_check_new_entities))
    
    # Initial check
    _check_new_entities()

class NodeRedFlowSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Node-RED Flow switch."""

    def __init__(self, coordinator, flow_id, flow_data):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._flow_id = flow_id
        self._attr_name = flow_data.get("label", "Unknown Flow")
        self._flow_label = flow_data.get("label", "Unknown Flow")
        self._attr_unique_id = f"node_red_flow_{flow_id}"

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
    def is_on(self) -> bool:
        """Return True if flow is enabled (disabled=False)."""
        data = self.coordinator.data.get(self._flow_id, {})
        return not data.get("disabled", False)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data.get(self._flow_id, {})
        attrs = {
            "id": self._flow_id,
            "label": data.get("label"),
            "type": data.get("type"),
        }
        
        # Add environment variables
        env = data.get("env", [])
        if env:
            attrs["env"] = {item["name"]: item["value"] for item in env}
            
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn the entity on (Enable flow)."""
        await self.coordinator.api.update_flow(self._flow_id, {"disabled": False})
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off (Disable flow)."""
        await self.coordinator.api.update_flow(self._flow_id, {"disabled": True})
        await self.coordinator.async_request_refresh()
