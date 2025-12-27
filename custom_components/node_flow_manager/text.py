from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Node-RED text entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    known_entities = set() # Set of (flow_id, env_name)

    def _check_new_entities():
        """Check for new text entities and add them."""
        new_entities = []
        for flow_id, flow_data in coordinator.data.items():
            env_list = flow_data.get("env", [])
            for env_item in env_list:
                name = env_item.get("name")
                value = env_item.get("value")
                
                # Check if we already have this entity
                if (flow_id, name) in known_entities:
                    continue

                # Simple heuristic: if it can be a float, skip it (number.py will handle it)
                # unless it contains characters that make it definitely a string
                try:
                    float(value)
                    continue
                except (ValueError, TypeError):
                    new_entities.append(NodeRedEnvText(coordinator, flow_id, flow_data.get("label"), name))
                    known_entities.add((flow_id, name))
        
        if new_entities:
            async_add_entities(new_entities)

    # Register listener
    entry.async_on_unload(coordinator.async_add_listener(_check_new_entities))
    
    # Initial check
    _check_new_entities()

class NodeRedEnvText(CoordinatorEntity, TextEntity):
    """Representation of a Node-RED Flow Environment Variable as a text entity."""

    def __init__(self, coordinator, flow_id, flow_label, env_name):
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._flow_id = flow_id
        self._env_name = env_name
        self._attr_name = f"{flow_label} {env_name}"
        self._flow_label = flow_label
        self._attr_unique_id = f"node_red_flow_{flow_id}_env_{env_name}"

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
        """Return the value of the text entity."""
        data = self.coordinator.data.get(self._flow_id, {})
        env_list = data.get("env", [])
        for item in env_list:
            if item.get("name") == self._env_name:
                return str(item.get("value", ""))
        return ""

    async def async_set_value(self, value: str) -> None:
        """Set the value of the text entity."""
        await self.coordinator.api.update_flow(
            self._flow_id, 
            {"env": [{"name": self._env_name, "value": value, "type": "str"}]}
        )
        await self.coordinator.async_request_refresh()
