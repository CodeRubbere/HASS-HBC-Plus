# Changelog

All notable changes to HBC+ (Home Battery Control Plus). The user guide has the details: *What's new* and
*Updating from …* per version ([English](docs/user-guide.en.md), [Nederlands](docs/gebruikershandleiding.nl.md)).

## [1.4.0] – in development

### Added
- **Setup self-test** (F1) — one button on the *Batteries* view checks the setup (P1, battery entities,
  master mode, heartbeat, health, the Node-RED flow, price sensor pin, notify targets, EV stop trigger) and
  measures per battery on which phase it is connected (800 W for about 35 s per battery, up to three attempts).
  A phase that differs from the phase map is applied only with *Apply phase map*. New package `hbc_selftest.yaml`,
  new tab *HBC+ Self-test v1.4*, results in `sensor.hbc_self_test_status` and `sensor.hbc_self_test_phases`.
- **Load forecast** (F2) — HBC+ learns the house use per quarter (working days and weekend days apart) and
  forecasts the next 24 hours (`sensor.hbc_load_forecast`). Optionally (*Dynamic uses load forecast*, off by
  default) Dynamic keeps only the cheap quarters the expensive quarters need, from the cheapest before each.
  New package `hbc_load_forecast.yaml` (needs `hbc_savings.yaml`); chart and settings on the Timed & Dynamic view.
- **Steered by Batterijplan** (F3) — when [Batterijplan](https://github.com/satscan1/hbc-batterijplan) (Live) steers
  Dynamic, the dashboard shows it: *Dynamic · managed by Batterijplan (Live)* on the Overview, a banner with
  Batterijplan's action on the Prices and Timed & Dynamic views, the *Price intervals* chart coloured by its plan
  (with a legend), and the three Dynamic modes read-only. New package `hbc_batterijplan.yaml`
  (`binary_sensor.hbc_managed_by_batterijplan`); display only, without Batterijplan nothing changes.
- **Managed by HELIOS banner** — when the *Helios* strategy is selected, the Overview, Prices and Timed & Dynamic
  views show a *Managed by HELIOS* banner, like the Batterijplan one. Display only.
- **HELIOS plan in the price chart** — with *Helios* selected, the *Price intervals* chart on the Prices and Timed &
  Dynamic views is titled *Price intervals: HELIOS plan* and colours the future bars by the HBC+ sub-strategy HELIOS
  planned (`input_number.helios_optimizer_energy_plan`, attribute `plan`), with a legend and the planned strategy in
  the tooltip; past bars are grey. Without a HELIOS plan the chart shows the normal price marks. Display only.

### Changed
- Strategy option *Self-test* in `input_select.house_battery_strategy` (used only by the self-test; chosen by hand it
  stops every battery). Strategy arbiter: requester `selftest` has priority 90.
- Dashboard: the *Choose strategy* tile no longer offers *Self-test*.
- Dashboard, *HBC+ is not steering the batteries*: when `sensor.p1_meter_power` is unavailable or has had no new value
  for more than 5 minutes, the message says so and points to the P1 meter and its integration (HBC+ only runs a control
  cycle on a P1 update) instead of *Check that Node-RED runs*.
- Dashboard: the Batterijplan and HELIOS banners, and *Dynamic · managed by Batterijplan (Live)*, are hidden while the
  heartbeat is stale: HBC+ is not steering then, so neither is Batterijplan or HELIOS.
- Dashboard: the chart title *Price intervals: Batterijplan plan* is now *Price intervals: Batterijplan*; on the Prices
  view the *Buy now* and *Sell now* tiles are *Buy price* and *Sell price*. New full-width *Executing now* card below
  the price chart (Prices and Timed & Dynamic views) with the sub-strategy HBC+ runs now
  (`input_text.house_battery_strategy_active_sub_strategy`).
- Dashboard: *Price intervals: HBC+* (Prices and Timed & Dynamic views) has a legend like the Batterijplan and HELIOS
  charts: Cheap, Regular, Expensive (the current mark in bold), the negative-price colours when they occur, the current
  quarter and, with separate sell prices, the sell-price line.
- Self-test: with the phase guard on *Enforce*, the *HBC+ phase planner* makes the battery under test the charger on its
  phase, also when the phase map puts another battery there (before, that battery could stay idle: *did not charge*).
  *Did not charge* now names the likely cause; the *Phase detection* card shows the phase guard mode.
- Dynamic, *Determine dynamic strategy*: step 3b for the load forecast; with the switch off the marks are identical
  to v1.3. `sensor.hbc_energy_prices_data` has a new attribute `load_forecast`.

## [1.3.0] – planned 22 December 2026

### Added
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
  attributes `files`, `flows` and `mixed`; new `sensor.hbc_release_number`. A *Versions* table on the Settings
  view lists every part. A minor release replaces every part; a patch release only the parts it changed, and its
  notes say which. For maintainers: `tools/set-version.py`, `tools/check-versions.py` and a GitHub Action that
  checks a release tag.
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

### Fixed
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

### Changed
- Phase guard on *Monitor*: a phase that stayed overloaded with the batteries part of the cause no longer switches
  to *Full stop*. On *Monitor* the automation *HBC+: Full stop when a phase stays overloaded by the batteries* now only
  writes to the logbook and notifies what it would have done (*HBC+: phase overload (Monitor)*); *Full stop* only
  happens on *Enforce*. The note on the Phase guard view says so too.
- **Problem alert** — the Overview alert *HBC+ keeps logging errors* shows how long ago the latest message
  was and a *Fix* line for known problems (new attribute `hint` on `sensor.hbc_health`, also in the
  notification). About 90 s after the last message it turns blue with the time it clears, instead of staying
  red for the full 10-minute window after the cause is fixed.
- Dashboard (v1.2 tab layout): *Battery calibration* on the Batteries view, *Notifications* on the Settings view, and
  *Held by* on the Overview while a strategy hold is active.

### Updating from 1.2
Copy all packages except your own `hbc_config.yaml` (new: `hbc_notify.yaml`, required, `hbc_calibration.yaml` and `hbc_savings.yaml`), delete the old
HBC+ tabs and import `node-red/hbc-plus-all-flows.json`, paste the dashboard again. Had you set your own notify
action? Put it in *Notify targets* and press *Send a test notification*. Full steps: *Updating from v1.2* in the user
guide.

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
