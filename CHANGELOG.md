# Changelog

All notable changes to HBC+ (Home Battery Control Plus). The user guide has the details: *What's new* and
*Updating from …* per version ([English](docs/user-guide.en.md), [Nederlands](docs/gebruikershandleiding.nl.md)).

## [1.2.0] – planned 10 December 2026

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
Copy all packages except your own `hbc_config.yaml` (new: `hbc_gridclock.yaml`, `hbc_price_guard.yaml`), delete the old HBC+ tabs and import
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
