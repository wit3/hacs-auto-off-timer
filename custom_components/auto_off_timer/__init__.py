"""Auto Off Timer integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_SENSORS, DOMAIN, PLATFORMS
from .services import async_setup_services


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Auto Off Timer integration."""
    hass.data.setdefault(DOMAIN, {DATA_SENSORS: {}, "services_registered": False})
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auto Off Timer from a config entry."""
    hass.data.setdefault(DOMAIN, {DATA_SENSORS: {}, "services_registered": False})
    await async_setup_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unload_ok


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
