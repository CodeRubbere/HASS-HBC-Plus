# HBC+ v1.0 — User guide

*14 November 2026* · 🇳🇱 [Nederlandse versie](gebruikershandleiding.nl.md)

## What HBC+ is

HBC+ (Home Battery Control Plus) v1.0 controls up to six home batteries from Home Assistant and Node-RED, and lets two batteries share one phase without overloading that phase's main fuse. With the phase guard in *Off* or *Monitor* the batteries are controlled without phase rules; only *Enforce* applies them.

Besides the phase guard, HBC+ v1.0 brings improvements in three areas:

- **Safety and security** — per-phase main-fuse protection, fail-open code that falls back to control without phase rules on an error, an HA alarm that works without Node-RED, and a heartbeat that hands the batteries back to their firmware when the control loop stops.
- **Performance** — one fast read node instead of ~43 separate reads, the PID step and the Timed period choice merged with settings caches, and fewer Modbus writes per tick.
- **Stability** — bug fixes (among others: total helpers reset to 0 after a restart, a price cache that kept old prices after a source change, the debug board), totals that never send NaN to HA, and one consistent HA server node in every flow file.

It also adds two features:

- **Charge Deadline strategy** — charges to a target (full, SoC or energy reserve) before a deadline, in the cheapest quarter-hours, with optional PV reserve and a follow-up strategy once the deadline has passed. See [Charge Deadline](#charge-deadline).
- **GridClock as data source** — Dynamic and Charge Deadline can read prices from the [Grid Clock](https://gridclock.eu) integration (`sensor.grid_clock_<zone>_prices`). Prices refresh automatically when the default zone changes. See [Dynamic](#dynamic).

All changes are described in full in the section [Improvements in HBC+ v1.0](#improvements-in-hbc-v10) below.

What the phase guard adds:

- **A phase map.** Every battery (M1–M6) is assigned to L1, L2, L3 or *Own circuit*.
- **One active battery per phase** (default). The partner on that phase waits at 1 W idle and then stops, the same way HBC+ parks batteries it does not need.
- **Two limits per phase.** The active battery only gets the room left under both the main (grid) fuse, after the house load on that phase, and the battery circuit the batteries of that phase share (default 16 A ≈ 3680 W each), recomputed every tick from the P1 meter.
- **Correct planner ceiling.** The max power HBC+ reports to Charge Deadline and HELIOS is the sum per phase, not the sum of all batteries, so those planners book enough charge hours.
- **A Phases dashboard** and an independent overload alarm in Home Assistant that works even when Node-RED is down.
- **An optional *Shared headroom* mode** in which both batteries on a phase may run at once, as long as together they stay under the fuse.

Net effect with two batteries per phase (6 × Marstek Venus E, 5.12 kWh each): usable capacity doubles to about 30.7 kWh, peak power stays 7.5 kW (3 × 2500 W).

Why the phase guard works the way it does is explained in [Design background and decisions](#design-background-and-decisions).

### Credits

HBC+ is a standalone version with its own development. It started from House Battery Control (HBC) v4.15.1 by **CodeBob** ([gitcodebob](https://github.com/gitcodebob/marstek-venus-rs485-node-red)), the founding father of HBC: the original control loop, strategies, dashboard and helpers are his work, and all credit for that foundation goes to him. HBC+ has no further link with HBC.

Dynamic and Charge Deadline use the [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) macro by **TheFes**.

## Architecture

HBC+ has three parts: Home Assistant packages that hold the settings and an independent alarm, the Node-RED control loop that does the limiting, and a dashboard that shows what happens per phase.

```mermaid
flowchart LR
  subgraph HA["Home Assistant"]
    M["Grid meter and batteries<br/>P1 per phase · Marstek M1–M6"]
    P["hbc_phase_guard.yaml<br/>settings · phase map"]:::new
    T["Template sensors, alarm<br/>fuse room per phase · overload 10 s"]:::new
    Q["MQTT status sensors<br/>active battery and reason per phase"]:::new
    D["Phases view<br/>HBC+ dashboard"]:::new
    Q --> D
  end
  subgraph NR["Node-RED"]
    R["Read HA states (fast)"] --> B["Batteries (totals)"] --> PL["HBC+ phase planner"]:::new --> S["Strategy selection"] --> G["HBC+ phase guard"]:::new --> W["Set Batteries (Modbus)"]
    S --> ST["Strategy tabs<br/>Self-consumption · Charge · Sell · Timed · Dynamic"]
    PM["Phase monitor<br/>read-only · 5 s"]:::new
  end
  M -- reads --> R
  W -- writes --> M
  PM -- "MQTT hbc/phase/*" --> Q
  classDef new stroke-width:3px
```

*Thick border = phase guard.* The planner and guard run inside *HBC+ Home Battery Start*, so the limiting never depends on another tab. The Phase monitor tab only reports; the template sensors and the overload alarm run in Home Assistant and keep working when Node-RED is down.

## Functionality

### The control loop

On every update of `sensor.p1_meter_power` (rate limited), *HBC+ Home Battery Start* runs one tick:

1. **Read HA states (fast)** reads all batteries (M1…M*n*, `input_number.house_battery_count`) and settings in one node from the Home Assistant states in global context. If those are missing it falls back to the original chain of current-state nodes.
2. **Batteries (totals)** computes total battery power, max charge/discharge power and usable energy, and writes them to the `input_number.house_battery_total_*` helpers. A briefly unavailable value is held for up to 5 min.
3. **Update battery order** rotates battery priority.
4. **HBC+ phase planner** (new) works out per phase who may run and how much room there is.
5. **Strategy selection** calls the strategy tab named in `input_select.house_battery_strategy`. It returns `msg.solutions`: one `{id, mode, power}` per battery.
6. **HBC+ phase guard** (new) checks the solutions one last time.
7. **Write limiter → Set Batteries** writes power, then mode, per battery, only when a value changed (awaited writes, 60 s keep-alive on mode).
8. **HBC+ heartbeat** publishes the time to MQTT `hbc/heartbeat`, at most once a minute. If it stops, Home Assistant hands the batteries back to their firmware (see F4).

### Guard modes

`input_select.house_battery_phase_guard_mode` decides whether the phase rules do anything.

| Mode | What HBC+ does | Use it for |
| --- | --- | --- |
| Off | Planner and guard pass every message untouched: no phase rules. | One battery per phase, or to rule HBC+ out while debugging |
| Monitor (default) | Computes and publishes what it *would* do; node status shows `would: …`. Changes nothing. | Commissioning; checking the plumbing before batteries share a phase |
| Enforce | Applies the phase rules in the planner, the strategies, the guard and the master switch. | Normal operation with two batteries on a phase |

Every changed node was tested against the original with the same inputs: Off and Monitor give identical output.

### Phase rules (Enforce)

1. **Phase map.** Each battery has a phase from `input_select.marstek_mN_phase`: L1, L2, L3 or *Own circuit* (never shared, no phase rule).
2. **One active battery per shared phase.** The others get the 1 W idle setpoint (relay engaged) and, after the normal idle time, stop. This is the same soft-stop path HBC+ uses for batteries it does not need.
3. **Room per phase.** House net on a phase = P1 phase power minus battery power on that phase (import positive). Charge room = min(grid fuse − margin − house net, battery circuit − margin); discharge room = min(grid fuse − margin + house net, battery circuit − margin). The grid fuse carries house and batteries together; the battery circuit carries only the batteries. Both rooms are also capped at the battery's own max and recomputed every tick.
4. **Selection.** Candidates are batteries on that phase with RS485 `enable`, fresh values, and SoC above min (discharge) or below max (charge).
   - *SoC balance* (default): discharge from the fullest, charge into the emptiest. The current battery is kept until the SoC gap reaches the swap delta (5 %) **and** it has run for the minimum dwell (15 min). A change of direction may re-pick at once.
   - *Fixed order*: lowest M-number first, the partner only as backup.
   - *Rotate daily*: the primary swaps at midnight.
5. **Break-before-make handover.** The old battery goes to idle first; the new one is released only once the old one measures below 100 W. If the old battery's read-back is missing or stale, the partner stays blocked: a Marstek that lost Modbus may still be running its last command.
6. **Last-line guard.** Just before the writes, the guard corrects any phase with more than one active battery or a setpoint above the fuse room, and logs it. This also covers future strategies that ignore the rules.

Example: with grid fuse and battery circuit both at 3680 W and 1800 W of house load on L1, the active L1 battery may charge at 3680 − 200 − 1800 = 1680 W; with 3000 W of PV export on L1 it may discharge only 480 W. With a 7360 W grid fuse the same 1800 W leaves 5360 W under the grid fuse, so the battery circuit decides: 3680 − 200 = 3480 W.

### Shared headroom (option)

With `input_select.house_battery_phase_sharing` = *Shared headroom*, both batteries on a phase may run at once, as long as together they stay inside the fuse room. Rules 1, 3 and 6 stay; rules 2 and 5 are replaced by:

- **Fill order** follows the selection rule: the first battery gets min(its max, room), the partner gets what is left, up to its own max.
- **Minimum share:** the partner starts only when at least 300 W is left and stops again below 100 W.
- **Unknown counts as busy:** a battery with a stale read-back is counted at its last setpoint.

Typical gain: 2500 + 1000 W charging on a phase with no house load. The fallback when HBC+ is down still hands only one battery per phase to firmware.

### What changes per strategy

| Tab | HBC+ change (Enforce only) |
| --- | --- |
| Home Battery Start | New *phase planner* and *phase guard*; *Batteries (totals)* counts max power per phase |
| Self-consumption | *Load distribution* soft-stops standby batteries and caps each phase at its fuse room; anti-windup uses the capped capacity |
| Charge, Sell | *Max power solution* runs only the active battery per phase, at min(its max, fuse room); the partner idles at 1 W |
| Master Switch | On hand-back to firmware only the lowest M-number on a shared phase gets RS485 *disable*; the partner stays RS485 *enable* + forcible *stop* |
| Charge Deadline, Helios | Logic unchanged; they plan with the per-phase max power from *Batteries (totals)* |
| Partials, Timed, Dynamic (price fetch: see below), Full stop, PID presets, Oscillation Guard, Strategy arbiter | No change; whatever they run goes through Self-consumption or Max power, which apply the rules |
| Phase monitor | **New**, read-only: publishes `hbc/phase/*` for the dashboard every 5 s (republished on change, at most every 30 s otherwise) |

### Shared price fetch (Dynamic)

The *API call to Data Source* section of *HBC+ Strategy Dynamic* is a link-call subroutine, so any flow can fetch the current price list without its own copy of the data-source logic. Inside the Dynamic tab, *Cache check* calls it on a cache miss; the prices come back and go on to *Determine strategy*, as on a cache hit.

To use it from another flow, add a **link call** node, pick *Dynamic Fetch from Data Source*, and set a timeout of at least 30 s. The first node of the section, *Prepare request*, fills in what the caller leaves out.

| msg property | In / out | Meaning |
| --- | --- | --- |
| `dynamic.data_source` | in, optional | Price source; default = `input_select.house_battery_strategy_dynamic_data_source` |
| `dynamic_use_cache` | in, optional | `true` = return the Dynamic tab's cached prices if still valid (same rule as *Cache check*: after 13:00 they must cover tomorrow), else fetch |
| `dynamic` | out | `{data_source, data_all: {list, list_marked, average, min, max, start, …}, no_data?}` |
| `dynamic_from_cache` | out | `true` when the cache answered |

- Source *None*, or a source Node-RED cannot read, returns at once with `dynamic.no_data = true` and an empty list, so the caller never waits for the timeout.
- A successful fetch from any caller also refreshes the Dynamic tab's cache.
- The rest of the caller's message comes back unchanged (`msg.template` is used and removed).
- A fetch that fails inside the section makes the link call time out after 30 s; the error goes to *Strategy errors* in the Dynamic tab.
- A fetch that delivers no prices returns the last valid list of the same source with `dynamic.stale = true` while it still covers the current interval, otherwise `dynamic.no_data = true` (see R3).

### Effect on planners

Because *Batteries (totals)* writes the effective max into the existing helpers, Charge Deadline, HELIOS and the PID anti-windup need no code change.

| Value | 3 batteries (today) | 6 batteries, no phase rule | 6 batteries, Enforce |
| --- | --- | --- | --- |
| `house_battery_total_max_charge_power` | 7500 W | 15000 W | 7500 W |
| Usable energy | ~15.4 kWh | ~30.7 kWh | ~30.7 kWh |
| Hours to charge 0→100 % at max | ~2 h | ~2 h (but trips a fuse) | ~4 h |

The planner value follows the fuse room. On *Enforce*, *Batteries (totals)* subtracts the average house load per phase (exponential average over about 15 minutes) from the fuse room, rounds the result to 100 W and only changes the value when it moves by 250 W or more. A heat pump that runs for half an hour lowers the planner value; a kettle for a few seconds does not. Example: with 2 kW of house load on L1 for an hour, the charge ceiling settles at about 6200 W instead of 7500 W, so Charge Deadline books extra cheap quarters. When the load stops, the value returns within about 15 minutes.

### Safety built in

- **Fail-open.** Planner, guard and totals run in try/catch. On an error they warn and pass the message on unchanged, i.e. control without phase rules.
- **No cross-tab dependency** in the control loop: planner and guard live inside *Home Battery Start*. Disabling the Phase monitor tab changes nothing.
- **Independent alarms.** `binary_sensor.hbc_phase_limit_exceeded` turns on when grid power on any phase exceeds the grid fuse for 10 s; `binary_sensor.hbc_phase_circuit_limit_exceeded` when the batteries on any phase draw more than the battery circuit for 10 s. Both are pure Home Assistant and work when Node-RED is down.

## Strategies and settings

This section explains what each strategy does and which settings steer it. The dashboard's ⓘ links point here.

### Master mode

`input_select.marstek_master_battery_mode` decides who controls the Marsteks. HBC+ only steers the batteries in **Full control**.

| Master mode | RS485 control | Who controls |
| --- | --- | --- |
| Full control | enable | HBC+ (forcible charge / discharge) |
| Marstek control | disable | The Marstek firmware, in the work mode you chose in the Marstek app |
| Manual control | disable | The Marstek firmware, manual mode |

### Choosing a strategy

Pick the strategy in `input_select.house_battery_strategy`. The *Strategy arbiter* is the only writer of that helper: the Battery Oscillation Guard, and flows of your own (for example a PV limiter), can hold another strategy for a while and give your choice back afterwards (see *Installation*, Step 3).

| Strategy | What it does |
| --- | --- |
| Self-consumption | Keeps grid power at 0 W by charging from PV surplus and discharging into the house load (PID control) |
| Charge PV | Self-consumption without discharging: charges from PV surplus only |
| Zero import | Self-consumption without charging: discharges to keep grid import at 0 W |
| Standby / peak shave | Batteries idle (no relay clicks); with peak shaving on they still act above the grid limits |
| Charge | Charges from the grid until a goal, then hands over |
| Sell | Discharges to the grid until a goal, then hands over |
| Charge Deadline | Charges to a target before a deadline, in the cheapest quarter-hours |
| Timed | A different strategy per time period (A to E) |
| Dynamic | A different strategy for cheap, expensive and normal price periods |
| Helios | Carries out the decision of the HELIOS optimizer (pyscript, optional) |
| Full stop | Every battery on stop, 0 W; the relay opens, so no standby draw |

**EV stop trigger.** Put the entity id of an "EV is charging" sensor or boolean in `input_text.house_battery_strategy_ev_sensor_entity_id`. While it is `on`, HBC+ runs the strategy in `input_select.house_battery_strategy_ev_stop_trigger_strategy` (*Full stop* or *Standby / peak shave*), so the batteries do not discharge into the car.

### Self-consumption and PID tuning

Self-consumption is the PID controller of HBC+, and most other strategies use it to do the actual work. Each tick it takes the error between grid power and the target (0 W by default), ignores errors under 15 W, and computes a battery power from three terms:

- **P (Kp)** reacts to the error now;
- **I (Ki)** removes the error that remains over time;
- **D (Kd)** damps fast changes.

*Load distribution* then spreads that power over the batteries in priority order, each up to its own maximum. Near full, charging is limited to 1500 W from 95 % and 1000 W from 99 %.

The easiest way to tune is a preset in `input_select.house_battery_control_pid_presets`:

| Preset | Kp | Ki | Kd | Input smoothing | Output smoothing | When |
| --- | --- | --- | --- | --- | --- | --- |
| Very safe | 0.1 | 0.1 | 0 | 0 % | 10 % | A system that oscillates with every other preset |
| Safe | 0.3 | 0.3 | 0.1 | 20 % | 0 % | Good starting point for most |
| Regular | 0.3 | 0.4 | 0.8 | 50 % | 10 % | Faster response; needs a stable meter |
| Custom | — | — | — | — | — | Your own values in the PID helpers |

Start with *Safe*. Grid power that swings back and forth around 0 W means the control is too sharp: go one preset down, or lower Kp and Ki. A slow return to 0 W after a load step means it is too gentle: go one preset up. Change one thing at a time and watch for a few minutes. The *Battery Oscillation Guard* stops the batteries if they start to oscillate.

Other settings on the Self-consumption view:

- **Hysteresis** (`input_number.house_battery_control_hysteresis_in_w`, 0–200 W): the PID output must pass this before the batteries switch between charging and discharging.
- **Error and output smoothing** (`…_error_signal_dampening`, `…_pid_output_dampening`, 0–90 %): moving averages on the input and output; more smoothing is calmer but slower.

### Charge and Sell

**Charge** charges from the grid until the goal in `input_select.house_battery_strategy_charge_goal` is reached:

| Goal | Reached when |
| --- | --- |
| batteries are full | Every battery is at its maximum SoC |
| state of charge | The average SoC reaches `input_number.house_battery_strategy_charge_target_soc` |
| energy reserve | Usable energy reaches `input_number.house_battery_strategy_charge_target_energy` |
| solar forecast | Usable energy reaches the maximum minus today's expected PV surplus (the forecast minus `input_number.house_battery_solar_reserved_for_house`) |

**Sell** discharges to the grid until `input_select.house_battery_strategy_sell_goal` is reached: *batteries are empty*, *state of charge* (`…_sell_target_soc`) or *energy reserve* (`…_sell_target_energy`).

When the goal is reached, the strategy in *Then use* runs (`…_charge_goal_reached` / `…_sell_goal_reached`, default *Charge PV*).

**Power.** Without a grid limit, every battery charges or discharges at its maximum. With import (Charge) or export (Sell) peak shaving on, HBC+ regulates to that grid limit instead (see *Advanced settings*). On *Enforce* only the active battery per shared phase runs, within the phase's fuse room.

**Solar forecast.** For the *solar forecast* goal, put the entity ids of your forecast sensors (kWh today and kWh tomorrow, for example from Forecast.Solar or Solcast) in `input_text.house_battery_strategy_solar_forecast_entity_id` and `…_solar_forecast_tomorrow_entity_id`. Set `input_number.house_battery_solar_reserved_for_house` to what the house uses from PV on a typical day.

### Charge Deadline

Charges to a target before a deadline (`input_datetime.house_battery_deadline_start` / `_end`). The goal is in `input_select.house_battery_deadline_goal`: *batteries are full*, *state of charge* or *energy reserve*. It prefers the cheapest quarter-hours from the Dynamic price list, and paces the power by price (`input_number.house_battery_deadline_price_ratio`: how much harder the cheapest quarter charges than the most expensive one it uses). It also counts on expected PV when `input_boolean.house_battery_deadline_reserve_pv` is on, and keeps the target until the deadline when `…_hold_after_target` is on. After the deadline the strategy in *Then use* (`input_select.house_battery_deadline_reached`) runs. The plan is recomputed every tick from the remaining energy and time. It needs a working price source (see *Dynamic*).

### Timed

Runs a different strategy per time period. Period A is always on; B to E are switched on one after another (`input_boolean.house_battery_strategy_timed_has_period_b` … `_e`). Each period has a start, an end (`input_datetime.house_battery_strategy_timed_period_a1` / `_a2` …) and a strategy (`input_select.house_battery_strategy_timed_strat_a` …). The first enabled period that contains the current time wins; a period whose end is before its start runs past midnight. Outside all periods the baseline strategy (`…_timed_strat_0`) runs. The active period is shown in `input_text.house_battery_strategy_timed_period_selected`.

### Dynamic

Picks a strategy from the energy prices of today and tomorrow.

**Setup.**

1. Install the [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) macro (HACS).
2. Install a price integration and choose it in **Tariff data source** (`input_select.house_battery_strategy_dynamic_data_source`).
3. If you have more than one price integration, pin the sensor in `input_text.house_battery_strategy_dynamic_price_sensor` (see R4).
4. Check the *Price intervals* chart on the Timed/Dynamic view.

**How it decides.** Each day, HBC+ pairs the cheapest and the most expensive intervals, working inward from the extremes. A pair only counts when its price difference is at least **Minimum spread** (`input_number.house_battery_strategy_dynamic_threshold_delta`, in cents). Set that to cover your round-trip losses. **Cheapest hours** and **Expensive hours** cap the number of marked hours per day (0 = no cap). The current interval then decides the strategy:

| Interval | Strategy (helper) | Choices |
| --- | --- | --- |
| Cheap | `…_dynamic_cheapest` | Charge, Charge PV, Charge Deadline, Standby / peak shave |
| Expensive | `…_dynamic_expensive` | Self-consumption, Sell, Zero import, Standby / peak shave |
| Normal | `…_dynamic_default` (*Default to*) | Charge PV, Self-consumption, Zero import, Standby / peak shave, Full stop |

Prices are refreshed at midnight, at 13:15 and 15:00, after a change of source, and until tomorrow's prices are in. If the source fails, Dynamic keeps the last valid prices or falls back to *Default to* (see R3). Other flows can fetch the same prices through the link call (see *Shared price fetch*).

### Advanced settings

- **Battery priority** (`input_select.house_battery_control_priority_change_interval`): Self-consumption uses the batteries in priority order, starting with `input_number.house_battery_control_prioritize_battery`. The priority moves to the next battery every 30 minutes (*Auto balance*), daily at 02:00 (*Daily*), on Sunday at 02:00 (*Weekly*), or not at all (*Never*). Except with *Auto balance*, discharging runs in the reverse order, so the battery that charges first is the last to discharge.
- **Stop after idle** (`input_number.house_battery_control_idle_time`, 0–60 min): a battery that is not needed keeps 1 W (relay closed) for this long before it gets *stop*. This saves relay clicks when the load goes up and down.
- **Peak shaving** (`input_boolean.house_battery_control_has_power_limit_import` / `_export` with `input_number.house_battery_control_power_limit_import` / `_export`): the batteries keep grid import or export below the limit, for example for a capacity tariff. Charge and Sell regulate to these limits instead of running at full power.
- **Cutoff capacities** (`input_number.marstek_mN_charging_cutoff_capacity` 80–100 %, `…_discharging_cutoff_capacity` 11–80 %): the SoC limits written to each Marstek. HBC+ treats a battery at its limit as full or empty.

## Design background and decisions

### Why a phase guard is needed

Without the phase guard, the controller has no notion of phases. That only worked because M1, M2 and M3 each sat on their own phase. *Max power solution* (Charge, Sell and HELIOS Charge/Sell) puts every battery at its max, and *Load distribution* (Self-consumption) fills the batteries in priority order, each up to its own max. With two Marsteks on L1 that puts 2 × 2500 = 5000 W on that phase, well above a 16 A fuse (3680 W).

On top of that, the planner ceiling would be the sum of all batteries (6 × 2500 = 15000 W) instead of what can really flow per phase (3 × 2500 = 7500 W), so Charge Deadline would book only half the cheap quarters it needs. And the heartbeat fallback would put every battery in firmware anti-feed during an outage, after which two batteries on one phase could each push 2500 W.

### Edge cases

| Situation | Behaviour |
| --- | --- |
| HBC+ stopped (heartbeat stale) | Per shared phase only the battery with the lowest M-number goes to firmware anti-feed. Its partner stays RS485 *enable* + forcible *stop*, so it does nothing, even when Node-RED or HA is down. |
| Active battery RS485 off, offline or at its SoC limit | The partner takes over at once (no dwell), after break-before-make. |
| Active battery unreachable while it was running | The partner stays blocked, because the old battery may still be running its last command. The phase idles and an alert is raised. |
| Big load switches on while the phase charges at full power | The fuse is briefly above 16 A until the next tick plus the Marstek's response (a few seconds). Fuses tolerate this; the margin covers measurement error, not big steps. If it lasts 10 s the alarm fires. |
| Both batteries on a phase full or empty | The phase idles; nothing changes for the other phases. |
| A strategy returns two active batteries on a phase | The phase guard corrects it and logs it (rule 6). |
| Someone changes a battery in the Marstek app | The read-back differs from the setpoint; *Set Batteries* rewrites it; the HA alarm catches an overload within 10 s. |
| Guard mode *Off* | No phase rules; only safe with one battery per phase. |

### Design decisions

- **Limits:** a grid fuse and a battery circuit per phase, each the same for L1–L3 (defaults 16 A, 3680 W). The grid room follows the house load on that phase; the battery circuit only counts the batteries.
- **One battery per phase is the default.** *Shared headroom* (both at once within the fuse room) is an option in the settings.
- **Extension with three Marsteks (M4–M6).** Default phase map M1/M4 L1, M2/M5 L2, M3/M6 L3, changeable per battery.
- **Safety over speed.** Handover is break-before-make, and a battery without a fresh read-back counts as busy.
- **Fail-open.** Every new step falls back to control without phase rules on an error; the HA alarm works independently of Node-RED.
- **Signs:** battery power is positive while charging, P1 phase power is positive on import.
- **Monitor first.** The phase guard can run with one battery per phase; then nothing changes and you test the plumbing for free, before a second battery joins a phase.

## Improvements in HBC+ v1.0

Besides the phase guard, HBC+ v1.0 contains the changes below. Eight fix bugs, four make the system more robust, four make the control loop faster or write less to Modbus, and five are features. All of it runs in practice on a three-battery setup (two over RS485, one over Modbus TCP).

| # | Change | Where | Type |
| --- | --- | --- | --- |
| B1 | No `initial: 0` on the five total helpers | `hbc_control.yaml` | Bug fix |
| B2 | Battery power template reads the real entity id | `hbc_control.yaml` | Bug fix |
| B3 | Dynamic price cache tied to the data source | Dynamic – *Cache check* | Bug fix |
| B4 | Dynamic cache refetches until tomorrow is in | Dynamic – *Cache check* | Bug fix |
| B5 | "Now" bar in the price chart based on start/end | Dashboard | Bug fix |
| B6 | Price chart redraws on a source change | Dashboard + template sensor | Bug fix |
| B7 | Debug board shows the trace again | Start – *Set Batteries* | Bug fix |
| B8 | Dynamic *User input* listens to the sub-strategy choices | Dynamic – *User input* | Bug fix |
| R1 | *Batteries (totals)* never sends NaN to HA | Start – *Batteries (totals)* | Robustness |
| R2 | One consistent HA server node in every file | All flows | Robustness |
| R3 | Price fetch failure: last valid prices kept, baseline fallback, alert | Dynamic + `hbc_control.yaml` + dashboard | Robustness |
| R4 | Price sensor can be pinned | Dynamic – *Data source settings* + helper | Robustness |
| P1 | *Read HA states (fast)*: one node instead of ~43 reads | Start | Performance |
| P2 | *PID step*: 13 nodes in one, cache for PID settings | Self-consumption | Performance |
| P3 | *Pick period*: fast path for Timed with settings cache | Timed | Performance |
| P4 | Fewer Modbus writes, in order per battery | Start – *Set Batteries* | Performance |
| F1 | Feed-forward start for regulated charging | Charge – *Regulated power* | Feature |
| F2 | Grid Clock as Dynamic data source | Dynamic + selector | Feature |
| F3 | Charge Deadline strategy | Own tab + package | Feature |
| F4 | Control-loop heartbeat with fallback in HA | Start + package | Feature |
| F5 | Recorder exclusions for busy entities | Packages | Maintenance |
| E1–E4 | Strategy arbiter, Battery Oscillation Guard, Modbus TCP battery, P1 alias | Own tabs and packages | Extension |

### Bug fixes

**B1 — Total helpers reset to 0 after an HA restart.**

- *Problem:* the five total helpers (`house_battery_total_available_energy`, `_max_available_energy`, `_battery_power`, `_max_charge_power`, `_max_discharge_power`) had `initial: 0`. HA applies `initial` again on every restart. The flow writes these values through an *on change* filter, so static values such as the max energy were never rewritten and stayed at 0. Everything that divides by them broke; *Required average power to deadline*, for example, showed 0 W.
- *Fix:* `initial:` was removed from those five helpers, with a comment why. `house_target_grid_consumption_in_w` keeps its `initial: 0`.

**B2 — Battery power template read an entity that does not exist.**

- *Problem:* a template read `sensor.house_total_battery_power_in_w`, but the entity id comes from the sensor's `name:` (*House total battery power*) and is therefore `sensor.house_total_battery_power`. The `unique_id` does not set the entity id, so the template always read `unknown`.
- *Fix:* the template tries both ids and uses the first one with a value.

**B3 — Old prices stayed in use after a source change.**

- *Problem:* *Cache check* in Dynamic treated any cached price list as valid, whatever its source. After changing *Tariff data source*, the old source's prices were used until the next scheduled clear (00:01, 13:15 or 15:00), while the dashboard already showed the new source.
- *Fix:* *Cache data source* stores `data_source` with the cached data; *Cache check* compares it with `msg.dynamic.data_source` and drops the cache when they differ.

**B4 — No prices for tomorrow until 15:01.**

- *Problem:* a list fetched at 13:16, before day-ahead prices were published, was reused until the 15:01 or 00:01 clear. The Timed and Dynamic views then showed no prices for tomorrow although the source already had them.
- *Fix:* after 13:00, *Cache check* only counts a cache hit if `data_all.start + data_all.hours` reaches past midnight. Otherwise it refetches on every run until tomorrow is in. The node status then shows *Waiting for tomorrow (source)*.

**B5 — The "now" bar stuck on an old interval.**

- *Problem:* the price chart coloured the current interval from the stored `is_now` flag, which is only as fresh as the last sensor update.
- *Fix:* the chart's `data_generator` compares each interval's `start` and `end` with `Date.now()` when drawing; the marker follows the clock.

**B6 — The price chart did not redraw on a source change.**

- *Problem:* with `update_interval` set, apexcharts-card stops redrawing on state changes. A new source's prices only appeared after a browser refresh.
- *Fix:* `update_interval` is removed from the *Price intervals* card, and the trigger sensor `update_energy_prices` has an attribute `updated: "{{ now().isoformat() }}"` that changes every time. The card then redraws on a source change and on every 15-minute Dynamic run; the "now" bar moves along. The sensor is excluded from the recorder (F5), so this adds no database rows.

**B7 — The debug board showed a setpoint instead of the trace.**

- *Problem:* the awaited-write path forwards the last write message to the debug board. *Show on debug board* treats `msg.payload.data` as an override for its event data, so HA received the last setpoint (for example `{value: 1733}`) instead of the trace and log.
- *Fix:* the write messages carry the cycle's `strategy.trace` and `log`, and leftover `payload.data` is removed before the board update.

**B8 — Changing a Dynamic sub-strategy took up to 15 minutes.**

- *Problem:* the Dynamic trigger *User input* did not listen to the three sub-strategy choices. A change to *Default to*, *Cheap periods* or *Expensive periods* only took effect at the next 15-minute run.
- *Fix:* `input_select.house_battery_strategy_dynamic_default`, `_cheapest` and `_expensive` are now in that trigger's entity list; a change takes effect within a few seconds (prices come from the cache).

### Robustness

**R1 — One unavailable battery value broke the totals.**

- *Problem:* *Batteries (totals)* summed `Number(battery.x)` for every battery. When one entity was `unavailable` or `unknown` (reconnect, Modbus hiccup, HA restart), the total became NaN. That reached HA as `null` and raised `HomeAssistantError: expected float at 'value'` every cycle; strategies comparing against these totals got NaN too, and comparisons with NaN are always false.
- *Fix:* a guard per battery and per value. A valid number is used and remembered; a missing value uses the last good one for up to 5 minutes; after that the battery counts as 0, because an offline battery delivers nothing. `msg.batteries` itself is unchanged. The node status is green when all is OK, yellow while a value is held and red once a battery counts as 0. With valid data this gives exactly the same totals as before (14 test cases).

**R2 — The HA server node differed per file.**

- *Problem:* every flow file carries its own copy of server node `176d29a.6f648d6`, and the last file imported overwrites the live node. Importing one strategy file could therefore switch heartbeat and connection delay off.
- *Fix:* every HBC+ file carries the same server node (*HA System*) with *Expose to global context* on (needed for P1), heartbeat (30 s) and connection delay on.

**R3 — A failed price fetch went unnoticed and kept the last strategy.**

- *Problem:* when the tariff source delivered no prices, *Cache data source* threw away the cached list, *Determine dynamic strategy* returned without a new decision, and Dynamic kept running whatever it last chose, also *Charge* from the grid. Nothing told you.
- *Fix:* three layers.
  - *Last valid prices kept:* when a fetch fails and the cached list is from the same source and still covers the current interval, *Cache data source* passes that list on (`dynamic.stale = true`) and keeps it; the next run tries the source again.
  - *Fallback:* with no valid prices at all, Dynamic runs its baseline strategy (*Default to*) instead of the last one.
  - *Alert:* `sensor.hbc_energy_prices_data` has a `status` attribute (`ok`, `stale`, `no_data`). `binary_sensor.hbc_price_data_missing` turns on with `no_data`; the dashboard shows a warning, and after 30 minutes the automation *HBC+: alert when the tariff source delivers no prices* creates a persistent notification and calls `notify.notify`. The notification is dismissed when prices are back.

**R4 — The price sensor could be guessed wrong.**

- *Problem:* for EasyEnergy/EnergyZero, ENTSO-E, GE-Spot, Tibber and Nordpool (custom), Amber, Octopus, PVPC and Omie, *Data source settings* names no sensor, so the Cheapest Energy Hours macro auto-detects it. With two price integrations installed it can pick the wrong one.
- *Fix:* the optional helper `input_text.house_battery_strategy_dynamic_price_sensor` (set it in *Settings* → *Devices & services* → *Helpers*) pins the sensor, e.g. `sensor.nordpool_kwh_nl_eur_3_10_021`. It also overrides the built-in sensor for Nordpool and Tibber (core) and Frank Energie. Sources that pass their own list (Zonneplan, Grid Clock) ignore it. The status of *Data source settings* shows which sensor is used, *auto-detected*, or *not found* when the entity does not exist.

### Performance

On a busy Node-RED every extra node hop goes through the message queue again, and the Start flow regularly exceeded its 1 s link-call timeout. Every change below keeps the original logic and output, and falls back to the original nodes when the fast path cannot run.

**P1 — Read HA states (fast).** Was: about 43 *current state* nodes in a row (10 per battery + 13 settings), then *Mapping*. Now: one function reads everything from the HA states in global context and builds `msg.batteries` exactly as *Mapping* did. When the global states are missing (option off, HA not connected yet), output 2 sends the message through the original chain and the node shows yellow *fallback to old reads (reason) xN*. Requires *Expose to global context* on (R2).

**P2 — PID step in Self-consumption.** Was: 13 nodes in a row plus 7 reads of PID settings. Now: one *PID step* function; seven of the original bodies are copied verbatim, *Calculate corrections* differs only by the feed-forward block (F1). A template reads Kp, Ki, Kd, idle time, hysteresis and both damping values into flow context every 60 s, at start and whenever a helper changes; if the cache is older than 10 minutes, *PID step* reads straight from HA. Also: five *Max 1 per 10 s* delays before the writes to the PID helpers, and *Trace* is a function node instead of JSONata.

**P3 — Pick period in Timed.** Was: 20 reads, 5 config functions, 5 period switches and ~15 change and switch nodes. Now: one *Pick period* function with the same logic (periods A to E, the first matching window wins, a window may run past midnight, start = end is an empty period). It uses HA's time, so Node-RED's own timezone does not matter. *Timed settings cache* renders all period settings every 30 s and on every change; if the snapshot is older than 5 minutes, the old chain runs instead.

**P4 — Fewer Modbus writes.** The write design stays (awaited writes, *Write limiter*, 30 s failsafe, *Collect completions*, *Write latency*). On top of it: the **mode** is written only when it changes, when the read-back differs for more than 20 s, or as a 60 s keep-alive (before, it was written every tick); for **power** only the register of the current mode is written, and nothing in `stop`; *Next write* runs the writes one by one per battery, power first, then mode. Tested with 13 simulated scenarios.

### Features

**F1 — Feed-forward start for regulated charging.** At the start of regulated charging, the PID reached the import limit only through the integrator, which took a minute or more with a small Ki. Now the power jumps straight to current battery power + (import limit − grid power) − 150 W, capped at the max charge power. That value is held for 10 s, then the PID takes over without a step (the integrator is pre-loaded with it). A pause of more than 30 s counts as a new session. Turn it off with `FF_ENABLED = false` in *Regulated power*.

**F2 — Grid Clock as Dynamic data source.** *Tariff data source* has Grid Clock options that read `sensor.grid_clock_<zone>_prices` from the Grid Clock integration (gridclock.eu); its `prices` attribute holds `startsAt` and `total` in ct/kWh. A `template_prefix` converts the list to `{start, price}` in EUR/kWh for the Cheapest Energy Hours macro. An HA automation in `hbc_config.yaml` refreshes the prices as soon as the Grid Clock default zone changes. Requires the Grid Clock integration.

**F3 — Charge Deadline strategy.** Charges to a target SoC or target energy before a deadline, preferring the cheapest windows from the Dynamic price list and topping up from the grid when PV falls short. It consists of the tab *HBC+ Strategy Charge Deadline*, the package `hbc_deadline_charge.yaml` and a dashboard section (goal, estimate, planned windows, follow-up strategy). *Charge Deadline* can also be chosen as main strategy, in the Timed list, as Dynamic *cheapest* and as the follow-up after *charge/sell goal reached*.

**F4 — Heartbeat with fallback in HA.** *HBC+ heartbeat (max every 60 s)* in the Start flow publishes to MQTT `hbc/heartbeat` (retained), which feeds `sensor.hbc_last_run`. When that sensor is older than 5 minutes while the master mode is *Full control*, an HA automation hands every Marstek back to its firmware (RS485 off, anti-feed) and sends a notification. When the loop runs again, the master switch turns RS485 back on. Without this, batteries keep their last setpoint when Node-RED stops. The fallback is phase-aware: on *Enforce*, only the battery with the lowest M-number on a shared phase goes back to firmware; its partner is first set to RS485 *enable* + forcible *stop*, so two batteries in firmware anti-feed can never overload one phase. Batteries alone on their phase or on *Own circuit*, and all batteries on *Off* / *Monitor*, are handed back as before. The automation also checks again 5 minutes after an HA restart, writes to the logbook and notifies through `notify.notify` (set your own notify action in `packages/hbc_heartbeat.yaml`).

**F5 — Recorder exclusions.** `sensor.deadline_charged_at`, `sensor.deadline_window`, `sensor.deadline_cheap_blocks`, `sensor.deadline_goal_progress`, `sensor.hbc_energy_prices_data` and `input_number.house_battery_deadline_*_power` are not recorded: they re-render every minute or duplicate other statistics. `sensor.hbc_energy_prices_data` saves the most, because every 15-minute update would otherwise store the whole price list again.

### Extensions

| # | Part | What it does |
| --- | --- | --- |
| E1 | *Strategy arbiter* + `hbc_strategy_arbiter.yaml` | Only writer of `input_select.house_battery_strategy`; arbitrates between your own choice, flows of your own (such as a PV limiter) and the Oscillation Guard (see *Functionality*) |
| E2 | *Battery Oscillation Guard* | Detects charge/discharge waves and holds *Full stop* through the arbiter; thresholds in the tab's environment variables, notification through the *Notify phone* node |
| E3 | Marstek over Modbus TCP | A battery over Modbus TCP works with HBC+ unchanged, as long as its entities follow the `marstek_mN_*` pattern |
| E4 | P1 alias disabled in `hbc_config.yaml` | Not needed when your meter already provides `sensor.p1_meter_power` (e.g. HomeWizard); enable it for another meter |

### Known open points

1. **`value_conversion` only reaches *Convert price*.** The macro ranks prices in the source's own unit; Zonneplan and Grid Clock therefore convert inside `template_prefix`.

## Requirements

HBC+ v1.0 is a complete, standalone installation: every package, flow and the dashboard is in this repository. You only need the components below.

| Component | Requirement | Why |
| --- | --- | --- |
| Home Assistant | Packages enabled (`homeassistant: packages: !include_dir_named packages`) | All HBC+ helpers come as packages |
| Node-RED | Add-on or standalone, with `node-red-contrib-home-assistant-websocket` 0.80 or newer | Runs the control loop |
| Node-RED palette | `node-red-contrib-time-range-switch`, `node-red-node-smooth` | Used by HBC+ tabs |
| MQTT | MQTT integration in HA with a broker | Phase monitor status (`hbc/phase/*`) and the HBC+ heartbeat (`hbc/heartbeat`) |
| Batteries | Marstek Venus E, up to 6, entities named `marstek_mN_*` (RS485 or Modbus TCP) | HBC+ reads SoC, power, limits and RS485 mode per battery |
| Grid meter | Total power `sensor.p1_meter_power` **and** per-phase power `sensor.p1_meter_power_phase_1` … `_3`, positive on import | The fuse room is computed per phase from P1 |
| Dashboard | `custom:apexcharts-card` (HACS) | Price and history charts |
| Prices | [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) macro (HACS) and a price integration | Needed for Dynamic and Charge Deadline |
| Optional | HELIOS pyscript optimizer; Grid Clock integration | HELIOS strategy; Grid Clock as Dynamic price source |

Sign conventions must match: `sensor.marstek_mN_battery_power` is positive while **charging**, `sensor.p1_meter_power_phase_N` is positive on **import**. If your meter uses the opposite sign, fix it with a template sensor before installing, or the fuse room is computed wrongly.

Both limits default to 16 A per phase (3680 W): the main (grid) fuse and the battery circuit, the group the batteries of one phase share. Set your own values after installation (for example a 3 × 32 A connection ≈ 7360 W with the batteries on a 16 A group per phase ≈ 3680 W).

## Installation

Download HBC+ from [github.com/CodeRubbere/HASS-HBC-Plus](https://github.com/CodeRubbere/HASS-HBC-Plus) (*Code* → *Download ZIP*, or clone it). Installation takes about 30 minutes and changes nothing about how the batteries behave until you switch the guard to *Enforce*.

### What is in the repository

**Root**

| File | Contents |
| --- | --- |
| `README.md` | Short introduction, quick start and credits |
| `LICENSE` | GPL-3.0 licence |
| `.gitattributes` | Git setting: normalises line endings of text files |
| `.gitignore` | Keeps macOS and editor files out of the repository |

**packages/** — Home Assistant packages; copy all six into your HA `packages/` folder.

| File | Contents |
| --- | --- |
| `hbc_control.yaml` | Core helpers and sensors: battery count, totals, PID settings, strategy selection, Timed and Dynamic settings, price-data alert |
| `hbc_config.yaml` | Your installation-specific config: P1 alias (disabled) and the automation that refreshes prices when the Grid Clock zone changes |
| `hbc_deadline_charge.yaml` | Charge Deadline helpers and sensors: target, deadline, plan and cheap windows |
| `hbc_strategy_arbiter.yaml` | `input_text.hbc_strategy_arbiter`: the Strategy arbiter state, kept across restarts |
| `hbc_heartbeat.yaml` | Phase-aware HA fallback when HBC+ stops: `sensor.hbc_last_run`, `binary_sensor.hbc_heartbeat_stale` and the automation that hands the batteries back to their firmware |
| `hbc_phase_guard.yaml` | Phase guard: settings, phase map M1–M6, per-phase power and fuse headroom, overload alarm, MQTT status sensors and the defaults script |

**dashboards/**

| File | Contents |
| --- | --- |
| `hbc_plus.yaml` | The *Home Battery Control Plus* dashboard with the views Home, Self-consumption, Charge/Sell, Timed/Dynamic, Phases, Problem solver and Advanced settings |

**node-red/** — import `hbc-plus-all-flows.json` (everything at once) or the separate files.

| File | Tab | What it does |
| --- | --- | --- |
| `hbc-plus-all-flows.json` | All 15 below | One import file with every tab and the HA server node |
| `00 master-switch-flow (HBC+).json` | HBC+ Home Battery Master Switch v1.0 | Decides who controls the Marsteks (RS485, work mode); hands only one battery per shared phase back to the firmware |
| `00 presets-switch-flow (HBC+).json` | HBC+ Home Battery PID presets v1.0 | Applies a PID preset (Very safe, Safe, Regular) to the PID helpers |
| `01 start-flow (HBC+).json` | HBC+ Home Battery Start v1.0 | The control loop: reads the batteries, sums the totals, runs phase planner, strategy and phase guard, writes the setpoints and publishes the heartbeat |
| `02 strategy-charge (HBC+).json` | HBC+ Strategy Charge v1.0 | Charges from the grid up to a target (full, SoC, energy or solar forecast) |
| `02 strategy-charge-deadline (HBC+).json` | HBC+ Strategy Charge Deadline v1.0 | Charges to a target before a deadline, in the cheapest quarter-hours |
| `02 strategy-dynamic (HBC+).json` | HBC+ Strategy Dynamic v1.0 | Picks a strategy per price period (cheap, expensive, normal); contains the shared price fetch |
| `02 strategy-full-stop (HBC+).json` | HBC+ Strategy Full stop v1.0 | Sets all batteries to stop |
| `02 strategy-helios (HBC+).json` | HBC+ Strategy Helios v1.0 | Carries out the HELIOS optimizer's decision |
| `02 strategy-partials (HBC+).json` | HBC+ Strategy Partials v1.0 | Charge PV, Zero import and Standby / peak shave |
| `02 strategy-self-consumption (HBC+).json` | HBC+ Strategy Self-consumption v1.0 | PID controller that keeps grid power at the target; spreads the power over the batteries |
| `02 strategy-sell (HBC+).json` | HBC+ Strategy Sell v1.0 | Discharges to the grid down to a target |
| `02 strategy-timed (HBC+).json` | HBC+ Strategy Timed v1.0 | Runs a strategy per time slot (A to E) |
| `03 battery-oscillation-guard (HBC+).json` | HBC+ Battery Oscillation Guard v1.0 | Detects charge/discharge waves and holds Full stop through the arbiter |
| `03 phase-monitor (HBC+).json` | HBC+ Phase monitor v1.0 | Read-only: publishes the phase status over MQTT for the dashboard |
| `03 strategy-arbiter (HBC+).json` | HBC+ Strategy arbiter v1.0 | Sole writer of the strategy selection; chooses between your own choice, flows of your own and the Oscillation Guard |
| `README.md` | — | Overview of the Node-RED files and installation |

**docs/**

| File | Contents |
| --- | --- |
| `user-guide.en.md` | This guide in English |
| `gebruikershandleiding.nl.md` | This guide in Dutch |

### Step 1 — Back up

1. Node-RED: menu → *Export* → *All flows* → *Download*.
2. Home Assistant: make a full backup, or at least copy your `packages/` folder and dashboard YAML.
3. If you run an earlier version and changed one of its tabs in Node-RED since you last exported it, export that tab first. The HBC+ files replace tabs with the same node ids.

### Step 2 — Home Assistant packages

1. Copy all six files from `packages/` into your HA `packages/` folder (replace older copies). Coming from an earlier version? Delete the old files that HBC+ v1.0 renamed: `house_battery_control.yaml` (now `hbc_control.yaml`), `house_battery_control_config.yaml` (now `hbc_config.yaml`), `house_battery_deadline_charge.yaml` (now `hbc_deadline_charge.yaml`) and `nodered_heartbeat.yaml` (now `hbc_heartbeat.yaml`). With both versions present HA sees duplicate ids and refuses them.
2. Check that your P1 sensor names match (`sensor.p1_meter_power`, `sensor.p1_meter_power_phase_1` … `_3`). If not, add template aliases in `hbc_config.yaml`.
3. *Developer tools* → *Check configuration*, then restart Home Assistant.
4. Run the script **HBC+ phase guard: apply defaults** once (*Settings* → *Automations & scenes* → *Scripts*). New helpers without `initial:` start at their minimum or first option; the script sets guard mode *Monitor*, *One per phase*, *SoC balance*, 3680 W grid fuse, 3680 W battery circuit, 200 W margin, 5 % swap delta, 15 min dwell, and the phase map M1/M4 = L1, M2/M5 = L2, M3/M6 = L3. HA restores the values after every later restart.

### Step 3 — Node-RED flows

1. Open the Home Assistant server config node (*HA System*, id `176d29a.6f648d6`) and confirm the server address and access token are right for your setup after import.
2. Menu → *Import* → select `hbc-plus-all-flows.json` → choose **Replace** for existing nodes. Tabs with the same node ids (from an earlier installation) are replaced, not duplicated.
3. Check the server node has **Expose to global context** on. *Read HA states (fast)*, the HBC+ planner and guard, and *Prepare request* in Dynamic all need it. The HBC+ files all carry the correct copy; an older Helios export carried a copy with this option off.
4. *Deploy* → *Modified flows*, at a quiet moment. HBC+ rewrites battery mode and power once after a deploy; that is normal.
5. Set your own notify action in the *Notify phone* node of *HBC+ Battery Oscillation Guard v1.0*; the default is `notify.notify`. Step 6 lists all three places that send notifications.

**Flows of your own** can request a strategy through the *Strategy arbiter*: a link call to *Strategy request* with `msg.arbiter = {requester, action: 'hold' | 'release', strategy, reason}`. Give the requester a priority in the *Arbitrate* node; the Battery Oscillation Guard has 100, any other requester name gets 50, and on equal priority the hold that came first wins. A manual choice always wins and becomes the new base.

### Step 4 — Dashboard

1. *Settings* → *Dashboards* → *Add dashboard* → *New dashboard from scratch*, name it *Home Battery Control Plus*.
2. Open it → ⋮ → *Edit dashboard* → ⋮ → *Raw configuration editor*, paste the contents of `dashboards/hbc_plus.yaml`, save.
3. Open the **Phases** view and check that every card shows values.

### Step 5 — Set your phase map and fuse

On the Phases view, under *Which phase is each battery on?*, set the phase of every battery to the phase it is physically connected to. Set *Grid fuse per phase* to your main fuse and *Battery circuit per phase* to the group the batteries of one phase share (A × 230 V; 16 A → 3680 W, the default for both). No separate battery group? Set both to the main fuse. Then continue with commissioning below.

### Step 6 — First start

1. **Onboarding.** The top of the *Home Battery Control Plus* view has an onboarding checklist. Set **Number of batteries** (`input_number.house_battery_count`, 1–6). Check that *Grid Power Sensor* shows *Configured* and *Node-RED* shows *Configured and script deployed* (the Start flow turns `input_boolean.house_battery_control_has_node_red` on). Then hide the checklist with *Finish onboarding*.
2. **Battery entities.** Every battery needs its `marstek_mN_*` entities, from M1 up to the number you set. Check on the Phases view that each battery shows SoC and power.
3. **PID preset.** On the Self-consumption view, choose *Safe* (see *Self-consumption and PID tuning*).
4. **Strategy.** Choose a first strategy; *Self-consumption* or *Charge PV* is a safe start.
5. **Master mode.** Set *Master Battery Mode* to **Full control**. Only now does HBC+ steer the batteries. To hand them back to their own firmware, choose *Marstek control*.
6. **Notifications.** Set your own notify action (e.g. `notify.mobile_app_<phone>`) in the three places that send one; the default is `notify.notify`.

| Where | Sends a notification when |
| --- | --- |
| Node-RED, *HBC+ Battery Oscillation Guard v1.0*, node *Notify phone* | The batteries oscillate and are held on *Full stop* |
| `packages/hbc_heartbeat.yaml`, automation *hand batteries back to firmware when the HBC heartbeat is stale* | The control loop stopped and the batteries went back to their firmware |
| `packages/hbc_control.yaml`, automation *alert when the tariff source delivers no prices* | The tariff source delivered no valid prices for 30 minutes |

### Updating HBC+

A new HBC+ version comes as a new release of [the repository](https://github.com/CodeRubbere/HASS-HBC-Plus). Your settings are kept: they live in the helpers, and Home Assistant restores them after a restart.

1. **Back up** as in Step 1.
2. **Read the release notes** for files that were renamed or removed, and delete those from your HA `packages/` folder (in v1.0: `house_battery_control.yaml`, `house_battery_control_config.yaml`, `house_battery_deadline_charge.yaml` and `nodered_heartbeat.yaml` became `hbc_control.yaml`, `hbc_config.yaml`, `hbc_deadline_charge.yaml` and `hbc_heartbeat.yaml`).
3. **Packages:** copy the new `packages/*.yaml` over the old ones. If you changed a package yourself (the P1 alias in `hbc_config.yaml`, a notify action), carry that change over into the new file. Then *Check configuration* and restart HA.
4. **Flows:** import `node-red/hbc-plus-all-flows.json` with **Replace** and deploy. Changes you made inside HBC+ tabs are overwritten, so set your notify action in *Notify phone* again.
5. **Dashboard:** if the release changed `dashboards/hbc_plus.yaml`, paste it again in the raw configuration editor.
6. **New settings:** a helper that is new in a release starts at its minimum. Set it right after the update; the release notes name it (for example *Battery circuit per phase*). Running *HBC+ phase guard: apply defaults* also sets it, but resets the phase map too.

## Configuration reference

The phase guard entities below come from `packages/hbc_phase_guard.yaml`; their settings are on the Phases view, and the defaults are what *HBC+ phase guard: apply defaults* sets. The other HBC+ entities are listed under *Other HBC+ entities*; the strategy settings are explained in *Strategies and settings*.

### Settings

| Entity | Options / range | Default | What it does |
| --- | --- | --- | --- |
| `input_select.house_battery_phase_guard_mode` | Off · Monitor · Enforce | Monitor | Whether the phase rules act |
| `input_select.house_battery_phase_sharing` | One per phase · Shared headroom | One per phase | One battery per phase, or both within the fuse room |
| `input_select.house_battery_phase_selection` | SoC balance · Fixed order · Rotate daily | SoC balance | How the active battery is chosen |
| `input_number.house_battery_phase_limit_w` | 1000–17250 W | 3680 W | Grid fuse per phase (main fuse): house and batteries together, import and export, same for L1–L3 |
| `input_number.house_battery_phase_circuit_limit_w` | 500–17250 W | 3680 W | Battery circuit per phase: the group the batteries of one phase share; only the batteries count |
| `input_number.house_battery_phase_margin_w` | 0–1000 W | 200 W | Phase limit margin: kept free under both the grid fuse and the battery circuit, for measurement error and load steps |
| `input_number.house_battery_phase_switch_soc_delta` | 1–30 % | 5 % | SoC gap needed to swap the active battery |
| `input_number.house_battery_phase_min_dwell` | 1–120 min | 15 min | Minimum time a battery stays active before a SoC swap |
| `input_select.marstek_m1_phase` … `m6_phase` | L1 · L2 · L3 · Own circuit | M1/M4 L1, M2/M5 L2, M3/M6 L3 | Which phase each battery is on |

The number of batteries still comes from `input_number.house_battery_count` (max 6).

### Sensors

| Entity | Source | What it shows |
| --- | --- | --- |
| `sensor.hbc_phase_l1_active` … `l3` | MQTT `hbc/phase/L1` … `L3` | Active battery (M1, M4 or none); attributes standby, mode, room, setpoint, would, reason, since |
| `sensor.hbc_phase_findings` | MQTT `hbc/phase/summary` | Number of phases where HBC+ would act |
| `sensor.hbc_phase_l1_battery_power` … `l3` | Template | Measured sum of battery power on that phase |
| `sensor.hbc_phase_l1_charge_headroom` … `l3` | Template | Charge room under the grid fuse and the battery circuit (same formula as Node-RED) |
| `sensor.hbc_phase_l1_discharge_headroom` … `l3` | Template | Discharge room under the grid fuse and the battery circuit |
| `sensor.house_battery_installed_max_charge_power` | Template | Plain sum of all batteries' max charge power, for comparison |
| `binary_sensor.hbc_phase_limit_exceeded` | Template | On when grid power on any phase is above the grid fuse for 10 s |
| `binary_sensor.hbc_phase_circuit_limit_exceeded` | Template | On when the batteries on any phase draw more than the battery circuit for 10 s |
| `script.hbc_phase_guard_defaults` | Script | Resets all HBC+ settings and the phase map to the defaults |

The template sensors and the alarm run in Home Assistant only, so they keep working when Node-RED is down. The MQTT status sensors are display-only and excluded from the recorder.

### Other HBC+ entities

| Entity | Package | What it is |
| --- | --- | --- |
| `sensor.hbc_last_run` | `hbc_heartbeat.yaml` | Time of the last HBC+ heartbeat (MQTT `hbc/heartbeat`) |
| `binary_sensor.hbc_heartbeat_stale` | `hbc_heartbeat.yaml` | On when there was no heartbeat for more than 5 minutes; in *Full control* this hands the batteries back to their firmware |
| `sensor.hbc_energy_prices_data` | `hbc_control.yaml` | The current price list for the dashboard; attribute `status` is `ok`, `stale` or `no_data` |
| `binary_sensor.hbc_price_data_missing` | `hbc_control.yaml` | On when a tariff source is chosen but no valid prices are available |
| `input_text.house_battery_strategy_dynamic_price_sensor` | `hbc_control.yaml` | Optional: pins the price sensor for Dynamic (see R4) |
| `input_text.hbc_strategy_arbiter` | `hbc_strategy_arbiter.yaml` | State of the Strategy arbiter, restored after a restart |
| `input_boolean.house_battery_control_has_node_red` | `hbc_control.yaml` | Turned on by the Start flow once it runs; used by the onboarding checklist |
| `sensor.hbc_time` | `hbc_control.yaml` | Local time (HH:MM) for the *Time* badge on the dashboard views |

### Choosing values

- **Grid fuse:** your main fuse per phase in A × 230 V (3 × 16 A → 3680 W, the default; 3 × 25 A → 5750 W; 3 × 32 A → 7360 W). A grid connection has the same fuse on every phase, so one value covers L1–L3.
- **Battery circuit:** the breaker of the group the batteries of one phase share (16 A → 3680 W). Anything else on that group is not measured, so raise the margin if there is. No separate battery group? Use the grid fuse value.
- **Margin:** 200 W covers meter error and small steps; it applies to both limits. Raise it if one of the alarms fires while batteries run at full power.
- **Swap delta and dwell:** lower values balance SoC more tightly but cause more handovers (relay clicks). The defaults give at most one swap per 15 min per phase.
- **Own circuit:** use it for a battery on a dedicated group that does not share the main-fuse phase with a partner. It is never limited by the phase rules.

## Commissioning: from Monitor to Enforce

Run HBC+ in *Monitor* for a few days before any two batteries share a phase. With one battery per phase, Enforce changes nothing either, so you can test the plumbing for free.

1. **Check the measurements.** On the Phases view, *Batteries* per phase must match each battery's own power sensor, and the grid gauge must match your meter. Check the signs: charging shows positive battery power, import shows positive grid power.
2. **Watch Monitor for a few days.** In Node-RED, the status of *HBC+ phase planner* and *HBC+ phase guard* shows `would: …`. With one battery per phase, the active battery must always be that battery and `sensor.hbc_phase_findings` should stay at 0 except when the fuse room binds.
3. **Switch to Enforce** on the Phases view. Nothing should change while each phase has one battery.
4. **Add the second battery on a phase** (for example Marstek M4 on L1): create its `marstek_m4_*` entities, raise `input_number.house_battery_count`, set `input_select.marstek_m4_phase` = L1.
5. **Test, in this order**, while watching the Phases view:
   - [ ] Charge at max power: one battery per phase charges, the partner idles at 1 W, then stops
   - [ ] Sell at max power: the fuller battery discharges
   - [ ] Self-consumption with a 4 kW load on one phase
   - [ ] Charging with a 2 kW load on L1: the cap must drop to about 1480 W
   - [ ] Full stop
   - [ ] RS485 off on the active battery: the partner takes over after break-before-make
   - [ ] Unplug the active battery's network: the partner must stay blocked and the phase idles
6. **After batteries 5 and 6**, check overnight that Charge Deadline books enough cheap slots for the per-phase max power.

Always run the dashboard and the HA alarms while testing: `binary_sensor.hbc_phase_limit_exceeded` and `binary_sensor.hbc_phase_circuit_limit_exceeded` turn red on the Phases view after 10 s above their limit.

## Dashboard

The *Home Battery Control Plus* dashboard has a **Phases** view, which answers three questions at a glance: which battery works on each phase, how close each phase is to its fuse, and why.

| View | What it is for |
| --- | --- |
| Home Battery Control Plus | Onboarding, master mode, strategy choice, battery overview |
| Self-consumption | PID tuning and analysis |
| Charge/Sell | Goals and limits for Charge, Sell and Charge Deadline |
| Timed/Dynamic | Time periods, price source and cheap/expensive periods |
| **Phases** (new) | Phase guard status, per-phase cards, settings and phase map |
| Problem solver (spider icon) | *Flow trace* and *Insights*: the route the last tick took and the explanations of each node; switch on *Insight mode* (off again after 5 min) |
| Advanced settings | Battery life, peak shaving, charge/discharge limits |

On the Home view, warning cards appear only when something needs attention:

- **Onboarding** — the checklist (number of batteries, grid sensor, Node-RED, power limits), until you hide it.
- **No energy prices** — `binary_sensor.hbc_price_data_missing` is on; Dynamic runs its baseline strategy (see R3).
- **Dynamic strategy: Full Stop** — Dynamic is chosen while *Tariff data source* is *None*.

The Phases view, top to bottom:

- **Badges** — *Choose strategy*, *Executing* (the active sub-strategy) and *Time*, the same as on the other views.
- **Alerts** — red cards, visible only while `binary_sensor.hbc_phase_limit_exceeded` (grid fuse) or `binary_sensor.hbc_phase_circuit_limit_exceeded` (battery circuit) is on.
- **Phase guard** — tiles for guard mode, sharing, grid fuse, battery circuit, limit margin, and *Phases where HBC+ would act*.
- **L1 · L2 · L3** — per phase: a gauge of grid power against the fuse, the active battery, measured battery power on the phase, charge room and discharge room, plus the planner's standby battery, setpoint and reason. A table lists every battery on the phase with SoC, power and role: *active · charge*, *active · discharge*, *active · idle*, or *standby*.
- **Settings** — all HBC+ settings, and *Which phase is each battery on?* for M1–M6.

The gauge shows grid power against the grid fuse: import (positive) in light red and export (negative) in light green; orange from ±3200 W, red from ±3680 W. The bands and the ±4000 W range are fixed in the YAML: edit them if your grid fuse differs.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Phases view shows *unknown* for the active battery | MQTT not set up, or Phase monitor tab disabled | Check the MQTT integration; enable *HBC+ Phase monitor v1.0* |
| *Read HA states (fast)* yellow: `fallback to old reads` | *Expose to global context* off on the server node | Turn it on in *HA System*, Deploy |
| Planner status shows nothing or `guard off` | Guard mode is Off | Set Monitor or Enforce |
| Charge room always 0 or far too low | Wrong sign on the P1 phase sensors or battery power | Make import and charging positive (Requirements) |
| Both batteries on a phase run at once in *One per phase* | Guard on Off or Monitor, or the phase map is wrong | Set Enforce; check `input_select.marstek_mN_phase` |
| Partner never takes over | Old battery's read-back stale (break-before-make blocks on purpose) | Restore the old battery's Modbus connection |
| Overload alarm fires briefly when a big load starts | Load step before the next tick | Normal for a few seconds; raise the margin if it lasts 10 s |
| New settings start at their minimum after install | Defaults never applied | Run *HBC+ phase guard: apply defaults* |
| Charge Deadline books too few hours | Guard not on Enforce with 6 batteries, so it counts 15000 W | Set Enforce |
| Link call to *Dynamic Fetch from Data Source* times out | Fetch failed inside the section, or the timeout is shorter than the fetch | Check *Strategy errors* in the Dynamic tab; set the timeout to at least 30 s |
| Dashboard: *No energy prices*, or `binary_sensor.hbc_price_data_missing` on | The tariff source delivers no prices (integration down, sensor renamed, wrong sensor auto-detected) | Check the price integration; set `input_text.house_battery_strategy_dynamic_price_sensor` to the right sensor; the status of *Data source settings* in the Dynamic tab shows which sensor is used |
| Dynamic status yellow: *(last prices)* | The last fetch failed; the previous prices of the same source are still in use | Nothing to do if it clears on the next run; otherwise as above |
| Batteries suddenly run on their own firmware; notification *HBC stopped - batteries on firmware* | The control loop stopped for 5 minutes (Node-RED down, deploy error, lost HA connection), so the heartbeat fallback handed the batteries back | Start or fix Node-RED; once the loop runs again, the Master Switch flow takes over again in *Full control* |
| Onboarding shows *Setup Node-RED* | The Start flow has not run yet | Import and deploy the flows (Step 3); check the *HA System* server node |
| The strategy you choose does not stick, or changes by itself | A hold in the Strategy arbiter (Oscillation Guard or a flow of your own) | Look at `input_text.hbc_strategy_arbiter` and the HA logbook; a manual choice becomes the new base, the hold ends when its requester releases it |

To see what HBC+ decided and why, open the **Problem solver** view (spider icon) and switch on *Insight mode*.

Every tab has a **📖 How this flow works – HBC+ v1.0** comment: open it and read the Info sidebar. The last guard result is in Node-RED global context as `hbcplus_guard_last`; corrections also go to the HBC+ debug board.

## Help and feedback

Questions, bugs and ideas: open an issue in [the repository](https://github.com/CodeRubbere/HASS-HBC-Plus/issues). Mention the HBC+ version, what you expected and what happened instead. If you can, add the status of the Node-RED nodes involved and the HA logbook around that time.

## Related

- [HASS-HBC-Plus on GitHub](https://github.com/CodeRubbere/HASS-HBC-Plus) — the repository.
- [Nederlandse handleiding](gebruikershandleiding.nl.md) — the Dutch version of this guide.
- [node-red/README.md](../node-red/README.md) — per-tab overview of the HBC+ changes.

