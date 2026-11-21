# HBC+ – Features, security, stability and performance per release

Nov 21, 2026&#32;

## Overview

Every HBC+ release so far has made the controller safer to leave running unattended. 1.0 fixed the errors HBC 4.15.1 let through and cut the work per control tick. 1.1 made failures visible and fail safe. 1.2 and 1.3 keep the new price and automation features from weakening that.

**Credits.** HBC+ is built on HBC (House Battery Control) by **CodeBob**, the founding father of this project ([HBC on GitHub](https://github.com/gitcodebob/marstek-venus-rs485-node-red)). The control loop, the PID-based Self-consumption, the strategies and the Marstek integration all come from his work; HBC+ adds to it. All credit for the foundation goes to him.

| Release | Security | Stability | Performance |
| --- | --- | --- | --- |
| 1.0 (on top of HBC 4.15.1) | Phase guard keeps two batteries on one phase within the fuse and battery circuit | No NaN or stale totals, correct price cache, heartbeat with HA fallback, price-source failures handled | One read node instead of \~43, PID in one node, Timed fast path, fewer Modbus writes, recorder exclusions |
| 1.1 (16 Nov 2026) | Heartbeat judged by HA's own clock, notification on safety-setting changes, no test buttons in live flows | Heartbeat only after a good cycle, held battery values, errors always logged, fail-safe *Enforce*, *Full stop* on phase overload | Busy phase sensors out of the database, quieter failsafe, lighter loop, debounced Dynamic |
| 1.2 (20 Nov 2026) | Public price feed without token or personal data | Price guard with strict safety rules and fail-open; feed failures keep the last prices; supplier choice survives restarts | Feed fetched with ETag (304 when unchanged); buy and sell split once per fetch |
| 1.2.1 (21 Nov 2026) | – | Fresh install works without manual fixes: Node-RED reported ready on every (re)connect, PID preset *Safe* by default, price list no longer hidden | – |
| 1.3 (planned 22 Dec 2026) | HA and MQTT strategy requests validated; reserved requester names | Every external hold expires; calibration restores its settings after any interruption; savings skip gaps | Savings and efficiency computed in HA, busy split-power sensors out of the database |

## HBC+ 1.0

HBC+ 1.0 is HBC 4.15.1 plus below changes. The release was tested on a three-battery setup (two over RS485, one over Modbus TCP).

### Features

| # | Feature | What it does |
| --- | --- | --- |
| – | Phase guard for two batteries per phase | Off, Monitor or Enforce; a planner picks the active battery per phase (*SoC balance*, *Fixed order* or *Rotate daily*) |
| – | Strategies | Self-consumption, Charge, Sell, Timed, Dynamic, Full stop and the partials Charge PV, Zero import and Standby / peak shave |
| F1 | Feed-forward start for regulated charging | Jumps straight to the expected power for 10 s, then the PID trims |
| F2 | Grid Clock (integration) as Dynamic data source | Removed again in 1.2 |
| F3 | Charge Deadline | Charges to a target before a deadline, in the cheapest quarter-hours |
| F4 | Control-loop heartbeat with HA fallback | Hands the batteries back to their firmware when Node-RED stops |
| F5 | Recorder exclusions | Keeps busy entities out of the HA database |
| E1 | Strategy arbiter | The only writer of the strategy choice; lets other flows hold a strategy |
| E2 | Battery Oscillation Guard | Detects charge/discharge waves and holds *Full stop* for a while |
| E3 | Marstek over Modbus TCP | A battery without RS485 works too |
| E4 | P1 alias | For a meter that does not provide `sensor.p1_meter_power` |

### Security

| # | Security Change | Why it matters |
| --- | --- | --- |
| – | Phase guard (Off, Monitor, Enforce) | Two batteries on one phase can draw 5000 W on a 16 A group. On *Enforce* only the active battery per phase runs, within the grid fuse and the battery circuit. Off and Monitor were tested identical to the original. |

### Stability

| # | Stability Change | Why it matters |
| --- | --- | --- |
| B1 | No `initial: 0` on the five totals helpers | HA reset them on every restart and they stayed at 0; anything dividing by them broke. |
| B3, B4 | Price cache tied to its source; refetch until tomorrow is in | A source switch kept serving the old prices, and tomorrow stayed empty until 15:01. |
| B7 | Debug board shows the trace again | A 4.15.1 regression sent the last setpoint instead of the trace. |
| R1 | *Batteries (totals)* never sends NaN | One unavailable value made every total NaN and HA errors on every cycle. A value is held for 5 min; after that the battery counts as 0. |
| R2 | One consistent HA server node in every file | Differing copies broke the fast read path after an import. |
| R3 | Price fetch failure: last valid prices, baseline fallback, alert | A failed source no longer leaves Dynamic on its last strategy, which could be grid charging. |
| R4 | Price sensor can be pinned | Stops the macro guessing the wrong sensor when two price integrations are installed. |
| F4 | Control-loop heartbeat with HA fallback | If Node-RED stops, HA hands the batteries back to their firmware instead of leaving the last setpoint active. |

### Performance

| # | Performance Change | Effect |
| --- | --- | --- |
| P1 | *Read HA states (fast)* | One node instead of \~43 sequential reads per tick, with a fallback to the old chain. |
| P2 | *PID step* | 13 nodes in one, with a PID-settings cache refreshed every 60 s. |
| P3 | *Pick period* | Timed decides in one node with a settings cache, instead of \~45 nodes. |
| P4 | Fewer Modbus writes | Mode only when it changes (or every 60 s), only the power register of the current mode, one battery at a time. |
| F5 | Recorder exclusions | The price list and the Charge Deadline sensors no longer write a full copy to the database every update. |

## HBC+ 1.1

Released 16 November 2026. 1.1 makes failures visible and makes Home Assistant step in when something goes wrong.

### Features

1.1 added no new functions; it is a safety, security and performance release.&#32;

| Feature | What it does |
| --- | --- |
| F1-`sensor.hbc_health` with alert | Status of the control loop (`ok`, `warning`, `error`), with a notification when errors keep coming |
| F2-*Full stop* on phase overload | HA stops the batteries when they keep a phase overloaded |
| F3-Notification on safety-setting changes | Names who changed the phase guard settings |
| F4-Fixed dashboard view paths | Links between views always work (`/home-battery-control-plus/<view>`) |
| F5-*Securing your setup* | Guide section on protecting Node-RED, MQTT and the dashboard |

### Security

| # | Security Change | Why it matters |
| --- | --- | --- |
| S1 | Heartbeat judged by when HA received it | A message with a future time (spoofed, or a Node-RED clock running ahead) could keep the fallback off forever. |
| S2 | Notification when a phase guard safety setting changes | HA has no per-entity permissions, so any user or automation can change the fuse limits; now every change is reported with who made it. |
| S3 | Test buttons removed from the live flows | A stray click could no longer trigger test actions on a running system. |

The guide also gained *Securing your setup*: how to protect the Node-RED editor, MQTT (`hbc/#`) and the dashboard.

### Stability

| # | Stability Change | Why it matters |
| --- | --- | --- |
| R5 | Heartbeat fallback no longer undone by the Master Switch | The switch turned RS485 back on while the loop was still dead. |
| R6 | Heartbeat only after a good control cycle | A running but failing loop kept the heartbeat alive. |
| R7 | One unavailable battery value no longer stops every battery | Held values reach the strategies; every setpoint is checked before it is written. |
| R8 | Warnings and errors always logged; `sensor.hbc_health` with alert | Errors were invisible with Insight mode off. |
| R9 | Fail-safe on *Enforce* | An error in the phase guard falls back to one battery per phase, not to no rules. |
| R10 | *Full stop* when the batteries keep a phase overloaded | HA acts on its own when a phase stays above its limit for 10 s with the batteries part of the cause. |
| R11 | Warning when a battery keeps ignoring commands | A battery stuck on old setpoints is reported. |
| R12 | Charge/Sell thresholds, logger fallback, 1 s link-call timeouts | A slow strategy now fails in its own tab instead of stalling the loop; the *smooth* palette is gone. |

### Performance

| # | Performance Change | Effect |
| --- | --- | --- |
| P5 | Busy phase sensors out of the HA database | Less recorder load; the PID terms are recorded again (at most every 10 s) for the PID graph. |
| P6 | Output failsafe warns once | No log flood every tick. |
| P7 | *Trace* in JavaScript everywhere; one node writes the totals | No JSONata on every tick; totals written only when they change (refresh every 30 min). |
| P8 | Dynamic waits 3 s after the last setting change | One recalculation instead of one per changed setting. |

## HBC+ 1.2

Released 20 November 2026.

Targeting the end of Dutch net metering. With default settings it behaves exactly like 1.1

### Features

| # | Feature | What it does |
| --- | --- | --- |
| F6 | Grid Clock feed | New tariff source with all-in buy and sell prices per quarter for your own supplier (and BE grid operator), public and without a token |
| F7 | Buy and sell prices | Every quarter has both; Dynamic values *Sell* at the sell price; *Sell now* tile and a sell line in the price chart |
| F8 | Price guard | At negative prices stops exporting and charges instead (Off, Monitor, On), with signals for a PV limiter |
| – | Remove: Grid Clock (integration) source | Replaced by the Grid Clock feed |

### Security and privacy

| Security Change | Why it matters |
| --- | --- |
| Prices from a public feed on `cdn.gridclock.eu`, no account or token | Nothing to register, copy, leak or renew. |
| Only the zone and the supplier's short name are in the request | Grid Clock stores nothing about HBC+ users; the requests pass Cloudflare like any web request, without logging. |
| No Cloudflare rate-limit rule | The zone stays on the Free plan. The files are small, cacheable and the same for everyone, so misuse costs little. |

### Stability

| Stability Change | Why it matters |
| --- | --- |
| Price guard safety rules | *On* only with the Grid Clock feed (real all-in prices); *Full stop* is never overridden; no override while the EV stop trigger is on; charging at negative import prices only on phase guard *Enforce* or with no shared phase. |
| Price guard is fail-open and Off by default | A missing entity or `msg.price_override` means no change; *Monitor* shows what it would do without acting. |
| Feed failures keep the last valid prices | Same rule as every source; `sensor.hbc_grid_clock_feed` shows the error and the reason. |
| Supplier choice survives restarts | The index waits for HA's states and never guesses a zone, reloads after every HA (re)connect, and ignores an index for a zone that is no longer selected. |
| Grid Clock integration source removed | One custom integration less to depend on. |
| Pairing with sell prices keeps the 1.1 code path | When the expensive side is valued at the buy price, the v1.1 pairing runs unchanged. |

### Performance

| Performance Change | Effect |
| --- | --- |
| Feed fetched with `If-None-Match` | An unchanged file costs a `304`, no download. |
| *Price split* runs once, inside the fetch section | The cache and every link-call caller get the same buy and sell lists without recomputing. |
| Price state as an HA template | `sensor.hbc_price_state` works even when Node-RED is down, and costs Node-RED nothing per tick. |

## HBC+ 1.2.1

Released 21 November 2026. A maintenance release: fixes found while testing a fresh install of 1.2, and clearer installation steps.

### Features

| Feature | What it does |
| --- | --- |
| *Pricing List* switch on the Prices view | Shows or hides the price list (*Price marks visualisation*) on its own; no longer switches Insight mode (Logging *Live*) on |

### Security

No security changes.

### Stability

| Stability Change | Why it matters |
| --- | --- |
| Node-RED reported ready on every (re)connect | Node-RED turned on `input_boolean.house_battery_control_has_node_red` only once, 2 s after deploy, often before it was connected to Home Assistant; the dashboard then kept showing *Step 3 — Setup Node-RED*. |
| *Apply defaults* also sets the PID preset *Safe* | On a fresh install all PID gains were 0: Self-consumption did nothing and logged *Controller disabled* on every tick. The gains are set directly, so this also works before the Node-RED flows are imported. |
| Price list and *Using the dynamic strategy* link no longer depend on a Marketplace update entity | They stayed hidden when the Marketplace reported `update.cheapest_energy_hours_update` as unknown or unavailable, as it often does on a fresh install. |

### Performance

No performance changes.

### Documentation

| Change | Why it matters |
| --- | --- |
| *Before you start — install from Marketplace* | Cheapest Energy Hours, card-mod and apexcharts-card are installed before step 1; card-mod is now listed as required. |
| Requirements as a bullet list, also in the README | Easier to check before you start. |
| Dashboard URL must be `home-battery-control-plus` | The buttons that open other views link to that address; the dashboard name itself does not matter. |

## HBC+ 1.3

Planned for 22 December 2026.

### Features

| Feature | What it does |
| --- | --- |
| F9-Savings | New *Savings* view: cost with and without batteries per day, month and year, split into stored PV and charging from the grid |
| F10-Measured round-trip efficiency | Efficiency over 7 days, a suggested *Minimum spread* with an *Apply* button, and an optional switch that makes Dynamic pair on efficiency × high − low |
| F11-One notification setting | Every alert goes through `script.hbc_notify`; set the targets once and send a test |
| F12-Battery calibration | A full charge in the cheapest block after midnight when a battery has not been full for 14 days; charge cutoff to 100 % for that night |
| F13-Strategy requests from Home Assistant | Hold and release a strategy with an HA script or MQTT, with time-outs; *Held by* line on the Home view |

### Security

| Security Change | Why it matters |
| --- | --- |
| Strategy requests from HA and MQTT are checked before they reach the arbiter | Requester must be 1–32 characters a–z, 0–9 or \_; the strategy must exist; anything else is rejected and answered on `hbc_arbiter_result`. |
| Reserved requester names `guard` and `manual` | An outside automation cannot pose as the Oscillation Guard or as a manual choice. |
| Priorities unchanged for outsiders | Requests from HA get 50, the calibration 40, the Oscillation Guard 100; a manual choice always wins. |
| MQTT entry documented with broker restrictions | The guide asks to limit who may publish on `hbc/#`. |

### Stability

| Stability Change | Why it matters |
| --- | --- |
| Every hold from HA or MQTT expires (default 120 min, max 24 h) | A crashed automation can never keep the batteries on a held strategy. The expiry is stored with the hold, so it survives a restart. |
| Hold and release scripts refuse when HBC+ is not running | They stop with an error instead of failing silently. |
| Calibration saves and restores the Charge Deadline settings and charge cutoffs | Restored on success, after the block, on a manual strategy choice and after an HA restart; the cutoff never stays at 100 %. |
| Calibration gives up after three failed nights | No endless nightly grid charging when something else is wrong. |
| One notification script for every alert | Invalid targets are skipped and logged, one failing target doesn't block the others, and alerts are queued so none are lost. |
| Savings skip gaps and counter resets | A quarter after an HA outage, without a price, or with a counter reset is never estimated; it is counted in `quarters_missing`. |
| Efficiency sanity check | Above 100 % or below 50 % points to wrong power-sensor signs instead of feeding a bad number to the suggestion. |
| Efficiency in Dynamic is off by default | Off, or with the efficiency unknown, Dynamic pairs exactly as in 1.2 (120 of 120 price lists identical); on, it never marks more pairs. |

### Performance

| Performance Change | Effect |
| --- | --- |
| Savings and efficiency computed in HA | No extra work in the Node-RED control loop, and the counting continues while Node-RED is down. |
| Split-power sensors and the calibration status out of the recorder | The four sensors that change every few seconds write nothing to the database; the energy counters built from them are recorded. |
| Day, month and year totals from utility meters | No templates re-summing history. |
