from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Node-RED number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    known_entities = set() # Set of (flow_id, env_name)

    def _check_new_entities():
        """Check for new number entities and add them."""
        new_entities = []
        for flow_id, flow_data in coordinator.data.items():
            env_list = flow_data.get("env", [])
            for env_item in env_list:
                name = env_item.get("name")
                value = env_item.get("value")
                
                # Check if we already have this entity
                if (flow_id, name) in known_entities:
                    continue

                # Simple heuristic: if it can be a float, it's a number
                try:
                    float_val = float(value)
                    new_entities.append(NodeRedEnvNumber(coordinator, flow_id, flow_data.get("label"), name, float_val))
                    known_entities.add((flow_id, name))
                except (ValueError, TypeError):
                    continue
        
        if new_entities:
            async_add_entities(new_entities)

    # Register listener
    entry.async_on_unload(coordinator.async_add_listener(_check_new_entities))
    
    # Initial check
    _check_new_entities()

class NodeRedEnvNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Node-RED Flow Environment Variable as a number entity."""

    def __init__(self, coordinator, flow_id, flow_label, env_name, initial_value):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._flow_id = flow_id
        self._env_name = env_name
        self._attr_name = f"{flow_label} {env_name}"
        self._flow_label = flow_label
        self._attr_unique_id = f"node_red_flow_{flow_id}_env_{env_name}"
        self._attr_native_min_value = -1000000.0
        self._attr_native_max_value = 1000000.0
        self._attr_native_step = 0.001 if isinstance(initial_value, float) else 1.0

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
    def native_value(self) -> float:
        """Return the value of the number entity."""
        data = self.coordinator.data.get(self._flow_id, {})
        env_list = data.get("env", [])
        for item in env_list:
            if item.get("name") == self._env_name:
                try:
                    return float(item.get("value"))
                except (ValueError, TypeError):
                    return 0.0
        return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the value of the number entity."""
        # We store as string in Node-RED env as that's most common for env vars
        # unless they explicitly use json/num types, but 'str' is safest compatible
        await self.coordinator.api.update_flow(
            self._flow_id, 
            {"env": [{"name": self._env_name, "value": str(value), "type": "num"}]}
        )
        await self.coordinator.async_request_refresh()
