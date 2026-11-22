# HBC+ - complete Node-RED flow set (v1.2, release planned 2026-12-10)

Everything Node-RED needs for HBC+ (Home Battery Control Plus), a standalone home battery controller with the phase guard for
2 batteries per phase. All tabs are named `HBC+ ... v1.2`. Node-RED cannot replace a flow tab on import (it skips it or
imports a copy), so delete the old HBC+ tabs before you import a new version (see *Install*).

**Quickest install:** import `hbc-plus-all-flows.json` (all 16 tabs, HA server config node once).
Or import the files one by one.

**Version check (v1.3).** Every tab has a node *HBC+ version* (no wires) that registers the tab's HBC+ version when the
flow starts and removes it when the flow stops. *HBC+ health (hbc/health)* on the Start tab compares them with each other,
with the list of expected tabs and with `sensor.hbc_package_version`, and warns *HBC+ version mismatch*. On a release,
bump `VERSION` in every *HBC+ version* node, in *HBC+ health* and in `packages/hbc_control.yaml`.

## Contents

| File | Tab | HBC+ change |
| --- | --- | --- |
| `00 master-switch-flow (HBC+).json` | HBC+ Home Battery Master Switch v1.4 | **changed** - hand-back to firmware: partner on a shared phase stays RS485 + stop (Enforce only); the periodic check skips *Full control* while `binary_sensor.hbc_heartbeat_stale` is on (*Skip while HBC heartbeat is stale*), *HBC heartbeat back* re-applies it once the heartbeat is fresh |
| `00 presets-switch-flow (HBC+).json` | HBC+ Home Battery PID presets v1.4 | unchanged |
| `01 start-flow (HBC+).json` | HBC+ Home Battery Start v1.4 | **changed** - new *HBC+ phase planner* and *HBC+ phase guard* nodes; *Batteries (totals)* per phase (Enforce only); heartbeat only after a good cycle (link *HBC+ cycle result*); *Batteries (totals)* also hands held values to the strategies and marks a battery without data as not driven; *Set Batteries* validates every solution and skips batteries with RS485 off; *Custom logger* always logs warnings and errors; *HBC+ health* publishes `hbc/health`; *Totals to HA (on change)* replaces five *On change* nodes (with a 30-min refresh); Enforce fail-safe and a warning for batteries that ignore commands in *Set Batteries*; v1.3: *HBC+ health* runs the version check (*HBC+ version mismatch*, `version_ok`, `version_issues`) |
| `02 strategy-charge (HBC+).json` | HBC+ Strategy Charge v1.4 | **changed** - *Max power solution* respects phase roles and fuse room (Enforce only); threshold checks fixed for unavailable helpers |
| `02 strategy-charge-deadline (HBC+).json` | HBC+ Strategy Charge Deadline v1.4 | logic unchanged (uses Self-consumption + totals); documentation updated for HBC+ v1.0; *Trace* in JavaScript |
| `02 strategy-dynamic (HBC+).json` | HBC+ Strategy Dynamic v1.4 | **changed** - *API call to Data Source* is a link-call section: *Cache check* calls it with a link call and gets the prices back; any other flow can call it too (link call to *Dynamic Fetch from Data Source*, timeout >= 30 s; optional `msg.dynamic.data_source`, `msg.dynamic_use_cache`; reply in `msg.dynamic`); a failed fetch keeps the last valid prices of the same source, falls back to the baseline strategy when none are left, and raises `binary_sensor.hbc_price_data_missing`; an error inside the section is caught (*Catch fetch errors*) and handled the same way, so a caller always gets a reply; `input_text.house_battery_strategy_dynamic_price_sensor` pins the price sensor; test nodes removed (*Test*, *Fetch*, *Debug ON*); *User input* waits 3 s after the last change; *Trace* in JavaScript; v1.4: *Determine dynamic strategy* step 3b, optional load forecast: keeps only the cheap quarters the expensive quarters need (switch off: identical); v1.3: *Data source settings* reads every source name that starts with *Grid Clock* as the Grid Clock feed |
| `02 strategy-full-stop (HBC+).json` | HBC+ Strategy Full stop v1.4 | *Trace* in JavaScript, logic unchanged |
| `02 strategy-helios-placeholder (HBC+).json` | HBC+ Strategy Helios (placeholder) v1.4 | **new** - keeps the *Helios* strategy option safe until a HELIOS integration exists: runs *Full stop* and warns at most every 10 min; delete it before importing a real HELIOS flow (link in named *Helios*) |
| `02 strategy-partials (HBC+).json` | HBC+ Strategy Partials v1.4 | *Trace* in JavaScript, logic unchanged |
| `02 strategy-self-consumption (HBC+).json` | HBC+ Strategy Self-consumption v1.4 | **changed** - *Load distribution*: standby soft stop, fuse room per phase (Enforce only); a limit or PID output that is not a number counts as 0 W; *PID step* warns once (not every tick) when the output failsafe is inactive; disabled *smooth* nodes removed |
| `02 strategy-sell (HBC+).json` | HBC+ Strategy Sell v1.4 | **changed** - *Max power solution*, as Charge (Enforce only); threshold checks fixed for unavailable helpers |
| `02 strategy-timed (HBC+).json` | HBC+ Strategy Timed v1.4 | **changed** - test inject *Test* removed; *Trace* in JavaScript |
| `03 battery-oscillation-guard (HBC+).json` | HBC+ Battery Oscillation Guard v1.4 | **changed** - caught errors go to the HBC+ logger (*Log error (HBC+ logger)*) |
| `03 self-test (HBC+).json` | HBC+ Self-test v1.4 | **new (v1.4)** - setup self-test: *Flow check* answers `hbc_selftest_flow_check`; *Self-test controller* measures per battery on which P1 phase its charging power shows up; link in *Self-test* is the strategy used during the test (battery under test charges, the rest stops; a plan older than 2 min = all stop) |
| `03 strategy-arbiter (HBC+).json` | HBC+ Strategy arbiter v1.4 | **changed** - caught errors go to the HBC+ logger (*Log error (HBC+ logger)*); test inject *TEST: simulate oscillation* removed; v1.4: requester `selftest` (setup self-test) gets priority 90 |
| `03 phase-monitor (HBC+).json` | HBC+ Phase monitor v1.4 | **new** - read-only, publishes `hbc/phase/*` for the dashboard; caught errors go to the HBC+ logger |
| `hbc-plus-all-flows.json` | all of the above | one import file |
| `examples/price-fetch-example.json` | HBC+ Example: price fetch | **new** - example of the shared price fetch (dynamic link call, reading the price now); not in the all-flows file |

## Changes in v1.2
- **Dynamic:** *Data source settings* has a second output for the source *Grid Clock* (the Grid Clock feed): *Grid Clock feed request* -> *Grid Clock feed* (http request, ETag) -> *Grid Clock feed parse* -> *Cleanup*; the status goes to the HA event `hbc_gridclock_status`. New *Price split* (before *Cache data source*) gives every source a sell list (sell = buy without the feed). *Determine dynamic strategy* adds `sell` and `neg` to every mark and values the HIGH side at the sell price when the expensive strategy is *Sell* (otherwise the v1.1 code runs unchanged). New group *Grid Clock suppliers* fills the supplier and grid-operator selects from `index.json`. *Selected* applies the price guard. *Index request* waits for HA's states and never guesses a zone; *HA (re)started* reloads the index after every (re)connect, so the chosen supplier and grid operator show again after a restart. The old *Grid Clock* (integration) case is gone.
- **Start:** *Read HA states (fast)* reads the price-guard entities as optional (a missing one is never a fallback). *Strategy selection* builds `msg.price_override` once per tick and applies it to the top-level strategy; *HBC+ price guard status* fires `hbc_price_guard_status` when it changes.
- **Timed** (*Pick period*), **Charge** (*Set reached strategy*, new *Price goal*), **Sell** (*Strategy after reached*): apply the price guard.
- **All tabs:** names end in v1.2; the *How this flow works* texts of Start, Dynamic, Timed, Charge and Sell describe the v1.2 changes.

## Changes in v1.1
The table above shows each tab's changes compared with HBC. New in v1.1 (details in the user guide, *What's new in HBC+ v1.1*):
- **Robustness (R5-R12):** heartbeat only after a good cycle and no longer undone by the Master Switch; held values and checked
  setpoints, so no NaN reaches the batteries; warnings and errors always logged and published to `sensor.hbc_health`; fail-safe
  on Enforce; a battery that keeps ignoring commands is reported; Charge/Sell threshold fixes, logger fallback, 1 s link-call
  timeouts inside the control loop; the *smooth* nodes are gone.
- **Security (S3):** test injects removed from Dynamic, Timed and the Oscillation Guard.
- **Performance (P6-P8):** the output failsafe warns once; *Trace* in JavaScript and one node for the totals; Dynamic waits 3 s
  after the last setting change.
- **Layout:** tabs tidied; the junctions in Charge and Sell are gone (same connections).
- **All tabs:** names end in v1.1.

Flows of your own can request a strategy through the *Strategy arbiter* (link call to *Strategy request*, `msg.arbiter = {requester, action: 'hold' | 'release', strategy, reason}`); see the arbiter tab's Info.

## Documentation
Every tab has a **📖 How this flow works - HBC+ v1.2** comment (open it and look in the Info sidebar):
what the flow does, how it runs, and what HBC+ changes or does not change in it.

## Safety rules built in
- **Off / Monitor = no phase rules.** Every changed node was tested against the original with the same inputs:
  identical output in Off and Monitor. Only `input_select.house_battery_phase_guard_mode = Enforce` changes anything.
- **Fail-safe on Enforce.** New code runs in try/catch. On Off / Monitor an error warns and passes the message on unchanged; on Enforce, *Set Batteries* applies the strict rule (per shared phase only the lowest M-number runs, at most battery circuit - margin).
- **Link calls inside the control loop** time out after 1 s, like the loop itself; the price fetch and the Strategy arbiter calls keep 30 s.
- **Logger fallback.** Every node that uses the HBC+ logger falls back to a do-nothing function when it is not set yet.
- **No dependency on another tab** in the control loop: planner and guard live inside *Home Battery Start*.
- **Heartbeat = working loop.** *HBC+ heartbeat* only publishes after a good cycle (the strategy returned without an error, at least one battery written without an error).
- **No NaN to the batteries.** Held values reach the strategies; *Set Batteries* checks mode and power of every solution before it is written.
- **Errors are visible.** Warnings and errors reach the Node-RED log (the same message at most once a minute) and `hbc/health` -> `sensor.hbc_health`, also with Insight mode off.

## HA server config node
All files carry the same copy of the *HA System* server node (`176d29a.6f648d6`), with
**Expose to global context** on. The fast read and the HBC+ planner/guard need that.

## Install
1. **Back up first:** Node-RED menu > Export > All flows > Download.
2. These files are built from the repo exports of 23 Oct - 12 Nov 2026. If you changed one of these tabs in
   Node-RED since then, export that tab into `node-red/` and rebuild it first.
3. Updating? First delete every tab whose name starts with *HBC+* (double-click the tab > Delete) and do not deploy yet.
   Then Import (menu > Import); if Node-RED reports that the *HA System* server node already exists, leave it unselected.
   Deploy (Modified flows) at a quiet moment.
   HBC+ rewrites battery mode and power once after a deploy; that is normal.
4. Home Assistant needs `packages/hbc_phase_guard.yaml` (restart HA) and the HBC+ dashboard
   (`dashboards/hbc_plus.yaml`). Run *HBC+ phase guard: apply defaults* once.
5. Guard mode **Monitor** first: watch the node status of *HBC+ phase planner* / *HBC+ phase guard*
   (`would: ...`) and the Phase guard view. Switch to **Enforce** only when that looks right.

## Outside Node-RED
- `packages/hbc_heartbeat.yaml` (HA fallback when HBC+ stops) is phase-aware: on Enforce only the lowest
  M-number per shared phase goes back to firmware anti-feed; its partner stays RS485 enable + forcible stop.
  Every battery handed back gets forcible stop first. The package also holds `sensor.hbc_health` and the alert
  *HBC+: alert when the control loop keeps logging errors*.
