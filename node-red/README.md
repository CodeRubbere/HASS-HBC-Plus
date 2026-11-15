# HBC+ - complete Node-RED flow set (v1.0, 2026-11-14)

Everything Node-RED needs for HBC+ (Home Battery Control Plus), a standalone home battery controller with the phase guard for
2 batteries per phase. All tabs are named `HBC+ ... v1.0`. Tabs with the same node ids from an earlier installation are
replaced on import instead of added as copies.

**Quickest install:** import `hbc-plus-all-flows.json` (all 15 tabs, HA server config node once).
Or import the files one by one.

## Contents

| File | Tab | HBC+ change |
| --- | --- | --- |
| `00 master-switch-flow (HBC+).json` | HBC+ Home Battery Master Switch v1.0 | **changed** - hand-back to firmware: partner on a shared phase stays RS485 + stop (Enforce only) |
| `00 presets-switch-flow (HBC+).json` | HBC+ Home Battery PID presets v1.0 | unchanged |
| `01 start-flow (HBC+).json` | HBC+ Home Battery Start v1.0 | **changed** - new *HBC+ phase planner* and *HBC+ phase guard* nodes; *Batteries (totals)* per phase (Enforce only) |
| `02 strategy-charge (HBC+).json` | HBC+ Strategy Charge v1.0 | **changed** - *Max power solution* respects phase roles and fuse room (Enforce only) |
| `02 strategy-charge-deadline (HBC+).json` | HBC+ Strategy Charge Deadline v1.0 | logic unchanged (uses Self-consumption + totals); documentation updated for HBC+ v1.0 |
| `02 strategy-dynamic (HBC+).json` | HBC+ Strategy Dynamic v1.0 | **changed** - *API call to Data Source* is a link-call section: *Cache check* calls it with a link call and gets the prices back; any other flow can call it too (link call to *Dynamic Fetch from Data Source*, timeout >= 30 s; optional `msg.dynamic.data_source`, `msg.dynamic_use_cache`; reply in `msg.dynamic`); a failed fetch keeps the last valid prices of the same source, falls back to the baseline strategy when none are left, and raises `binary_sensor.hbc_price_data_missing`; `input_text.house_battery_strategy_dynamic_price_sensor` pins the price sensor |
| `02 strategy-full-stop (HBC+).json` | HBC+ Strategy Full stop v1.0 | unchanged |
| `02 strategy-helios (HBC+).json` | HBC+ Strategy Helios v1.0 | unchanged, except its copy of the HA server config node (see below) |
| `02 strategy-partials (HBC+).json` | HBC+ Strategy Partials v1.0 | unchanged |
| `02 strategy-self-consumption (HBC+).json` | HBC+ Strategy Self-consumption v1.0 | **changed** - *Load distribution*: standby soft stop, fuse room per phase (Enforce only) |
| `02 strategy-sell (HBC+).json` | HBC+ Strategy Sell v1.0 | **changed** - *Max power solution*, as Charge (Enforce only) |
| `02 strategy-timed (HBC+).json` | HBC+ Strategy Timed v1.0 | unchanged |
| `03 battery-oscillation-guard (HBC+).json` | HBC+ Battery Oscillation Guard v1.0 | unchanged |
| `03 strategy-arbiter (HBC+).json` | HBC+ Strategy arbiter v1.0 | unchanged |
| `03 phase-monitor (HBC+).json` | HBC+ Phase monitor v1.0 | **new** - read-only, publishes `hbc/phase/*` for the dashboard |
| `hbc-plus-all-flows.json` | all of the above | one import file |

Flows of your own can request a strategy through the *Strategy arbiter* (link call to *Strategy request*, `msg.arbiter = {requester, action: 'hold' | 'release', strategy, reason}`); see the arbiter tab's Info.

## Documentation
Every tab has a **📖 How this flow works - HBC+ v1.0** comment (open it and look in the Info sidebar):
what the flow does, how it runs, and what HBC+ v1.0 changes or does not change in it.

## Safety rules built in
- **Off / Monitor = no phase rules.** Every changed node was tested against the original with the same inputs:
  identical output in Off and Monitor. Only `input_select.house_battery_phase_guard_mode = Enforce` changes anything.
- **Fail-open.** New code runs in try/catch; on an error it warns and passes the message on unchanged.
- **No dependency on another tab** in the control loop: planner and guard live inside *Home Battery Start*.

## HA server config node
All files carry the same copy of the *HA System* server node (`176d29a.6f648d6`), with
**Expose to global context** on. The fast read and the HBC+ planner/guard need that. The original Helios
export carried an older copy with it switched off (named *Home Assistant*); importing that one with Replace
would have switched it off. The HBC+ Helios file carries the correct copy.

## Install
1. **Back up first:** Node-RED menu > Export > All flows > Download.
2. These files are built from the repo exports of 23 Oct - 12 Nov 2026. If you changed one of these tabs in
   Node-RED since then, export that tab into `node-red/` and rebuild it first.
3. Import (menu > Import), choose **Replace** for existing nodes, Deploy (Modified flows) at a quiet moment.
   HBC+ rewrites battery mode and power once after a deploy; that is normal.
4. Home Assistant needs `packages/hbc_phase_guard.yaml` (restart HA) and the HBC+ dashboard
   (`dashboards/hbc_plus.yaml`). Run *HBC+ phase guard: apply defaults* once.
5. Guard mode **Monitor** first: watch the node status of *HBC+ phase planner* / *HBC+ phase guard*
   (`would: ...`) and the Phases view. Switch to **Enforce** only when that looks right.

## Outside Node-RED
- `packages/hbc_heartbeat.yaml` (HA fallback when HBC+ stops) is phase-aware: on Enforce only the lowest
  M-number per shared phase goes back to firmware anti-feed; its partner stays RS485 enable + forcible stop.
