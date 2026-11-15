
# Home Battery Control Plus via Home Assistant & Node-RED

Home Battery Control Plus is an open-source solution for the community to control home batteries and electric vehicles using Home Assistant and Node-RED. Control your batteries exactly how you want, all in one place without vendor lock-ins.

This project is designed for hobbyists who want full control over their home battery systems. It provides ready-to-use flows and configuration examples, including a PID controller for advanced battery management. Use at your own discretion.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 
[![Node-RED](https://img.shields.io/badge/Node--RED-Flow-FF4A00?logo=node-red&logoColor=)](https://nodered.org/)
![License](https://img.shields.io/github/license/gitcodebob/marstek-venus-rs485-node-red)
[![GitHub stars](https://img.shields.io/github/stars/CodeRubbere/HASS-HBC-Plus?style=flat)](https://github.com/CodeRubbere/HASS-HBC-Plus/stargazers)

> 🇳🇱 Nederlandse handleiding: [docs/gebruikershandleiding.nl.md](docs/gebruikershandleiding.nl.md)

## Credits

HBC+ is a standalone version with its own development. It started from House Battery Control (HBC) v4.15.1 by **CodeBob** ([gitcodebob/marstek-venus-rs485-node-red](https://github.com/gitcodebob/marstek-venus-rs485-node-red)), the founding father of HBC: the original control loop, strategies, dashboard and helpers are his work, and all credit for that foundation goes to him. HBC+ has no further link with HBC.

## What HBC+ adds

- **Phase guard** — a phase map for up to 6 batteries (M1–M6), one active battery per phase by default, and per-phase headroom under both the grid fuse and the battery circuit, computed from the P1 meter every tick. Optional *Shared headroom* mode.
- **Correct planner ceiling** — Charge Deadline and HELIOS plan with the max power per phase, not the sum of all batteries.
- **Phases dashboard** and an overload alarm in Home Assistant that works even when Node-RED is down.
- **Shared price fetch** — any flow can fetch the Dynamic price list with one link call.
- **Safety, performance and stability** improvements (fail-open code, fewer Modbus writes, one fast read node, bug fixes).

With the phase guard on *Off* or *Monitor*, HBC+ controls the batteries without phase rules. Only *Enforce* applies them.

## Repository layout

| Path | Contents |
| --- | --- |
| `packages/` | Home Assistant packages: core helpers, Charge Deadline, Strategy arbiter, the phase-aware heartbeat fallback `hbc_heartbeat.yaml`, and `hbc_phase_guard.yaml` (HBC+) |
| `dashboards/hbc_plus.yaml` | The *Home Battery Control Plus* dashboard, including the **Phases** view |
| `node-red/hbc-plus-all-flows.json` | All 15 HBC+ Node-RED tabs in one import file |
| `node-red/*.json` | The same tabs as separate files |
| `node-red/README.md` | Per-tab overview of what HBC+ changes |
| `docs/` | User guide in English and Dutch |

## Quick start

1. Make sure Home Assistant (with packages and MQTT) and Node-RED (with the palettes listed under *Before you use it*) are running.
2. **Back up** Node-RED (*Export → All flows*) and Home Assistant.
3. Copy `packages/*.yaml` to your HA `packages/` folder, restart HA, and run the script **HBC+ phase guard: apply defaults** once.
4. Import `node-red/hbc-plus-all-flows.json` in Node-RED with **Replace**, check that the *HA System* server node has **Expose to global context** on, and Deploy.
5. Add the dashboard from `dashboards/hbc_plus.yaml`, set your phase map, grid fuse and battery circuit on the **Phases** view.
6. Run in **Monitor** for a few days, then switch to **Enforce**.

Full instructions: **[docs/user-guide.en.md](docs/user-guide.en.md)**.

Questions or bugs: open an issue at [github.com/CodeRubbere/HASS-HBC-Plus/issues](https://github.com/CodeRubbere/HASS-HBC-Plus/issues).

## Before you use it

- The Battery Oscillation Guard sends phone notifications through `notify.notify`. Set your own notify action (e.g. `notify.mobile_app_<phone>`) in its *Notify phone* node.
- A Marstek over Modbus TCP works as well, as long as its entities follow the `marstek_mN_*` pattern.
- `packages/hbc_heartbeat.yaml` (HA fallback when HBC+ stops) also sends a notification through `notify.notify`; set your own notify action there.
- `packages/hbc_control.yaml` sends a notification through `notify.notify` when the tariff source delivers no prices for 30 minutes; set your own notify action there too.
- Requirements: Home Assistant with packages, Node-RED with `node-red-contrib-home-assistant-websocket` (0.80 or newer), `node-red-contrib-time-range-switch`, `node-red-node-smooth`, MQTT, Marstek Venus E batteries (`marstek_mN_*` entities), a P1 meter with per-phase power, `apexcharts-card` (HACS), and for Dynamic and Charge Deadline the Cheapest Energy Hours macro (HACS) with a price integration.
- Always consult a qualified electrician about your installation and fuse ratings.

## License

GPL-3.0. See [LICENSE](LICENSE). HBC+ is derived from HBC v4.15.1 by CodeBob (GPL-3.0); all changes are described in [docs/user-guide.en.md](docs/user-guide.en.md).
