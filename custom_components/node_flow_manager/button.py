from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Node-RED refresh button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([NodeRedRefreshButton(coordinator, entry)])

class NodeRedRefreshButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Node-RED Refresh Button."""

    def __init__(self, coordinator, entry):
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Refresh Flows"
        self._attr_unique_id = f"node_red_refresh_{entry.entry_id}"
        self._attr_icon = "mdi:refresh"
        self._entry_id = entry.entry_id
        self._host = entry.data.get("host", "Node-RED")

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"Node-RED ({self._host})",
            "manufacturer": "Node-RED",
            "model": "Service",
            "configuration_url": self.coordinator.api.configuration_base_url,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()
