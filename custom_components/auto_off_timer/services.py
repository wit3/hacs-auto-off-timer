"""Service handlers for Auto Off Timer."""
from __future__ import annotations

from typing import Protocol

import voluptuous as vol
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import CONF_DURATION, DATA_SENSORS, DOMAIN, SERVICE_CANCEL, SERVICE_RESTART, SERVICE_START


class _TimerSensor(Protocol):
    async def async_start(self, duration: int | None = None) -> None:
        """Start a countdown."""

    async def async_restart(self, duration: int | None = None) -> None:
        """Restart a countdown."""

    async def async_cancel(self) -> None:
        """Cancel a countdown."""


START_RESTART_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_DURATION): cv.positive_int,
    }
)

CANCEL_SCHEMA = vol.Schema({vol.Required(CONF_ENTITY_ID): cv.entity_ids})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register services for Auto Off Timer."""
    data = hass.data.setdefault(DOMAIN, {DATA_SENSORS: {}, "services_registered": False})
    if data.get("services_registered"):
        return

    async def _handle_start(call: ServiceCall) -> None:
        await _handle_service(call, action="start")

    async def _handle_restart(call: ServiceCall) -> None:
        await _handle_service(call, action="restart")

    async def _handle_cancel(call: ServiceCall) -> None:
        await _handle_service(call, action="cancel")

    hass.services.async_register(
        DOMAIN,
        SERVICE_START,
        _handle_start,
        schema=START_RESTART_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART,
        _handle_restart,
        schema=START_RESTART_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL,
        _handle_cancel,
        schema=CANCEL_SCHEMA,
    )

    data["services_registered"] = True


async def _handle_service(call: ServiceCall, action: str) -> None:
    hass = call.hass
    data = hass.data.get(DOMAIN, {})
    sensors: dict[str, _TimerSensor] = data.get(DATA_SENSORS, {})

    entity_ids: list[str] = call.data[CONF_ENTITY_ID]
    duration: int | None = call.data.get(CONF_DURATION)

    for target in entity_ids:
        sensor = sensors.get(target)
        if sensor is None:
            continue
        if action == "start":
            await sensor.async_start(duration)
        elif action == "restart":
            await sensor.async_restart(duration)
        elif action == "cancel":
            await sensor.async_cancel()
