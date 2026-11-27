
<p align="center"><img src="assets/logo/hbc-plus-readme.svg" alt="HBC+ Home Battery Control Plus" width="720"></p>

# Home Battery Control Plus (HBC+)

Home Battery Control Plus is een open-source oplossing voor de community om thuisbatterijen en elektrische auto's aan te sturen met Home Assistant en Node-RED. Stuur je batterijen precies zoals jij wilt, alles op één plek en zonder vendor lock-in.

Dit project is bedoeld voor hobbyisten die volledige controle willen over hun thuisbatterijen. Het biedt kant-en-klare flows en configuratievoorbeelden, waaronder een PID-regelaar voor geavanceerd batterijbeheer. Gebruik op eigen verantwoordelijkheid.

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-3DDC84?logo=home-assistant&logoColor=#03A9F4)](https://www.home-assistant.io/) 
[![Node-RED](https://img.shields.io/badge/Node--RED-Flow-FF4A00?logo=node-red&logoColor=)](https://nodered.org/)
![License](https://img.shields.io/github/license/gitcodebob/marstek-venus-rs485-node-red)
[![GitHub stars](https://img.shields.io/github/stars/CodeRubbere/HASS-HBC-Plus?style=flat)](https://github.com/CodeRubbere/HASS-HBC-Plus/stargazers)

**Huidige versie: v1.2.2** (24 november 2026) · [Download](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) · [Nieuw in v1.2](docs/gebruikershandleiding.nl.md#nieuw-in-hbc-v12)

**Volgende: v1.3**, gepland voor 22 december 2026 · [Nieuw in v1.3](docs/gebruikershandleiding.nl.md#nieuw-in-hbc-v13) · [Release notes](docs/release-notes/v1.3.nl.md) · [Changelog](CHANGELOG.md) (Engels)

> 🇬🇧 English: [README.md](README.md) · [user guide](docs/user-guide.en.md)

## Credits

HBC+ is een zelfstandige versie met een eigen ontwikkeling. Het begon bij House Battery Control (HBC) v4.15.1 van **CodeBob** ([gitcodebob/marstek-venus-rs485-node-red](https://github.com/gitcodebob/marstek-venus-rs485-node-red)), de grondlegger van HBC: de oorspronkelijke regellus, strategieën, het dashboard en de helpers zijn zijn werk, en alle eer voor die basis gaat naar hem. HBC+ heeft verder geen band met HBC.

Het Node-RED + HA-regelschema is gebaseerd op de aanpak van Ruald Ordelman. En op de eenvoudig te gebruiken Modbus-naar-HA-boards van [Fonske](https://github.com/fonske). Veel dank voor het delen van jullie werk en ideeën met de community!

Batterijpackages bijgedragen door de community:
- [Fonske](https://github.com/fonske) — Marstek Venus-packages via [Modbus TCP-IP](https://github.com/fonske/MarstekVenusV3-modbus-TCP-IP) en RS485 ([Lilygo](https://github.com/fonske/MarstekVenus-LilygoRS485) / [M5Stack](https://github.com/fonske/MarstekVenus-M5stackRS485)), en de referentie-naamgeving `marstek_m1_*` waarop elk ander package aansluit
- [Jos1958](https://github.com/Jos1958) — Anker SolarBank 3 Pro (cloud bridge)
- [@wouterbouvy](https://github.com/wouterbouvy) — Anker SOLIX Solarbank Max AC / Solarbank 4 (lokale Modbus TCP)

## Wat HBC+ toevoegt

- **Fasebewaking** — een fasekaart voor maximaal 6 batterijen (M1–M6), standaard één actieve batterij per fase, en per fase ruimte onder zowel de netzekering als de batterijgroep, elke tick berekend uit de P1-meter. Optioneel de modus *Shared headroom*.
- **Juist plafond voor planners** — Charge Deadline plant met het maximale vermogen per fase, niet met de som van alle batterijen.
- **Strategie Charge Deadline** — laadt vóór een deadline tot een doel (vol, SoC of energiereserve), in de goedkoopste kwartieren, met optioneel een PV-reserve en een vervolgstrategie zodra de deadline voorbij is.
- **Grid Clock-prijzen** — de tariefbron *Grid Clock* leest all-in inkoop- en terugleverprijzen per kwartier voor je eigen leverancier uit de openbare [Grid Clock](https://gridclock.eu)-feed: geen account, token of registratie. De prijzen worden vanzelf ververst na een wijziging van zone of leverancier.
- **Inkoop- en terugleverprijs** — Dynamic waardeert *Sell* naar wat een teruggeleverde kWh echt oplevert, klaar voor het einde van de salderingsregeling op 1 januari 2027.
- **Prijsbewaking** — stopt met terugleveren en laadt juist bij negatieve prijzen; signalen voor een PV-begrenzer. Standaard uit.
- **View Phase guard** op het dashboard en een overbelastingsalarm in Home Assistant dat ook werkt als Node-RED niet draait.
- **Gedeelde prijsophaling** — de groep *API call to Data Source* in *HBC+ Strategy Dynamic* is een link-call-subroutine: elke flow kan de actuele prijslijst ophalen met één **link call** naar *Dynamic Fetch from Data Source* (time-out ≥ 30 s), eventueel voor een andere bron (`msg.dynamic.data_source`) of uit de cache (`msg.dynamic_use_cache`). De aanroeper krijgt altijd antwoord in `msg.dynamic`: verse prijzen, de laatste geldige prijzen (`stale`) als de bron faalt, of `no_data`. Fouten binnen de groep worden opgevangen, dus een aanroeper wacht nooit op een time-out.
- **Verbeteringen in veiligheid, performance en stabiliteit** (een fail-safe fasebewaking op *Enforce*, een *Full stop* als de batterijen een fase overbelast houden, een heartbeat-fallback die alleen werkende regelcycli telt, batterijwaarden die nooit NaN worden, waarschuwingen en fouten die altijd in het Node-RED-log en `sensor.hbc_health` komen, minder Modbus-schrijfacties, één snelle leesnode, bugfixes).

Met de fasebewaking op *Off* of *Monitor* stuurt HBC+ de batterijen zonder faseregels. Alleen *Enforce* past ze toe.

**Komt in v1.3** (in ontwikkeling, gepland voor 22 december 2026):

- **Besparing** — wat je energie kostte met de batterijen vergeleken met zonder, per dag, maand en jaar, en het gemeten rendement met een voorgestelde *Minimum spread*.
- **Batterijkalibratie** — een batterij die 14 dagen niet vol is geweest, wordt één keer tot 100 % geladen, in het goedkoopste blok van de nacht.
- **Zelftest bij installatie** — één knop controleert de installatie en meet op welke fase elke batterij is aangesloten.
- **Voorspelling huisverbruik** — HBC+ leert hoeveel het huis per kwartier gebruikt; optioneel laadt Dynamic alleen wat de dure kwartieren nodig hebben.
- **Eén meldingsinstelling** — *Notify targets* op de view Settings, met een testknop.
- **Strategie-aanvragen vanuit Home Assistant** — houd een strategie vast vanuit een automatisering of via MQTT, met een time-out, zonder Node-RED.
- **Vermogens-setpoint voor Charge en Sell** — een flow zoals HELIOS kan Charge of Sell op een gepland vermogen laten draaien in plaats van op het maximum.
- **Nieuw dashboard** — kies in twee stappen (*Control mode*: Manual, Schedule, Price of External; dan de modus), met badges op elke view voor wie beslist (*Controller*), de control mode en wat er nu draait (*Strategy*). Een rustige *Dashboard mode* na elke herstart, meldingen van één regel waarop je tikt voor details, en zeven views in plaats van negen.
- **Markt-, inkoop- en terugleverprijs voor andere flows** — met Grid Clock heeft elk kwartier in `sensor.hbc_energy_prices_data` de kale marktprijs naast de inkoop- en terugleverprijs, voor flows zoals HELIOS.
- **Batterijplan en HELIOS op het dashboard** — de badge *Controller*, een regel *Managed by* en de prijsgrafiek laten zien wie beslist en wat er gepland is.
- **Update- en versiecheck** — de Overview meldt wanneer er een nieuwere release is, en welk onderdeel van je installatie een andere versie heeft; de view Settings controleert ook de Marketplace-onderdelen die HBC+ nodig heeft, en of MQTT en Node-RED werken.
- **Release-zip** — `hbc-plus-vX.Y.Z.zip` onder *Assets*, met alleen wat je installeert.

## Werkt met Batterijplan

[Batterijplan](https://github.com/satscan1/hbc-batterijplan) is een Home Assistant-integratie die HBC+ kan aansturen. Met HBC+ op **Dynamic** en de schakelaar **Live** van Batterijplan aan, zet Batterijplan elk kwartier de Dynamic-modi. Vanaf v1.3 laat het dashboard dat zien: de badge *Controller* zegt *Batterijplan*, de Overview toont *Managed by Batterijplan (Live)* met de actie van nu, en de prijsgrafiek krijgt de kleuren van zijn plan (`packages/hbc_batterijplan.yaml`). Zonder Batterijplan verandert er niets. Details: [Aangestuurd door Batterijplan](docs/gebruikershandleiding.nl.md#aangestuurd-door-batterijplan).

## Indeling van de repository

| Pad | Inhoud |
| --- | --- |
| `packages/` | Home Assistant-packages: basis-helpers, Charge Deadline, Strategy arbiter, de fasebewuste heartbeat-fallback `hbc_heartbeat.yaml`, `hbc_phase_guard.yaml`, de meldingsinstelling `hbc_notify.yaml`, de batterijkalibratie `hbc_calibration.yaml`, besparing `hbc_savings.yaml`, de zelftest `hbc_selftest.yaml`, de voorspelling van het huisverbruik `hbc_load_forecast.yaml`, de Batterijplan-indicator `hbc_batterijplan.yaml` en de dashboardhelpers `hbc_dashboard.yaml` (HBC+) |
| `dashboards/hbc_plus.yaml` | Het dashboard *Home Battery Control Plus* (Engels): Overview, Batteries, PID Control, **Phase guard**, Savings, Settings en Logging |
| `www/hbc-plus/` | Het dashboardlogo; kopieer het naar de map `www/` van HA |
| `assets/logo/` | Het HBC+-logo als SVG en PNG: op licht, op donker, in één kleur, app-icoon, GitHub-socialpreview |
| `node-red/hbc-plus-all-flows.json` | Alle 16 HBC+-tabbladen voor Node-RED in één importbestand |
| `node-red/*.json` | Dezelfde tabbladen als losse bestanden |
| `node-red/README.md` | Per tabblad wat HBC+ verandert (Engels) |
| `node-red/examples/` | Voorbeeldtabblad voor de gedeelde prijsophaling |
| `tools/` | Voor beheerders: `set-version.py` zet de versie van een release en schrijft `versions.json`; `check-versions.py` (versies, gelijke flowbestanden, de lijsten met packages, `versions.json`), `check-docs.py` (Engelse en Nederlandse handleiding gelijk, CHANGELOG-regel) en `release-files.py` (wat er sinds de laatste tag veranderd is, en dat elk gewijzigd onderdeel een nieuwe versie heeft). `hooks/pre-commit` draait de eerste twee vóór elke commit (`git config core.hooksPath tools/hooks`). De GitHub Action in `.github/workflows/` draait ze bij elke push en maakt bij een tag een concept-release met de zip |
| `versions.json` | Het release-manifest: elk onderdeel en zijn versie. Home Assistant leest het bij de release-tag om te zeggen welke onderdelen ouder zijn dan de release |
| `docs/` | Handleiding in het Engels en Nederlands, en de release notes per versie |

## Vereisten

- **Home Assistant** met packages aan (`homeassistant: packages: !include_dir_named packages`).
- **Node-RED** (add-on of los) met `node-red-contrib-home-assistant-websocket` 0.80 of nieuwer.
- **Node-RED-palette** `node-red-contrib-time-range-switch`.
- **MQTT**: de MQTT-integratie in HA met een broker.
- **Batterijen**: Marstek Venus E, maximaal 6, entiteiten met de naam `marstek_mN_*` (RS485 of Modbus TCP).
- **Netmeter**: `sensor.p1_meter_power` en vermogen per fase `sensor.p1_meter_power_phase_1` … `_3`, positief bij afname.
- **Dashboard-URL**: `home-battery-control-plus`, zodat de knoppen die andere views openen werken. De naam maakt niet uit; de URL kun je later niet meer wijzigen.
- **Dashboard**: `apexcharts-card`, `card-mod` en `fold-entity-row` (alle drie via Marketplace).
- **Prijzen**: de [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours)-macro (Marketplace) en een prijsintegratie, voor Dynamic en Charge Deadline.
- **Optioneel**: een zonnevoorspelling (bijvoorbeeld Forecast.Solar of Solcast) voor het laaddoel *solar forecast* en de zon-check van de batterijkalibratie; de Workday-integratie (`binary_sensor.workday_sensor`), zodat de voorspelling van het huisverbruik een feestdag als weekenddag telt.

Details per vereiste: [Vereisten in de handleiding](docs/gebruikershandleiding.nl.md#vereisten).

## Snel aan de slag

1. Download de [nieuwste release](https://github.com/CodeRubbere/HASS-HBC-Plus/releases/latest) (*Assets* → **hbc-plus-vX.Y.Z.zip**; vóór v1.3: *Source code (zip)*) en pak hem uit.
2. Zorg dat Home Assistant (met packages en MQTT) en Node-RED (zie *Vereisten*) draaien.
   Installeer via Marketplace **Cheapest Energy Hours**, **card-mod**, **apexcharts-card** en **fold-entity-row**, herstart daarna HA en herlaad de browser.
3. **Maak een back-up** van Node-RED (*Export → All flows*) en Home Assistant.
4. Kopieer `packages/*.yaml` naar de map `packages/` van HA en `www/hbc-plus/` naar de map `www/` van HA (het dashboardlogo), herstart HA en draai één keer het script **HBC+ phase guard: apply defaults**.
5. Importeer `node-red/hbc-plus-all-flows.json` in Node-RED (bijwerken? verwijder eerst de oude HBC+-tabbladen: Node-RED kan een flow bij import niet vervangen), controleer dat de servernode *HA System* **Expose to global context** aan heeft, en deploy.
6. Voeg een dashboard toe met de naam *Home Battery Control Plus* (**de URL moet `home-battery-control-plus` zijn**) met de inhoud van `dashboards/hbc_plus.yaml`, maak het *Alleen beheerder* (iedereen die het kan openen, kan de batterijen aansturen), stel je fasekaart in op de view **Batteries**, en de netzekering en batterijgroep onder *Phase guard settings* op de view **Settings**.
7. Stel *Notify targets* in op de view **Settings** en druk op *Send a test notification*; draai één keer de zelftest op de view **Batteries** (*Battery phase test*).
8. Druk op **HBC+** onder *Controller* op de Overview om HBC+ te laten sturen, en kies een *Control mode*.
9. Laat de fasebewaking een paar dagen op **Monitor** draaien en zet hem daarna op **Enforce**.

Volledige instructies: **[docs/gebruikershandleiding.nl.md](docs/gebruikershandleiding.nl.md)**.

**Bijwerken?** Volg [Bijwerken vanaf v1.2](docs/gebruikershandleiding.nl.md#bijwerken-vanaf-v12): nieuwe packages (waaronder het verplichte `hbc_notify.yaml`), en de oude HBC+-tabbladen worden vóór de import verwijderd. De algemene stappen voor elke release: [HBC+ bijwerken](docs/gebruikershandleiding.nl.md#hbc-bijwerken).

Vragen of bugs: open een issue op [github.com/CodeRubbere/HASS-HBC-Plus/issues](https://github.com/CodeRubbere/HASS-HBC-Plus/issues).

## Kom je van HBC?

Draai je al House Battery Control (HBC) van CodeBob? Dan kun je overstappen op HBC+ zonder opnieuw te beginnen: HBC+ gebruikt dezelfde helpernamen, dus je strategie en je instellingen voor Timed, Dynamic, Charge, Sell en PID komen mee. Wat er verandert:

- **Packages:** `house_battery_control.yaml` wordt vervangen door de `hbc_*.yaml`-packages; hernoem je eigen `house_battery_control_config.yaml` naar `hbc_config.yaml` (de `hbc_config.yaml` in deze repository is voor nieuwe installaties).
- **Netmeter:** HBC+ heeft ook het vermogen per fase nodig (`sensor.p1_meter_power_phase_1` … `_3`).
- **Nieuwe vereisten:** MQTT, `card-mod` en `fold-entity-row`; `node-red-node-smooth` is niet meer nodig.
- **Flows:** alle HBC-tabbladen worden verwijderd en vervangen door de HBC+-tabbladen; draai nooit beide.
- **Dashboard:** een nieuw dashboard met de URL `home-battery-control-plus`.

De overstap duurt ongeveer 45 minuten, en de batterijen blijven op hun eigen firmware tot je weer *Full control* kiest. Stap voor stap: **[Overstappen van HBC](docs/gebruikershandleiding.nl.md#overstappen-van-hbc)**.

## Voordat je het gebruikt

- Alle HBC+-meldingen (Battery Oscillation Guard, heartbeat-fallback, foutmelding, ontbrekende prijzen, fasebewaking) gaan via `script.hbc_notify` in `packages/hbc_notify.yaml`. Stel één keer in waar ze heen gaan, bij *Notify targets* op de view *Settings* (bijvoorbeeld `notify.mobile_app_<telefoon>`; leeg = `notify.notify`), en druk op *Send a test notification*.
- Een Marstek via Modbus TCP werkt ook, zolang de entiteiten het patroon `marstek_mN_*` volgen.
- Raadpleeg altijd een erkend installateur over je installatie en de waarden van je zekeringen.

## Uitbrengen (beheerders)

Elk onderdeel van HBC+ heeft een eigen versie; `tools/` houdt ze kloppend. Eén keer per clone of worktree:
`git config core.hooksPath tools/hooks` (controleert vóór elke commit de versies en beide handleidingen).

1. **Zet de versie.** Minorrelease: `python3 tools/set-version.py X.Y.0` (elk onderdeel). Patchrelease:
   `python3 tools/set-version.py X.Y.Z <onderdeel> …` met alleen de onderdelen die veranderd zijn (`flows`,
   `dashboard`, of een packagebestand zoals `hbc_phase_guard`). Het schrijft ook `versions.json`.
2. **Schrijf de documentatie.** Een regel `## [X.Y.Z]` in `CHANGELOG.md`, en dezelfde wijziging in beide
   handleidingen (Engels en Nederlands); `python3 tools/check-docs.py` controleert of ze gelijk lopen.
3. **Controleer vóór je tagt.** `python3 tools/check-versions.py` en `python3 tools/release-files.py`: de tweede
   toont wat er sinds de laatste tag veranderd is en faalt als een gewijzigd onderdeel zijn versie hield.
4. **Merge via een pull request** naar `main`; de job *check* moet slagen (ruleset op `main`).
5. **Tag** `vX.Y.Z` op `main` en push de tag. De Action controleert opnieuw en maakt een **concept**-release met
   `hbc-plus-vX.Y.Z.zip`, `versions.json` en notes (de CHANGELOG-regel plus de bestanden om te kopiëren).
6. **Publiceer het concept** nadat je het gelezen hebt. Een patch voor een *oudere* lijn (een 1.2.x na 1.3.0): vink
   *Set as the latest release* uit, anders vergelijkt de update-check van Home Assistant met die.
7. **Na een merge tussen feature-branches** (bijvoorbeeld `main` naar `feature/v1.3`): los versieconflicten op in
   het voordeel van de eigen versie van de branch, en draai daarna `python3 tools/set-version.py <versie van de
   branch>` en `python3 tools/check-versions.py`.

**De update-check testen vóór een release:** push de branch met zijn `versions.json`, en zet in Home Assistant
`sensor.hbc_latest_version` op de naam van de branch (*Ontwikkelhulpmiddelen* → *Toestanden*, bijvoorbeeld
`feature/v1.3`). HBC+ haalt het manifest dan van die branch, en de Overview en de lijst *Versions* op de view
Settings tonen wat er verschilt. De volgende release-check (hooguit 6 uur, of een herstart) zet de sensor terug.

## Licentie

GPL-3.0. Zie [LICENSE](LICENSE). HBC+ is afgeleid van HBC v4.15.1 van CodeBob (GPL-3.0); alle wijzigingen staan beschreven in [docs/gebruikershandleiding.nl.md](docs/gebruikershandleiding.nl.md).
