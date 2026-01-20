"""Constants for Auto Off Timer."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "auto_off_timer"
PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_TARGETS = "targets"
CONF_DEFAULT_DURATION = "default_duration"
CONF_ENTITIES = "entities"
CONF_ENABLED = "enabled"
CONF_DURATION = "duration"
CONF_RESTART_MODE = "restart_mode"

RESTART_ON_ONLY = "on_only"
RESTART_ANY_CHANGE = "any_change"
RESTART_NEVER = "never"

SERVICE_START = "start"
SERVICE_RESTART = "restart"
SERVICE_CANCEL = "cancel"

ATTR_TARGET = "target"
ATTR_DURATION_SECONDS = "duration_seconds"
ATTR_FINISHES_AT = "finishes_at"

DATA_SENSORS = "sensors"
