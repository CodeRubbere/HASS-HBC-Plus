# Changelog

All notable changes to HBC+ (Home Battery Control Plus). The user guide has the details: *What's new* and
*Updating from …* per version ([English](docs/user-guide.en.md), [Nederlands](docs/gebruikershandleiding.nl.md)).

## [1.3.0] – planned 22 December 2026

Includes everything in 1.2.1 and 1.2.2.

### Added
- **Dutch dashboard** — `dashboards/hbc_plus.nl.yaml`: the same dashboard in Dutch (same views, entities and URL).
  `tools/set-version.py` and `tools/check-versions.py` keep its version numbers in step with `hbc_plus.yaml`.
- **Savings** (F1) — new *Savings* view: what your energy cost with the batteries compared with without them, per day,
  month and year, split into stored PV and charging from the grid. New package `hbc_savings.yaml`.
- **Measured round-trip efficiency** (F2) — `sensor.hbc_round_trip_efficiency` over 7 days and a suggested *Minimum
  spread* you can take over with one button. Optionally Dynamic pairs on what a kWh really earns after losses
  (*Dynamic uses measured efficiency*, off by default).
- **One notification setting** (F3) — every HBC+ notification goes through `script.hbc_notify`. Set *Notify targets*
  once on the *Settings* view (comma-separated; empty = `notify.notify`), with a *Send a test notification*
  button. New package `hbc_notify.yaml`, required.
- **Battery calibration** (F4) — a battery that has not been full for 14 days is charged to 100 % once, in the
  cheapest block after midnight, with Charge Deadline; its charge cutoff goes to 100 % for that night and back
  afterwards. On by default (*Auto*). New package `hbc_calibration.yaml`.
- **Strategy requests from Home Assistant** (F5) — `script.hbc_strategy_hold` and `script.hbc_strategy_release` hold
  a strategy through the Strategy arbiter, with a time-out, without Node-RED; also via MQTT (`hbc/arbiter/request`).
  Active holds show on the Overview (`sensor.hbc_strategy_holds`).
- **Power setpoint for Charge and Sell** (F6) — a flow that calls *Charge* or *Sell* can pass a total power in
  `msg.power_setpoint = { for, w, by }`; the batteries then run at that power instead of their maximum, within the
  phase rules and the grid limit. For a HELIOS flow that runs the power Helios planned. Without a setpoint nothing
  changes.
- **Version check** (F7) — every HBC+ tab registers its version and the packages have `sensor.hbc_package_version`;
  *HBC+ health* warns (*HBC+ version mismatch*, `sensor.hbc_health` attributes `version_ok`, `version_issues`) when
  tabs, or flows and packages, are of different HBC+ versions, or a tab is missing.
- **Update check** — the Overview shows *HBC+ vX.Y.Z is available* under *Status & control* when GitHub has a newer
  HBC+ release than your packages, with a link to the release notes. Home Assistant asks GitHub at start and every
  6 hours (`sensor.hbc_latest_version`, `binary_sensor.hbc_update_available`); no token or personal data is sent.
  Copy `packages/hbc_control.yaml` again and paste the dashboard again.
- **Version check per part** — every package file has its own version (`sensor.hbc_version_<file>`) and *HBC+ health*
  also checks those against the flows, so one old or missing package file now gives *HBC+ version mismatch* too.
  The dashboard checks itself: a card on the Overview says when it is of another release than the packages and
  flows. `sensor.hbc_package_version` is now the newest version installed (packages and flows), with the
  attributes `files`, `flows` and `mixed`; new `sensor.hbc_release_number`. A *Versions* list on the Settings
  view shows every part, grouped: the dashboard, *Node-RED flows* with each tab (new attribute `flow_versions` on
  `sensor.hbc_health`), *Package files* with each file, and *Marketplace* with each item. A minor release replaces every part; a patch release only the parts it changed, and its
  notes say which. For maintainers: `tools/set-version.py`, `tools/check-versions.py` and a GitHub Action that
  checks a release tag.
- **Marketplace items in the version check** — `sensor.hbc_marketplace` finds the four Marketplace items HBC+ needs
  (Cheapest Energy Hours, card-mod, apexcharts-card, fold-entity-row) through their Marketplace update entities, by
  repository, so a renamed entity still counts. The *Versions* details on the Settings view list each with the
  installed and the latest version (a newer one in orange, a missing one in red), and *Marketplace item not found*
  warns when one is missing.
- **Apps in the version check** — `sensor.hbc_apps` checks the apps and services HBC+ needs: MQTT set up and
  connected, Node-RED running (a report from *HBC+ health* within 11 minutes), and with the Supervisor the version of
  the Mosquitto broker and Node-RED apps. They show under *Apps* in the *Versions* list; *Required app not working*
  warns when MQTT or Node-RED does not work. An external broker or a standalone Node-RED is not a problem.
- **Update notice per part** — a release carries `versions.json` (every part and its version); Home Assistant reads
  it at the release tag (`sensor.hbc_release_manifest`), and the Overview lists each part older than the latest release
  of your version line, the dashboard included (*Not every part of HBC+ vX.Y.Z is installed*;
  `sensor.hbc_outdated_parts`, `sensor.hbc_release_dashboard_number`). The dashboard header takes its version from the
  same constant as the other version cards.
- **Release zip** — a release has `hbc-plus-vX.Y.Z.zip` under *Assets* with only what users install. For maintainers:
  the GitHub Action makes a draft release with the zip, `versions.json` and notes (CHANGELOG entry plus the files to
  copy) on a tag; `tools/release-files.py` lists what changed since the last tag and refuses a changed part without a
  new version; `tools/check-docs.py` checks that the English and Dutch guides are in step; `check-versions.py` also
  checks that every tab is identical in `hbc-plus-all-flows.json` and in its own file; `tools/hooks/pre-commit` runs
  the checks before each commit.
- **Setup self-test** (F8) — one button on the *Batteries* view checks the setup (P1, battery entities,
  master mode, heartbeat, health, the Node-RED flow, price sensor pin, notify targets, EV stop trigger) and
  measures per battery on which phase it is connected (800 W for about 35 s per battery, up to three attempts).
  A phase that differs from the phase map is applied only with *Apply phase map*. New package `hbc_selftest.yaml`,
  new tab *HBC+ Self-test v1.3*, results in `sensor.hbc_self_test_status` and `sensor.hbc_self_test_phases`.
- **Load forecast** (F9) — HBC+ learns the house use per quarter (working days and weekend days apart) and
  forecasts the next 24 hours (`sensor.hbc_load_forecast`). Optionally (*Dynamic uses load forecast*, off by
  default) Dynamic keeps only the cheap quarters the expensive quarters need, from the cheapest before each.
  New package `hbc_load_forecast.yaml` (needs `hbc_savings.yaml`); chart and settings on the Savings view.
- **Steered by Batterijplan** (F10) — when [Batterijplan](https://github.com/satscan1/hbc-batterijplan) (Live) steers
  Dynamic, the dashboard shows it: the *Controller* badge says *Batterijplan* (tap it to open Batterijplan), the Overview
  shows *Managed by Batterijplan (Live)* with Batterijplan's action this quarter, and the price chart under *Pricing* is
  coloured by its plan (with a legend). The Dynamic modes stay editable; Batterijplan sets them every quarter. New
  package `hbc_batterijplan.yaml` (`binary_sensor.hbc_managed_by_batterijplan`); display only, without Batterijplan
  nothing changes.
- **Market price** — every entry of `marks` on `sensor.hbc_energy_prices_data` has `market` next to `price` (buy) and
  `sell`: the bare day-ahead price from the Grid Clock feed (its `spot`; no VAT, tax, supplier margin or grid costs),
  `null` with any other source. New `sensor.hbc_energy_market_price_now`; the shared price fetch returns
  `data_all.market`. For flows such as HELIOS; Dynamic itself does not use it.
- **Managed by HELIOS** — with control mode *External* (strategy *Helios*) the *Controller* badge says *HELIOS*, or
  *HELIOS offline* in red when no HELIOS plan is found, and the Overview shows *Managed by HELIOS Optimizer (Live)*,
  like the Batterijplan line. Display only.
- **HELIOS plan in the price chart** — with *External* chosen, the price chart under *Pricing* on the Overview is
  labelled *HELIOS Optimizer strategy* and colours the future bars by the HBC+ sub-strategy HELIOS planned
  (`input_number.helios_optimizer_energy_plan`, attribute `plan`), with a legend and the planned strategy in the
  tooltip; past bars are grey. Without a HELIOS plan the chart shows the normal price marks. Display only.

### Changed
- **Problem alert** — the Overview alert *HBC+ keeps logging errors* shows how long ago the latest message
  was and a *Fix* line for known problems (new attribute `hint` on `sensor.hbc_health`, also in the
  notification). About 90 s after the last message it turns blue with the time it clears, instead of staying
  red for the full 10-minute window after the cause is fixed.
- **Dashboard layout** — seven views (v1.2 had nine): Overview, Batteries, PID Control, Phase guard, Savings, Settings
  and Logging. The Overview takes over the *Prices*, *Charge & Sell* and *Timed & Dynamic* views. New package
  `hbc_dashboard.yaml`, required for the dashboard:
  - **Control mode and mode** — you choose in two steps: *Control mode* (`input_select.hbc_control_mode`: Manual,
    Schedule = Timed, Price = Dynamic, External = Helios) and, with Manual, the mode (`input_select.hbc_manual_mode`:
    Self-consumption, Solar only, Zero import, Standby, Charge, Charge by deadline, Sell, Stop). Both write
    `input_select.house_battery_strategy` as your choice through the Strategy arbiter, and follow it when the strategy
    changes elsewhere; Node-RED and the strategy names are unchanged. Holds, the EV stop trigger, the price guard and a
    phase overload do not change your choice: the Overview shows them as *Override*
    (`binary_sensor.hbc_override_active`).
  - **Controller** — the master mode is the *Controller* row on the Overview: *HBC+* (Full control), *Marstek*
    (Marstek control), *Marstek M.* (Manual control).
  - **Badges on every view** — *Health*, *Controller* (`sensor.hbc_steered_by`: HBC+, Marstek, Batterijplan, HELIOS
    or HELIOS offline), *Control mode*, *Strategy* (`sensor.hbc_control_state`: what runs now, in friendly words)
    and *Time*.
  - **Dashboard mode** — on after every restart: the Overview shows only Status & control, Now and Batteries. With
    it off, *Now* is hidden and the badges *Show Batteries*, *Show Prices* and *Show Strategies* choose the fourth
    column, one at a time;
    changing a setting yourself brings back *Strategies* (Charge, Charge Deadline and Sell, as far as the control
    mode uses them).
  - **One-line alerts** — every alert, and the Batterijplan and HELIOS lines, is one line; tap it for the details.
  - **New requirement: fold-entity-row** (Marketplace, *Dashboard*) — folds the *Details* under *Tariff data source*
    (Grid Clock zone, supplier and grid operator). Listed in *Requirements* and *Before you start*.
  - **Moved** — the load forecast to the Savings view; the price guard settings to the Settings view; *Battery
    calibration* on the Batteries view, *Notifications* on the Settings view, and *Held by* on the Overview while a
    strategy hold is active.
  - **Batteries view** — the self-test result is one line (*13 of 13 checks passed · all batteries on the expected
    phase*, with the time of the last run) that lists only what needs attention; *Show details* opens every check and
    the phase table. Compact *Run full test* and *Check setup only* buttons. *Battery calibration* shows the plan and a
    bar of the days since full per battery, with its settings folded. *Charges first (battery)* and *Rotation* can be
    changed in place; *Idle and switching* explains what 0 and higher values do.
  - **Phase guard view** — per phase one status line (*L1 · charging 1450 W · active M1*) with the room left in W, an
    orange line only when HBC+ would change something, and the batteries on the phase with what they do; *Show
    details* adds why this battery, since when and the setpoint.
  - **Security** — *Marstek* and *Marstek M.* (handing the batteries to their firmware) ask for confirmation, and the
    installation steps tell you to make the dashboard *Admin only*. The GitHub stars badge is a plain link: no image
    is loaded from a third party.
- **Hardening** — `sensor.hbc_package_version` reads a fixed list of package files instead of looping over every
  sensor (that loop re-rendered it on every sensor change, P1 included, up to once a second); `tools/set-version.py`
  keeps the list in step and `tools/check-versions.py` checks it. The *Master Switch* and *PID presets* tabs have a
  catch node, so their errors reach `sensor.hbc_health` like every other tab's. Debug nodes that wrote to the
  sidebar are off by default (the status counters under the nodes still work). `sensor.hbc_time` was defined twice.
- **Strategy arbiter** — a new *Fit state (255)* node keeps the saved state within the 255 characters of
  `input_text.hbc_strategy_arbiter`: when too many holds are active it drops expired holds first, then inactive ones,
  then the lowest priority, and logs a warning (before, Home Assistant rejected the whole state). Over MQTT the
  requesters `selftest` and `calibration` and the strategy *Self-test* are refused; the MQTT automation adds a fixed
  `source: mqtt`, and the reason shown starts with *MQTT:*. The guides' Mosquitto ACL example gives a client write
  access to `hbc/arbiter/request` only.
- Dashboard, *Now*: the graph shows one row per configured battery (M1 to the value of `input_number.house_battery_count`)
  instead of six rows with empty ones.
- Strategy option *Self-test* in `input_select.house_battery_strategy` (used only by the self-test; chosen by hand it
  stops every battery). Strategy arbiter: requester `selftest` has priority 90.
- Dashboard: *Self-test* is not offered as a choice.
- Dashboard, *HBC+ is not steering the batteries*: when `sensor.p1_meter_power` is unavailable or has had no new value
  for more than 5 minutes, the message says so and points to the P1 meter and its integration (HBC+ only runs a control
  cycle on a P1 update) instead of *Check that Node-RED runs*.
- Dashboard: *Managed by Batterijplan (Live)* and *Managed by HELIOS Optimizer (Live)* are hidden while the
  heartbeat is stale: HBC+ is not steering then, so neither is Batterijplan or HELIOS.
- Dashboard: the price chart under *Pricing* is labelled *HBC+*, *Batterijplan strategy* or *HELIOS Optimizer
  strategy*, after whose plan it shows. The HBC+ chart has a legend like the Batterijplan and HELIOS charts: Cheap,
  Regular, Expensive (the current mark in bold), the negative-price colours when they occur, the current quarter and,
  with separate sell prices, the sell-price line. A history graph on the Overview shows control mode and strategy
  over 12 hours.
- Self-test: with the phase guard on *Enforce*, the *HBC+ phase planner* makes the battery under test the charger on its
  phase, also when the phase map puts another battery there (before, that battery could stay idle: *did not charge*).
  *Did not charge* now names the likely cause; the *Phase detection* card shows the phase guard mode.
- Dynamic, *Determine dynamic strategy*: step 3b for the load forecast; with the switch off the marks are identical
  to before. `sensor.hbc_energy_prices_data` has a new attribute `load_forecast`.

### Fixed
- Dashboard: the history graph under *Now* asked for 3 minutes of history and failed (*Invalid start_time*) when the
  browser clock ran more than 3 minutes ahead; it now shows 6 minutes. The *Batteries view* notes linked to a page
  that does not exist, and three headings used an icon that only exists with Batterijplan installed.
- **Package failed to load: duplicate key 'exclude'** — `hbc_calibration.yaml`, `hbc_load_forecast.yaml`,
  `hbc_phase_guard.yaml` and `hbc_savings.yaml` each had their own `recorder: exclude:` next to `hbc_control.yaml`.
  Home Assistant allows that key in one package only, so it refused `hbc_control.yaml` (*Setup of package
  'hbc_control' failed: integration 'recorder' has duplicate key 'exclude'*). All HBC+ recorder exclusions are now in
  `hbc_control.yaml`, together with `sensor.hbc_marketplace` and `sensor.hbc_apps`. Copy all five files again.
- Dynamic: a tariff source named *Grid Clock feed*, *Grid Clock BE* or any other name that starts with *Grid Clock*
  gave no prices; it now reads the Grid Clock feed.
- Lost connection to Home Assistant: every node that calls HA failed with `NoConnectionError` and was logged as an
  *Unhandled exception* error, usually first from *HBC+ Strategy Timed >> Render settings* (its 30-s settings refresh),
  so the alert pointed at Timed. It is now ONE warning per outage, *No connection to Home Assistant since HH:MM*,
  repeated every 5 minutes while it lasts, with a *Fix* hint; *Once per (re)connect* (Start tab) clears it when HA
  runs again. Timed skips its settings refresh while there is no connection (new node *HA connected?*) and keeps
  using the last settings.
- Dashboard, PID Control: the *PID analysis* graph could show *Unable to load history: Invalid start_time*. It asked
  for only 90 s of history (`hours_to_show: 0.025`), and Home Assistant refuses a start time later than its own clock,
  so a browser clock more than 90 s ahead of the HA server broke the graph. It now shows 6 minutes
  (`hours_to_show: 0.1`).

### Documentation
- README, user guide (English and Dutch) and `node-red/README.md` describe v1.3: the new dashboard layout, parts and alerts, the
  update and version-check entities in the configuration reference, troubleshooting for the update notice and test
  notifications, optional requirements (solar forecast, Workday). New release notes `docs/release-notes/v1.3.md`, also in Dutch
  (`v1.3.nl.md`), and a Dutch README (`README.nl.md`, also in the release zip).

### Updating from 1.2
Copy all packages except your own `hbc_config.yaml` (new: `hbc_notify.yaml`, required, `hbc_calibration.yaml`, `hbc_savings.yaml`, `hbc_selftest.yaml`,
`hbc_load_forecast.yaml`, `hbc_batterijplan.yaml` and `hbc_dashboard.yaml`), delete the old
HBC+ tabs and import `node-red/hbc-plus-all-flows.json`, install **fold-entity-row** from Marketplace and paste the
dashboard again (new layout; *Dashboard mode* is
on after a restart, switch it off to see every setting). Had you set your own notify
action? Put it in *Notify targets* and press *Send a test notification*. Full steps: *Updating from v1.2* in the user
guide. Then run the self-test once (*Batteries* → *Battery phase test*).

## [1.2.2] – 24 November 2026

The phase guard on *Monitor* no longer stops the batteries; only *Enforce* does. The Node-RED flows are unchanged
(still v1.2.1): no need to import them again.

### Changed
- Phase guard on *Monitor*: a phase that stayed overloaded with the batteries part of the cause no longer switches
  to *Full stop*. On *Monitor* the automation *HBC+: Full stop when a phase stays overloaded by the batteries* now only
  writes to the logbook and notifies what it would have done (*HBC+: phase overload (Monitor)*); *Full stop* only
  happens on *Enforce*. The note on the Phase guard view says so too.
  Copy `packages/hbc_phase_guard.yaml` again and paste the dashboard again.

## [1.2.1] – 21 November 2026

Fixes for a fresh install, a separate *Pricing List* switch on the Prices view, and clearer installation steps.

### Changed
- Prices view: the *Insights mode* badge is now **Pricing List** (`input_boolean.house_battery_control_show_price_list`,
  new). It only shows or hides the price list (*Price marks visualisation*) and no longer switches Insight mode
  (Logging *Live*) on. Copy `packages/hbc_control.yaml` again and paste the dashboard again.

### Fixed
- Fresh install: Self-consumption logged *Controller disabled — all PID gains are 0* on every tick. The script
  *HBC+ phase guard: apply defaults* now also selects the PID preset *Safe* and sets its gains (Kp 0.3, Ki 0.3,
  Kd 0.1).
- Fresh install: the dashboard kept showing *Step 3 — Setup Node-RED* after the flows were deployed. Node-RED turned
  on `input_boolean.house_battery_control_has_node_red` only once, 2 s after deploy, often before it was connected to
  Home Assistant. It now also does this each time it (re)connects (tab *HBC+ Home Battery Start*).
- Prices view: the price list and the *Using the dynamic strategy* link stayed hidden when the Marketplace reported
  `update.cheapest_energy_hours_update` as unknown or unavailable, as it often does on a fresh install.

### Documentation
- Installation: new section *Before you start — install from Marketplace* (Cheapest Energy Hours, card-mod,
  apexcharts-card); card-mod is now listed as required.
- Requirements as a bullet list, in the user guide and in a new *Requirements* section of the README.
- The dashboard URL must be `home-battery-control-plus`, or the buttons that open other views lead nowhere.

### Updating from 1.2.0
Copy `packages/hbc_control.yaml` and `packages/hbc_phase_guard.yaml` again, check the configuration and restart HA.
Delete the old HBC+ tabs in Node-RED, import `node-red/hbc-plus-all-flows.json` and deploy. Paste
`dashboards/hbc_plus.yaml` again. If Self-consumption logs *Controller disabled*, choose the PID preset *Safe* on the
PID Control view.

## [1.2.0] – 20 November 2026

Ready for the end of Dutch net metering on 1 January 2027: from then on an exported kWh earns less than an
imported kWh costs. With default settings v1.2 behaves exactly like v1.1.

### Added
- **Grid Clock feed** (F6) — the *Tariff data source* *Grid Clock* now has all-in buy and sell prices per quarter for
  your own supplier, from the public files on `cdn.gridclock.eu`. No account, token or registration; only the zone and the
  supplier's short name are in the request. Supplier and (Belgium) grid operator are chosen on the Prices view
  and kept across restarts. New package `hbc_gridclock.yaml`, status in `sensor.hbc_grid_clock_feed`.
- **Buy and sell prices** (F7) — every quarter carries a sell price next to the buy price. Dynamic values *Sell* at
  the sell price; new `sensor.hbc_energy_export_price_now`, *Sell now* tile and a sell line in the price chart.
- **Price guard** (F8) — while prices are negative, stops exporting and charges instead (Off / Monitor / On, Off by
  default), with signals for a PV limiter (`binary_sensor.hbc_pv_curtail_advised`). New package
  `hbc_price_guard.yaml`. *On* only with the tariff source *Grid Clock*; never overrides *Full stop* or the EV stop trigger.
- **Logo** — the HBC+ logo in the dashboard header and the README. New folder `www/hbc-plus/`: copy it into your HA
  `www/` folder. All logo files (SVG and PNG) are in `assets/logo/`.

### Changed
- Dynamic: *Price split* gives every source a sell list (sell = buy without the feed); marks carry `sell` and `neg`.
- Start, Timed, Charge and Sell apply the price guard; Charge has a new *Price goal*.
- All flow tabs are named *v1.2*; the *How this flow works* texts describe the v1.2 changes.
- Dashboard: new tab layout in the order you use it: Overview, Prices, Charge & Sell, Timed & Dynamic, Phase guard,
  PID Control, Batteries, Settings and Logging; the view addresses stay the same. Buy/sell tiles, sell line, price
  guard section and a price-guard alert on the Overview.
- Tariff data source *Grid Clock* reads the Grid Clock feed instead of the Grid Clock integration; the integration and
  its automation in `hbc_config.yaml` are no longer needed.
- Charge Deadline: *Deadline required power* and *HBC battery fleet SoC* show *unknown* without a log error when they
  have no value (before: *Received invalid sensor state: unknown … expected a number*).
- `hbc_config.yaml`: clean P1 alias templates to uncomment (option A: other sensor names, option B: import and export per
  phase, e.g. DSMR in kW); the update steps keep your own copy. Setup step 2 (Settings view) explains both.

### Updating from 1.1
Copy all packages except your own `hbc_config.yaml` (new: `hbc_gridclock.yaml`, `hbc_price_guard.yaml`) and the new folder `www/hbc-plus/` into your HA `www/`
folder, delete the old HBC+ tabs and import
`node-red/hbc-plus-all-flows.json`, paste the dashboard again (new tab layout). Used *Grid Clock* as source? It stays selected and
now reads the feed: choose your supplier. Full steps: *Updating from v1.1* in the user guide.

## [1.1.0] – 16 November 2026

Safer when something goes wrong.

- **Robustness (R5–R12):** heartbeat only after a good control cycle and no longer undone by the Master Switch; held
  values and checked setpoints (no NaN to the batteries); warnings and errors always logged and published to
  `sensor.hbc_health` with an alert; fail-safe phase guard on *Enforce*; Home Assistant switches to *Full stop* when
  the batteries keep a phase overloaded; a battery that ignores commands is reported.
- **Security (S1–S3):** heartbeat judged by when HA received it; a notification when a phase guard safety setting
  changes; test buttons removed from the live flows.
- **Performance (P5–P8):** busy phase sensors out of the database, quieter output failsafe, lighter control loop,
  Dynamic recalculates once 3 s after the last setting change.
- **Dashboard:** fixed view paths and links (`/home-battery-control-plus/<view>`).
- **Flows:** tab names end in v1.1; `node-red-node-smooth` no longer needed.

## [1.0.0]

First standalone release of HBC+, built on HBC by CodeBob: the phase guard for two batteries per phase, the Strategy
arbiter, Battery Oscillation Guard, Charge Deadline, the HA heartbeat fallback and the changes B1–B8, R1–R4, P1–P4,
F1–F5 and E1–E4 (see *Improvements in HBC+* in the user guide).
