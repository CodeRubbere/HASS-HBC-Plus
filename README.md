
# Home Battery Control Plus (HBC+)

Home Battery Control Plus is an open-source solution for the community to control home batteries and electric vehicles using Home Assistant and Node-RED. Control your batteries exactly how you want, all in one place without vendor lock-ins.

This project is designed for hobbyists who want full control over their home battery systems. It provides ready-to-use flows and configuration examples, including a PID controller for advanced battery management. Use at your own discretion.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 
[![Node-RED](https://img.shields.io/badge/Node--RED-Flow-FF4A00?logo=node-red&logoColor=)](https://nodered.org/)
![License](https://img.shields.io/github/license/gitcodebob/marstek-venus-rs485-node-red)
[![GitHub stars](https://img.shields.io/github/stars/CodeRubbere/HASS-HBC-Plus?style=flat)](https://github.com/CodeRubbere/HASS-HBC-Plus/stargazers)

**Current version: v1.1** (16 November 2026) · [Download](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) · [What's new in v1.1](docs/user-guide.en.md#whats-new-in-hbc-v11)

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
- **Phases dashboard** and an overload alarm in Home Assistant that works even when Node-RED is down.
- **Shared price fetch** — the *API call to Data Source* group in *HBC+ Strategy Dynamic* is a link-call subroutine: any flow can fetch the current price list with one **link call** to *Dynamic Fetch from Data Source* (timeout ≥ 30 s), optionally for another source (`msg.dynamic.data_source`) or from the cache (`msg.dynamic_use_cache`). The caller always gets a reply in `msg.dynamic`: fresh prices, the last valid prices (`stale`) when the source fails, or `no_data`. Errors inside the group are caught, so a caller never waits for a timeout.
- **Safety, performance and stability** improvements (a fail-safe phase guard on *Enforce*, a *Full stop* when the batteries keep a phase overloaded, a heartbeat fallback that only counts working control cycles, battery values that never turn into NaN, warnings and errors that always reach the Node-RED log and `sensor.hbc_health`, fewer Modbus writes, one fast read node, bug fixes).

With the phase guard on *Off* or *Monitor*, HBC+ controls the batteries without phase rules. Only *Enforce* applies them.

**Coming in v1.2** (in development, planned for 10 December 2026, ready for the end of Dutch net metering on 1 January 2027):

- **Grid Clock feed** — a new tariff source with all-in buy and sell prices per quarter for your own supplier, public and without a token.
- **Buy and sell prices** — Dynamic values *Sell* at the real sell price; a sell price sensor and a sell line in the price chart.
- **Price guard** — while prices are negative, stop exporting and charge instead; signals for a PV limiter. Off by default.

## Repository layout

| Path | Contents |
| --- | --- |
| `packages/` | Home Assistant packages: core helpers, Charge Deadline, Strategy arbiter, the phase-aware heartbeat fallback `hbc_heartbeat.yaml`, and `hbc_phase_guard.yaml` (HBC+) |
| `dashboards/hbc_plus.yaml` | The *Home Battery Control Plus* dashboard, including the **Phases** view |
| `node-red/hbc-plus-all-flows.json` | All 15 HBC+ Node-RED tabs in one import file |
| `node-red/*.json` | The same tabs as separate files |
| `node-red/README.md` | Per-tab overview of what HBC+ changes |
| `node-red/examples/` | Example tab for the shared price fetch |
| `docs/` | User guide in English and Dutch |

## Quick start

1. Download the [latest release](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) (*Assets* → *Source code (zip)*) and unzip it.
2. Make sure Home Assistant (with packages and MQTT) and Node-RED (with the palettes listed under *Before you use it*) are running.
3. **Back up** Node-RED (*Export → All flows*) and Home Assistant.
4. Copy `packages/*.yaml` to your HA `packages/` folder, restart HA, and run the script **HBC+ phase guard: apply defaults** once.
5. Import `node-red/hbc-plus-all-flows.json` in Node-RED (updating? delete the old HBC+ tabs first: Node-RED cannot replace a flow on import), check that the *HA System* server node has **Expose to global context** on, and Deploy.
6. Add a dashboard named *Home Battery Control Plus* (keep the URL `home-battery-control-plus`) with the contents of `dashboards/hbc_plus.yaml`, set your phase map, grid fuse and battery circuit on the **Phases** view.
7. Run in **Monitor** for a few days, then switch to **Enforce**.

Full instructions: **[docs/user-guide.en.md](docs/user-guide.en.md)**.

**Updating from v1.0?** Follow [Updating from v1.0](docs/user-guide.en.md#updating-from-v10): new packages and notifications, and the old HBC+ tabs are deleted before the import.

Questions or bugs: open an issue at [github.com/CodeRubbere/HASS-HBC-Plus/issues](https://github.com/CodeRubbere/HASS-HBC-Plus/issues).

## Before you use it

- The Battery Oscillation Guard sends phone notifications through `notify.notify`. Set your own notify action (e.g. `notify.mobile_app_<phone>`) in its *Notify phone* node.
- A Marstek over Modbus TCP works as well, as long as its entities follow the `marstek_mN_*` pattern.
- `packages/hbc_heartbeat.yaml` (HA fallback when HBC+ stops or no longer works, and the alert when HBC+ keeps logging errors) sends two notifications through `notify.notify`; set your own notify action in both.
- `packages/hbc_control.yaml` sends a notification through `notify.notify` when the tariff source delivers no prices for 30 minutes; set your own notify action there too.
- Requirements: Home Assistant with packages, Node-RED with `node-red-contrib-home-assistant-websocket` (0.80 or newer), `node-red-contrib-time-range-switch`, MQTT, Marstek Venus E batteries (`marstek_mN_*` entities), a P1 meter with per-phase power, `apexcharts-card` (HACS), and for Dynamic and Charge Deadline the Cheapest Energy Hours macro (HACS) with a price integration.
- Always consult a qualified electrician about your installation and fuse ratings.

## License

GPL-3.0. See [LICENSE](LICENSE). HBC+ is derived from HBC v4.15.1 by CodeBob (GPL-3.0); all changes are described in [docs/user-guide.en.md](docs/user-guide.en.md).
