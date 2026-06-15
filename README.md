# ha-rvm-nsw
Home Assistant integration for monitoring NSW Return and Earn RVM locations — shows live status, fill levels, and opening hours for self-service bottle return machines near you.

# Return and Earn

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Monitors NSW Return and Earn RVM locations with live status from the TOMRA API.

## Installation

### Via HACS (recommended)
1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Search for **Return and Earn**
4. Click **Download**
5. Restart Home Assistant

### Manual
Copy the `return_and_earn` folder into `config/custom_components/`, then restart Home Assistant.

## Setup

Go to **Settings → Devices & Services → Add Integration** and search for **Return and Earn**.

When adding a location, choose how to find it:
- **Nearest to home** — shows the 20 closest RVM locations to your HA home address
- **Nearest to an address** — enter any NSW suburb or address to find nearby locations
- **Enter UUID manually** — paste a location UUID directly from the TOMRA API

Each location is added as a separate device. Add as many as you like.

## Entities

Each device exposes four entities:

| Entity | Type | Values |
|--------|------|--------|
| Status | Sensor | Open / Almost Full / Full / Closed |
| Glass Status | Sensor | OPEN / SEMI_FULL / FULL / CLOSED |
| Plastic & Cans Status | Sensor | OPEN / SEMI_FULL / FULL / CLOSED |
| Open Now | Binary Sensor | on/off |

## Notes

- No API key required
- Only self-service automated machines (RVMs) are shown — staffed depots and collection centres are excluded
- Default poll interval: 15 minutes (configurable 1–1440 min)
- Data sourced from the TOMRA API used by the official Return and Earn app
