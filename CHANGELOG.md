# Changelog

All notable changes to HBC+ (Home Battery Control Plus). The user guide has the details: *What's new* and
*Updating from …* per version ([English](docs/user-guide.en.md), [Nederlands](docs/gebruikershandleiding.nl.md)).

## [1.4.0] – in development

### Added
- **Setup self-test** (F1) — one button on the *Advanced settings* view checks the setup (P1, battery entities,
  master mode, heartbeat, health, the Node-RED flow, price sensor pin, notify targets, EV stop trigger) and
  measures per battery on which phase it is connected (800 W for about 35 s per battery, up to three attempts).
  A phase that differs from the phase map is applied only with *Apply phase map*. New package `hbc_selftest.yaml`,
  new tab *HBC+ Self-test v1.4*, results in `sensor.hbc_self_test_status` and `sensor.hbc_self_test_phases`.
- **Load forecast** (F2) — HBC+ learns the house use per quarter (working days and weekend days apart) and
  forecasts the next 24 hours (`sensor.hbc_load_forecast`). Optionally (*Dynamic uses load forecast*, off by
  default) Dynamic keeps only the cheap quarters the expensive quarters need, from the cheapest before each.
  New package `hbc_load_forecast.yaml` (needs `hbc_savings.yaml`); chart and settings on the Timed/Dynamic view.

### Changed
- Strategy option *Self-test* in `input_select.house_battery_strategy` (used only by the self-test; chosen by hand it
  stops every battery). Strategy arbiter: requester `selftest` has priority 90.
- Dashboard: the *Choose strategy* tile no longer offers *Self-test*.
- Dynamic, *Determine dynamic strategy*: step 3b for the load forecast; with the switch off the marks are identical
  to v1.3. `sensor.hbc_energy_prices_data` has a new attribute `load_forecast`.

 – planned 10 December 2026

Ready for the end of Dutch net metering on 1 January 2027: from then on an exported kWh earns less than an
imported kWh costs. With default settings v1.2 behaves exactly like v1.1.

### Added
- **Grid Clock feed** (F6) — new *Tariff data source* with all-in buy and sell prices per quarter for your own
  supplier, from the public files on `cdn.gridclock.eu`. No account, token or registration; only the zone and the
  supplier's short name are in the request. Supplier and (Belgium) grid operator are chosen on the Timed/Dynamic
  view and kept across restarts. New package `hbc_gridclock.yaml`, status in `sensor.hbc_grid_clock_feed`.
- **Buy and sell prices** (F7) — every quarter carries a sell price next to the buy price. Dynamic values *Sell* at
  the sell price; new `sensor.hbc_energy_export_price_now`, *Sell now* tile and a sell line in the price chart.
- **Price guard** (F8) — while prices are negative, stops exporting and charges instead (Off / Monitor / On, Off by
  default), with signals for a PV limiter (`binary_sensor.hbc_pv_curtail_advised`). New package
  `hbc_price_guard.yaml`. *On* only with the Grid Clock feed; never overrides *Full stop* or the EV stop trigger.

### Changed
- Dynamic: *Price split* gives every source a sell list (sell = buy without the feed); marks carry `sell` and `neg`.
- Start, Timed, Charge and Sell apply the price guard; Charge has a new *Price goal*.
- All flow tabs are named *v1.2*; the *How this flow works* texts describe the v1.2 changes.
- Dashboard: buy/sell tiles, sell line, price guard section, Home view price-guard card.

### Removed
- Tariff data source *Grid Clock* (prices from the Grid Clock integration) and its automation in `hbc_config.yaml`.
  *Grid Clock feed* replaces it and needs no integration.

### Updating from 1.1
Copy all packages (new: `hbc_gridclock.yaml`, `hbc_price_guard.yaml`), delete the old HBC+ tabs and import
`node-red/hbc-plus-all-flows.json`, paste the dashboard again. Used *Grid Clock* as source? Choose your supplier
under *Grid Clock feed*. Full steps: *Updating from v1.1* in the user guide.

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
