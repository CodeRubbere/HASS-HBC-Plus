
<p align="center"><img src="assets/logo/hbc-plus-readme.svg" alt="HBC+ Home Battery Control Plus" width="720"></p>

# Home Battery Control Plus (HBC+)

Home Battery Control Plus is an open-source solution for the community to control home batteries and electric vehicles using Home Assistant and Node-RED. Control your batteries exactly how you want, all in one place without vendor lock-ins.

This project is designed for hobbyists who want full control over their home battery systems. It provides ready-to-use flows and configuration examples, including a PID controller for advanced battery management. Use at your own discretion.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 
[![Node-RED](https://img.shields.io/badge/Node--RED-Flow-FF4A00?logo=node-red&logoColor=)](https://nodered.org/)
![License](https://img.shields.io/github/license/gitcodebob/marstek-venus-rs485-node-red)
[![GitHub stars](https://img.shields.io/github/stars/CodeRubbere/HASS-HBC-Plus?style=flat)](https://github.com/CodeRubbere/HASS-HBC-Plus/stargazers)

**Current version: v1.1** (16 November 2026) · [Download](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) · [What's new in v1.1](docs/user-guide.en.md#whats-new-in-hbc-v11)

**Next: v1.2**, planned for 10 December 2026, ready for the end of Dutch net metering · [What's new in v1.2](docs/user-guide.en.md#whats-new-in-hbc-v12) · [Changelog](CHANGELOG.md)

> 🇳🇱 Nederlandse handleiding: [docs/gebruikershandleiding.nl.md](docs/gebruikershandleiding.nl.md)

## Credits

HBC+ is a standalone version with its own development. It started from House Battery Control (HBC) v4.15.1 by **CodeBob** ([gitcodebob/marstek-venus-rs485-node-red](https://github.com/gitcodebob/marstek-venus-rs485-node-red)), the founding father of HBC: the original control loop, strategies, dashboard and helpers are his work, and all credit for that foundation goes to him. HBC+ has no further link with HBC.

The Node-RED + HA control schema is based on the approach by Ruald Ordelman. And the easy to use Modbus to HA boards by [Fonske](https://github.com/fonske). Many thanks for sharing your work and ideas with the community!

Battery packages contributed by the community:
- [Fonske](https://github.com/fonske) — Marstek Venus packages over [Modbus TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP) and RS485 ([Lilygo](https://github.com/fonske/MarstekVenus-LilygoRS485) / [M5Stack](https://github.com/fonske/MarstekVenus-M5stackRS485)), and the reference `marstek_m1_*` entity naming that every other package maps onto
- [Jos1958](https://github.com/Jos1958) — Anker SolarBank 3 Pro (cloud bridge)
- [@wouterbouvy](https://github.com/wouterbouvy) — Anker SOLIX Solarbank Max AC / Solarbank 4 (local Modbus TCP)

## What HBC+ adds

- **Phase guard** — a phase map for up to 6 batteries (M1–M6), one active battery per phase by default, and per-phase headroom under both the grid fuse and the battery circuit, computed from the P1 meter every tick. Optional *Shared headroom* mode.
- **Correct planner ceiling** — Charge Deadline plans with the max power per phase, not the sum of all batteries.
- **Charge Deadline strategy** — charges to a target (full, SoC or energy reserve) before a deadline, in the cheapest quarter-hours, with optional PV reserve and a follow-up strategy once the deadline has passed.
- **GridClock as data source** — Dynamic and Charge Deadline can read prices from the [Grid Clock](https://gridclock.eu) integration (`sensor.grid_clock_<zone>_prices`). Prices refresh automatically when the default zone changes.
- **Phase guard view** on the dashboard and an overload alarm in Home Assistant that works even when Node-RED is down.
- **Shared price fetch** — the *API call to Data Source* group in *HBC+ Strategy Dynamic* is a link-call subroutine: any flow can fetch the current price list with one **link call** to *Dynamic Fetch from Data Source* (timeout ≥ 30 s), optionally for another source (`msg.dynamic.data_source`) or from the cache (`msg.dynamic_use_cache`). The caller always gets a reply in `msg.dynamic`: fresh prices, the last valid prices (`stale`) when the source fails, or `no_data`. Errors inside the group are caught, so a caller never waits for a timeout.
- **Safety, performance and stability** improvements (a fail-safe phase guard on *Enforce*, a *Full stop* when the batteries keep a phase overloaded, a heartbeat fallback that only counts working control cycles, battery values that never turn into NaN, warnings and errors that always reach the Node-RED log and `sensor.hbc_health`, fewer Modbus writes, one fast read node, bug fixes).

With the phase guard on *Off* or *Monitor*, HBC+ controls the batteries without phase rules. Only *Enforce* applies them.

**Coming in v1.2** (in development, planned for 10 December 2026, ready for the end of Dutch net metering on 1 January 2027):

- **Grid Clock feed** — the tariff source *Grid Clock* now has all-in buy and sell prices per quarter for your own supplier, public and without a token.
- **Buy and sell prices** — Dynamic values *Sell* at the real sell price; a sell price sensor and a sell line in the price chart.
- **Price guard** — while prices are negative, stop exporting and charge instead; signals for a PV limiter. Off by default.
- **New dashboard layout** — nine views in the order you use them: Overview, Prices, Charge & Sell, Timed & Dynamic, Phase guard, PID Control, Batteries, Settings and Logging.

## Works with Batterijplan

[Batterijplan](https://github.com/satscan1/hbc-batterijplan) is a Home Assistant integration that can steer HBC+. With HBC+ on **Dynamic** and Batterijplan's **Live** switch on, Batterijplan sets the Dynamic modes every quarter. From v1.4 the dashboard shows this: a banner with Batterijplan's current action, the *Price intervals* chart coloured by its plan, and the Dynamic modes read-only while it steers (`packages/hbc_batterijplan.yaml`). Without Batterijplan nothing changes. Details: [Steered by Batterijplan](docs/user-guide.en.md#steered-by-batterijplan) · 🇳🇱 [Aangestuurd door Batterijplan](docs/gebruikershandleiding.nl.md#aangestuurd-door-batterijplan).

## Repository layout

| Path | Contents |
| --- | --- |
| `packages/` | Home Assistant packages: core helpers, Charge Deadline, Strategy arbiter, the phase-aware heartbeat fallback `hbc_heartbeat.yaml`, `hbc_phase_guard.yaml`, the notification setting `hbc_notify.yaml` the battery calibration `hbc_calibration.yaml`, savings `hbc_savings.yaml` and the Batterijplan indicator `hbc_batterijplan.yaml` (HBC+) |
| `dashboards/hbc_plus.yaml` | The *Home Battery Control Plus* dashboard: Overview, Prices, Charge & Sell, Timed & Dynamic, Savings, **Phase guard**, PID Control, Batteries, Settings and Logging |
| `www/hbc-plus/` | The dashboard logo; copy it into your HA `www/` folder |
| `assets/logo/` | The HBC+ logo as SVG and PNG: on light, on dark, one colour, app icon, GitHub social preview |
| `node-red/hbc-plus-all-flows.json` | All 15 HBC+ Node-RED tabs in one import file |
| `node-red/*.json` | The same tabs as separate files |
| `node-red/README.md` | Per-tab overview of what HBC+ changes |
| `node-red/examples/` | Example tab for the shared price fetch |
| `docs/` | User guide in English and Dutch |

## Requirements

- **Home Assistant** with packages enabled (`homeassistant: packages: !include_dir_named packages`).
- **Node-RED** (add-on or standalone) with `node-red-contrib-home-assistant-websocket` 0.80 or newer.
- **Node-RED palette** `node-red-contrib-time-range-switch`.
- **MQTT**: the MQTT integration in HA with a broker.
- **Batteries**: Marstek Venus E, up to 6, entities named `marstek_mN_*` (RS485 or Modbus TCP).
- **Grid meter**: `sensor.p1_meter_power` and per-phase power `sensor.p1_meter_power_phase_1` … `_3`, positive on import.
- **Dashboard URL**: `home-battery-control-plus`, so the buttons that open other views work. The name does not matter; the URL cannot be changed later.
- **Dashboard**: `apexcharts-card` and `card-mod` (both Marketplace).
- **Prices**: the [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) macro (Marketplace) and a price integration, for Dynamic and Charge Deadline.

Details per requirement: [Requirements in the user guide](docs/user-guide.en.md#requirements).

## Quick start

1. Download the [latest release](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) (*Assets* → *Source code (zip)*) and unzip it.
2. Make sure Home Assistant (with packages and MQTT) and Node-RED (see *Requirements*) are running.
   From Marketplace, install **Cheapest Energy Hours**, **card-mod** and **apexcharts-card**, then restart HA and reload the browser.
3. **Back up** Node-RED (*Export → All flows*) and Home Assistant.
4. Copy `packages/*.yaml` to your HA `packages/` folder and `www/hbc-plus/` to your HA `www/` folder (the dashboard logo), restart HA, and run the script **HBC+ phase guard: apply defaults** once.
5. Import `node-red/hbc-plus-all-flows.json` in Node-RED (updating? delete the old HBC+ tabs first: Node-RED cannot replace a flow on import), check that the *HA System* server node has **Expose to global context** on, and Deploy.
6. Add a dashboard named *Home Battery Control Plus* (**the URL must be `home-battery-control-plus`**) with the contents of `dashboards/hbc_plus.yaml`, set your phase map on the **Batteries** view, and grid fuse and battery circuit under *Phase guard settings* on the **Settings** view.
7. Run in **Monitor** for a few days, then switch to **Enforce**.

Full instructions: **[docs/user-guide.en.md](docs/user-guide.en.md)**.

**Updating from v1.0?** Follow [Updating from v1.0](docs/user-guide.en.md#updating-from-v10): new packages and notifications, and the old HBC+ tabs are deleted before the import.

Questions or bugs: open an issue at [github.com/CodeRubbere/HASS-HBC-Plus/issues](https://github.com/CodeRubbere/HASS-HBC-Plus/issues).

## Coming from HBC?

Already running House Battery Control (HBC) by CodeBob? You can switch to HBC+ without starting over: HBC+ uses the same helper names, so your strategy, Timed, Dynamic, Charge, Sell and PID settings carry over. What changes:

- **Packages:** `house_battery_control.yaml` is replaced by the `hbc_*.yaml` packages; rename your own `house_battery_control_config.yaml` to `hbc_config.yaml` (the `hbc_config.yaml` in this repository is for new installations).
- **Grid meter:** HBC+ also needs per-phase power (`sensor.p1_meter_power_phase_1` … `_3`).
- **New requirements:** MQTT and `card-mod`; `node-red-node-smooth` is no longer needed.
- **Flows:** all HBC tabs are deleted and replaced by the HBC+ tabs; never run both.
- **Dashboard:** a new dashboard with the URL `home-battery-control-plus`.

The switch takes about 45 minutes and the batteries stay on their own firmware until you set *Full control* again. Step by step: **[Migrating from HBC](docs/user-guide.en.md#migrating-from-hbc)** · 🇳🇱 [Overstappen van HBC](docs/gebruikershandleiding.nl.md#overstappen-van-hbc).

## Before you use it

- All HBC+ notifications (Battery Oscillation Guard, heartbeat fallback, error alert, missing prices, phase guard) go through `script.hbc_notify` in `packages/hbc_notify.yaml`. Set where they go once, in *Notify targets* on the *Settings* view (e.g. `notify.mobile_app_<phone>`; empty = `notify.notify`), and press *Send a test notification*.
- A Marstek over Modbus TCP works as well, as long as its entities follow the `marstek_mN_*` pattern.
- Always consult a qualified electrician about your installation and fuse ratings.

## License

GPL-3.0. See [LICENSE](LICENSE). HBC+ is derived from HBC v4.15.1 by CodeBob (GPL-3.0); all changes are described in [docs/user-guide.en.md](docs/user-guide.en.md).
