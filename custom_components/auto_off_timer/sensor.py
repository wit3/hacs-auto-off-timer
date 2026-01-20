"""Sensor platform for Auto Off Timer."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, UnitOfTime
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DURATION_SECONDS,
    ATTR_FINISHES_AT,
    ATTR_TARGET,
    CONF_DEFAULT_DURATION,
    CONF_DURATION,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_RESTART_MODE,
    CONF_TARGETS,
    DATA_SENSORS,
    DOMAIN,
    RESTART_ANY_CHANGE,
    RESTART_NEVER,
    RESTART_ON_ONLY,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Auto Off Timer sensors."""
    data = entry.data
    targets: list[str] = data[CONF_TARGETS]
    base_entities: dict[str, dict[str, Any]] = data.get(CONF_ENTITIES, {})
    option_entities: dict[str, dict[str, Any]] = entry.options.get(CONF_ENTITIES, {})

    entities: list[AutoOffTimerSensor] = []
    for target in targets:
        target_cfg = option_entities.get(target, base_entities.get(target, {}))
        if not target_cfg:
            target_cfg = {
                CONF_ENABLED: True,
                CONF_DURATION: data[CONF_DEFAULT_DURATION],
                CONF_RESTART_MODE: RESTART_ON_ONLY,
            }
        entities.append(
            AutoOffTimerSensor(
                hass=hass,
                target_entity_id=target,
                enabled=target_cfg.get(CONF_ENABLED, True),
                duration=int(target_cfg.get(CONF_DURATION, data[CONF_DEFAULT_DURATION])),
                restart_mode=target_cfg.get(CONF_RESTART_MODE, RESTART_ON_ONLY),
            )
        )

    async_add_entities(entities)


class AutoOffTimerSensor(RestoreEntity, SensorEntity):
    """Sensor representing a countdown for a target entity."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(
        self,
        hass: HomeAssistant,
        target_entity_id: str,
        enabled: bool,
        duration: int,
        restart_mode: str,
    ) -> None:
        self.hass = hass
        self._target_entity_id = target_entity_id
        self._enabled = enabled
        self._duration = duration
        self._restart_mode = restart_mode

        self._attr_name = f"Auto-Off {target_entity_id}"
        self._attr_unique_id = f"auto_off_timer_{target_entity_id.replace('.', '_')}"

        self._finish_at: datetime | None = None
        self._unsub_expire: CALLBACK_TYPE | None = None
        self._unsub_tick: CALLBACK_TYPE | None = None
        self._unsub_state: CALLBACK_TYPE | None = None

    @property
    def native_value(self) -> int:
        """Return the remaining seconds."""
        if self._finish_at is None:
            return 0
        remaining = int((self._finish_at - dt_util.utcnow()).total_seconds())
        return max(0, remaining)

    @property
    def available(self) -> bool:
        """Return True if target entity exists in state machine."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            ATTR_TARGET: self._target_entity_id,
            CONF_ENABLED: self._enabled,
            ATTR_DURATION_SECONDS: self._duration,
            CONF_RESTART_MODE: self._restart_mode,
            ATTR_FINISHES_AT: self._finish_at.isoformat() if self._finish_at else None,
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        self.hass.data[DOMAIN][DATA_SENSORS][self._target_entity_id] = self

        entity_registry = er.async_get(self.hass)
        target_entry = entity_registry.async_get(self._target_entity_id)
        if target_entry and target_entry.device_id:
            entity_registry.async_update_entity(
                self.entity_id, device_id=target_entry.device_id
            )

        self._unsub_state = async_track_state_change_event(
            self.hass, [self._target_entity_id], self._handle_target_event
        )

        last_state = await self.async_get_last_state()
        finish_at = None
        if last_state:
            raw_finish = last_state.attributes.get(ATTR_FINISHES_AT)
            if raw_finish:
                finish_at = dt_util.parse_datetime(raw_finish)

        if finish_at is not None:
            finish_at = dt_util.as_utc(finish_at)

        if (
            self._enabled
            and finish_at is not None
            and finish_at > dt_util.utcnow()
            and self._is_target_on()
        ):
            self._finish_at = finish_at
            self._schedule_timer()
            self._start_tick()
        else:
            self._finish_at = None

        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Clean up."""
        self._cancel_handles()
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None

        self.hass.data[DOMAIN][DATA_SENSORS].pop(self._target_entity_id, None)
        await super().async_will_remove_from_hass()

    async def async_start(self, duration: int | None = None) -> None:
        """Start a countdown if not already running."""
        if not self._enabled:
            return
        if self._finish_at is not None:
            return
        await self._start_or_restart(duration)

    async def async_restart(self, duration: int | None = None) -> None:
        """Restart the countdown."""
        if not self._enabled:
            return
        await self._start_or_restart(duration)

    async def async_cancel(self) -> None:
        """Cancel the countdown."""
        self._cancel_handles()
        self._finish_at = None
        self.async_write_ha_state()

    async def _start_or_restart(self, duration: int | None) -> None:
        self._cancel_handles()
        duration_to_use = duration if duration is not None else self._duration
        self._finish_at = dt_util.utcnow() + timedelta(seconds=duration_to_use)
        self._schedule_timer()
        self._start_tick()
        self.async_write_ha_state()

    def _schedule_timer(self) -> None:
        if self._finish_at is None:
            return
        self._unsub_expire = async_track_point_in_utc_time(
            self.hass, self._handle_expired, self._finish_at
        )

    def _start_tick(self) -> None:
        if self._unsub_tick is not None:
            return
        self._unsub_tick = async_track_time_interval(
            self.hass, self._handle_tick, timedelta(seconds=1)
        )

    def _stop_tick(self) -> None:
        if self._unsub_tick is not None:
            self._unsub_tick()
            self._unsub_tick = None

    def _cancel_handles(self) -> None:
        if self._unsub_expire is not None:
            self._unsub_expire()
            self._unsub_expire = None
        self._stop_tick()

    def _is_target_on(self) -> bool:
        state = self.hass.states.get(self._target_entity_id)
        return state is not None and state.state == "on"

    async def _handle_target_event(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None:
            return

        if new_state.state == "off":
            await self.async_cancel()
            return

        if new_state.state != "on":
            await self.async_cancel()
            return

        if not self._enabled or self._restart_mode == RESTART_NEVER:
            return

        if self._restart_mode == RESTART_ON_ONLY:
            if old_state is None or old_state.state != "on":
                await self.async_restart()
            return

        if self._restart_mode == RESTART_ANY_CHANGE:
            await self.async_restart()

    async def _handle_expired(self, now: datetime) -> None:
        self._unsub_expire = None
        self._stop_tick()

        if self._is_target_on():
            domain = self._target_entity_id.split(".", 1)[0]
            await self.hass.services.async_call(
                domain,
                "turn_off",
                {CONF_ENTITY_ID: self._target_entity_id},
                blocking=False,
            )

        self._finish_at = None
        self.async_write_ha_state()

    def _handle_tick(self, now: datetime) -> None:
        if self._finish_at is None or self._finish_at <= dt_util.utcnow():
            self._stop_tick()
        self.async_write_ha_state()
