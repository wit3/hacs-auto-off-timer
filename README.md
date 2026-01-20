# Auto Off Timer

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

Home Assistant custom integration that automatically turns off selected lights, switches, and fans after a configurable countdown. The integration creates one sensor per target entity to show the remaining time.

## Installation (HACS)

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Add this repository as a custom repository:
	 - URL: `https://github.com/wit3/hacs-auto-off-timer`
	 - Category: Integration
4. Install **Auto Off Timer**.
5. Restart Home Assistant.

## Configuration

1. Go to **Settings** → **Devices & Services**.
2. Click **Add Integration** and search for **Auto Off Timer**.
3. Select the target entities (domains: light, switch, fan).
4. Set the default duration (seconds).

To change per-entity settings (enabled, duration, restart mode), open the integration and use **Options**.

### Restart modes

- `on_only`: start/restart only when the entity turns on.
- `any_change`: restart on any state change while on (including attribute changes).
- `never`: do not auto-start; only manual services can start the timer.

## Sensors

For each target entity, a sensor is created:

- Name format: `Auto-Off <target_entity_id>`
- Example: `Auto-Off light.kitchen`

The sensor shows the remaining seconds. Attributes include the target entity, enabled flag, duration, restart mode, and `finishes_at` (UTC ISO).

## Services

Services are under the `auto_off_timer` domain and accept target entity IDs (light/switch/fan), not sensor IDs.

### Start

```yaml
service: auto_off_timer.start
data:
	entity_id:
		- light.kitchen
	duration: 600
```

### Restart

```yaml
service: auto_off_timer.restart
data:
	entity_id:
		- light.kitchen
```

### Cancel

```yaml
service: auto_off_timer.cancel
data:
	entity_id:
		- light.kitchen
```

## Example usage

1. Turn on a light (e.g., `light.kitchen`).
2. The sensor `Auto-Off light.kitchen` starts counting down.
3. When the countdown expires, the light is turned off automatically.
