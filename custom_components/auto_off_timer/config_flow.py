"""Config flow for Auto Off Timer."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DEFAULT_DURATION,
    CONF_DOMAINS,
    CONF_DURATION,
    CONF_ENABLED,
    CONF_ENTITIES,
    CONF_RESTART_MODE,
    CONF_TARGETS,
    DEFAULT_DOMAINS,
    DOMAIN,
    RESTART_ANY_CHANGE,
    RESTART_NEVER,
    RESTART_ON_ONLY,
)

DEFAULT_DURATION_SECONDS = 300


class AutoOffTimerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auto Off Timer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            raw_targets = user_input[CONF_TARGETS]
            targets: list[str] = (
                raw_targets if isinstance(raw_targets, list) else [raw_targets]
            )
            default_duration: int = user_input[CONF_DEFAULT_DURATION]
            entities: dict[str, dict[str, Any]] = {}
            for target in targets:
                entities[target] = {
                    CONF_ENABLED: True,
                    CONF_DURATION: default_duration,
                    CONF_RESTART_MODE: RESTART_ON_ONLY,
                }

            return self.async_create_entry(
                title="Auto Off Timer",
                data={
                    CONF_TARGETS: targets,
                    CONF_DEFAULT_DURATION: default_duration,
                    CONF_ENTITIES: entities,
                    CONF_DOMAINS: DEFAULT_DOMAINS,
                },
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TARGETS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=False,
                        domain=DEFAULT_DOMAINS,
                    )
                ),
                vol.Required(
                    CONF_DEFAULT_DURATION, default=DEFAULT_DURATION_SECONDS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=86400,
                        step=1,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return AutoOffTimerOptionsFlowHandler(config_entry)


class AutoOffTimerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        targets: list[str] = self._entry.data[CONF_TARGETS]
        current_entities: dict[str, dict[str, Any]] = self._entry.options.get(
            CONF_ENTITIES, self._entry.data.get(CONF_ENTITIES, {})
        )
        current_domains: list[str] = self._entry.options.get(
            CONF_DOMAINS, self._entry.data.get(CONF_DOMAINS, DEFAULT_DOMAINS)
        )

        if user_input is not None:
            entities: dict[str, dict[str, Any]] = {}
            for target in targets:
                entities[target] = {
                    CONF_ENABLED: user_input[f"{target}__{CONF_ENABLED}"],
                    CONF_DURATION: user_input[f"{target}__{CONF_DURATION}"],
                    CONF_RESTART_MODE: user_input[f"{target}__{CONF_RESTART_MODE}"],
                }

            return self.async_create_entry(
                title="",
                data={
                    CONF_ENTITIES: entities,
                    CONF_DOMAINS: user_input[CONF_DOMAINS],
                },
            )

        schema: dict[vol.Marker, Any] = {
            vol.Required(
                CONF_DOMAINS, default=current_domains
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=DEFAULT_DOMAINS,
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
        for target in targets:
            target_cfg = current_entities.get(target, {})
            schema[
                vol.Required(
                    f"{target}__{CONF_ENABLED}",
                    default=target_cfg.get(CONF_ENABLED, True),
                )
            ] = selector.BooleanSelector()
            schema[
                vol.Required(
                    f"{target}__{CONF_DURATION}",
                    default=target_cfg.get(CONF_DURATION, DEFAULT_DURATION_SECONDS),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=86400,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.BOX,
                )
            )
            schema[
                vol.Required(
                    f"{target}__{CONF_RESTART_MODE}",
                    default=target_cfg.get(CONF_RESTART_MODE, RESTART_ON_ONLY),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[RESTART_ON_ONLY, RESTART_ANY_CHANGE, RESTART_NEVER],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
