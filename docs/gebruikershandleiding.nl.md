# HBC+ v1.0 — Gebruikershandleiding

*14 november 2026* · 🇬🇧 [English version](user-guide.en.md)

## Wat HBC+ is

HBC+ (Home Battery Control Plus) v1.0 stuurt tot zes thuisbatterijen aan vanuit Home Assistant en Node-RED, en laat twee batterijen één fase delen zonder de hoofdzekering van die fase te overbelasten. Met de phase guard op *Off* of *Monitor* worden de batterijen aangestuurd zonder faseregels; alleen *Enforce* past ze toe.

Naast de fasebewaking brengt HBC+ v1.0 verbeteringen op drie vlakken:

- **Veiligheid** — bewaking van de hoofdzekering per fase, fail-open-code die bij een fout terugvalt op aansturing zonder faseregels, een HA-alarm dat ook zonder Node-RED werkt, en een heartbeat die de batterijen teruggeeft aan hun firmware als de regellus stopt.
- **Performance** — één snelle leesnode in plaats van ~43 losse reads, PID-stap en Timed-periodekeuze samengevoegd met instellingencaches, en minder Modbus-writes per tick.
- **Stabiliteit** — bugfixes (o.a. totaal-helpers die na een herstart op 0 sprongen, een prijscache die na een bronwissel oude prijzen gebruikte, het debug board), totalen die nooit NaN naar HA sturen, en één consistente HA-servernode in alle flowbestanden.

Alle wijzigingen staan uitgewerkt in de sectie [Verbeteringen in HBC+ v1.0](#verbeteringen-in-hbc-v10) hieronder.

Wat de fasebewaking toevoegt:

- **Een fasekaart.** Elke batterij (M1–M6) hoort bij L1, L2, L3 of *Own circuit* (eigen groep).
- **Eén actieve batterij per fase** (standaard). De partner op die fase wacht op 1 W idle en stopt daarna, zoals HBC+ doet met batterijen die het niet nodig heeft.
- **Twee limieten per fase.** De actieve batterij krijgt alleen de ruimte die overblijft onder zowel de hoofdzekering (net), na de huislast op die fase, als de batterijgroep die de batterijen van die fase delen (standaard 16 A ≈ 3680 W elk), elke tick opnieuw berekend uit de P1-meter.
- **Juist plafond voor planners.** Het maximale vermogen dat HBC+ aan Charge Deadline en HELIOS doorgeeft is de som per fase, niet de som van alle batterijen. Zo plannen die genoeg laaduren.
- **Een Phases-dashboard** en een onafhankelijk overbelastingsalarm in Home Assistant dat ook werkt als Node-RED stilstaat.
- **Een optionele modus *Shared headroom*** waarin beide batterijen op een fase tegelijk mogen draaien, zolang ze samen onder de zekering blijven.

Netto-effect met twee batterijen per fase (6 × Marstek Venus E, elk 5,12 kWh): de bruikbare capaciteit verdubbelt tot ongeveer 30,7 kWh, het piekvermogen blijft 7,5 kW (3 × 2500 W).

Waarom de fasebewaking zo werkt, staat in [Achtergrond en ontwerpkeuzes](#achtergrond-en-ontwerpkeuzes).

### Credits

HBC+ is een zelfstandige versie met een eigen ontwikkeling. Het is begonnen vanuit House Battery Control (HBC) v4.15.1 van **CodeBob** ([gitcodebob](https://github.com/gitcodebob/marstek-venus-rs485-node-red)), de founding father van HBC: de oorspronkelijke regellus, strategieën, het dashboard en de helpers zijn zijn werk, en alle credits voor dat fundament gaan naar hem. HBC+ heeft verder geen link meer met HBC.

Dynamic en Charge Deadline gebruiken de macro [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) van **TheFes**.

## Architectuur

HBC+ bestaat uit drie delen: Home Assistant-packages met de instellingen en een onafhankelijk alarm, de Node-RED-regellus die de begrenzing uitvoert, en een dashboard dat per fase laat zien wat er gebeurt.

```mermaid
flowchart LR
  subgraph HA["Home Assistant"]
    M["Netmeter en batterijen<br/>P1 per fase · Marstek M1–M6"]
    P["hbc_phase_guard.yaml<br/>instellingen · fasekaart"]:::new
    T["Template-sensoren, alarm<br/>zekeringruimte per fase · alarm 10 s"]:::new
    Q["MQTT-statussensoren<br/>actieve batterij en reden per fase"]:::new
    D["Phases-view<br/>HBC+-dashboard"]:::new
    Q --> D
  end
  subgraph NR["Node-RED"]
    R["Read HA states (fast)"] --> B["Batteries (totals)"] --> PL["HBC+ phase planner"]:::new --> S["Strategy selection"] --> G["HBC+ phase guard"]:::new --> W["Set Batteries (Modbus)"]
    S --> ST["Strategieën<br/>Self-consumption · Charge · Sell · Timed · Dynamic"]
    PM["Phase monitor<br/>alleen-lezen · 5 s"]:::new
  end
  M -- leest --> R
  W -- stuurt --> M
  PM -- "MQTT hbc/phase/*" --> Q
  classDef new stroke-width:3px
```

*Dikke rand = fasebewaking.* De planner en guard draaien in *HBC+ Home Battery Start*, dus de begrenzing hangt nooit van een ander tabblad af. Het Phase monitor-tabblad rapporteert alleen; de template-sensoren en het overbelastingsalarm draaien in Home Assistant en blijven werken als Node-RED stilstaat.

## Functionaliteit

### De regellus

Bij elke update van `sensor.p1_meter_power` (met rate limit) draait *HBC+ Home Battery Start* één tick:

1. **Read HA states (fast)** leest alle batterijen (M1…M*n*, `input_number.house_battery_count`) en instellingen in één node uit de Home Assistant-states in de global context. Ontbreken die, dan valt het terug op de oorspronkelijke keten van current-state-nodes.
2. **Batteries (totals)** berekent totaal batterijvermogen, max laad-/ontlaadvermogen en bruikbare energie, en schrijft die naar de helpers `input_number.house_battery_total_*`. Een waarde die even onbeschikbaar is, wordt maximaal 5 min vastgehouden.
3. **Update battery order** roteert de batterijprioriteit.
4. **HBC+ phase planner** (nieuw) bepaalt per fase wie mag draaien en hoeveel ruimte er is.
5. **Strategy selection** roept het strategietabblad aan dat in `input_select.house_battery_strategy` staat. Dat geeft `msg.solutions` terug: één `{id, mode, power}` per batterij.
6. **HBC+ phase guard** (nieuw) controleert de solutions nog één keer.
7. **Write limiter → Set Batteries** schrijft per batterij eerst vermogen, dan modus, alleen als een waarde veranderde (awaited writes, 60 s keep-alive op de modus).
8. **HBC+ heartbeat** publiceert de tijd naar MQTT `hbc/heartbeat`, hooguit eens per minuut. Stopt die, dan geeft Home Assistant de batterijen terug aan hun firmware (zie F4).

### Guard-modi

`input_select.house_battery_phase_guard_mode` bepaalt of de faseregels iets doen.

| Modus | Wat HBC+ doet | Gebruik het voor |
| --- | --- | --- |
| Off | Planner en guard laten elk bericht ongemoeid door: geen faseregels. | Eén batterij per fase, of om HBC+ uit te sluiten bij debuggen |
| Monitor (standaard) | Berekent en publiceert wat het *zou* doen; de nodestatus toont `would: …`. Verandert niets. | In bedrijf nemen; de koppeling testen voordat batterijen een fase delen |
| Enforce | Past de faseregels toe in de planner, de strategieën, de guard en de master switch. | Normaal gebruik met twee batterijen op een fase |

Elke gewijzigde node is getest tegen het origineel met dezelfde invoer: Off en Monitor geven identieke uitvoer.

### Faseregels (Enforce)

1. **Fasekaart.** Elke batterij heeft een fase uit `input_select.marstek_mN_phase`: L1, L2, L3 of *Own circuit* (nooit gedeeld, geen faseregel).
2. **Eén actieve batterij per gedeelde fase.** De andere krijgen het idle-setpoint van 1 W (relais blijft in) en stoppen na de normale idle-tijd. Dit is hetzelfde soft-stop-pad dat HBC+ gebruikt voor batterijen die het niet nodig heeft.
3. **Ruimte per fase.** Huisnetto op een fase = P1-fasevermogen min batterijvermogen op die fase (import positief). Laadruimte = min(netzekering − marge − huisnetto, batterijgroep − marge); ontlaadruimte = min(netzekering − marge + huisnetto, batterijgroep − marge). De netzekering draagt huis en batterijen samen; de batterijgroep alleen de batterijen. Beide ruimtes zijn ook begrensd op het eigen maximum van de batterij en worden elke tick opnieuw berekend.
4. **Selectie.** Kandidaten zijn de batterijen op die fase met RS485 `enable`, verse waarden, en SoC boven het minimum (ontladen) of onder het maximum (laden).
   - *SoC balance* (standaard): ontladen uit de volste, laden in de leegste. De huidige batterij blijft actief tot het SoC-verschil de wisseldelta (5 %) bereikt **en** hij de minimale verblijftijd (15 min) heeft gedraaid. Bij een richtingswissel mag direct opnieuw gekozen worden.
   - *Fixed order*: laagste M-nummer eerst, de partner alleen als reserve.
   - *Rotate daily*: de primaire batterij wisselt om middernacht.
5. **Break-before-make-overdracht.** De oude batterij gaat eerst naar idle; de nieuwe wordt pas vrijgegeven als de oude onder 100 W meet. Ontbreekt de teruglezing van de oude batterij of is die verouderd, dan blijft de partner geblokkeerd: een Marstek die Modbus kwijt is, kan nog zijn laatste opdracht uitvoeren.
6. **Laatste controle.** Vlak voor het schrijven corrigeert de guard elke fase met meer dan één actieve batterij of een setpoint boven de zekeringruimte, en logt dat. Dit vangt ook toekomstige strategieën op die de regels negeren.

Voorbeeld: met netzekering en batterijgroep allebei op 3680 W en 1800 W huislast op L1 mag de actieve L1-batterij laden met 3680 − 200 − 1800 = 1680 W; met 3000 W PV-teruglevering op L1 mag hij maar 480 W ontladen. Met een netzekering van 7360 W laat dezelfde 1800 W nog 5360 W onder de netzekering over, dus beslist de batterijgroep: 3680 − 200 = 3480 W.

### Shared headroom (optie)

Met `input_select.house_battery_phase_sharing` = *Shared headroom* mogen beide batterijen op een fase tegelijk draaien, zolang ze samen binnen de zekeringruimte blijven. Regels 1, 3 en 6 blijven; regels 2 en 5 worden vervangen door:

- **Vulvolgorde** volgt de selectieregel: de eerste batterij krijgt min(eigen max, ruimte), de partner krijgt wat over is, tot zijn eigen max.
- **Minimaal aandeel:** de partner start pas als er minstens 300 W over is en stopt weer onder 100 W.
- **Onbekend telt als bezig:** een batterij met een verouderde teruglezing telt mee met zijn laatste setpoint.

Typische winst: 2500 + 1000 W laden op een fase zonder huislast. De fallback als HBC+ stilstaat geeft nog steeds maar één batterij per fase terug aan de firmware.

### Wat er per strategie verandert

| Tabblad | HBC+-wijziging (alleen Enforce) |
| --- | --- |
| Home Battery Start | Nieuwe *phase planner* en *phase guard*; *Batteries (totals)* telt max vermogen per fase |
| Self-consumption | *Load distribution* soft-stopt standby-batterijen en begrenst elke fase op zijn zekeringruimte; anti-windup gebruikt de begrensde capaciteit |
| Charge, Sell | *Max power solution* laat alleen de actieve batterij per fase draaien, op min(eigen max, zekeringruimte); de partner staat idle op 1 W |
| Master Switch | Bij teruggave aan de firmware krijgt alleen het laagste M-nummer op een gedeelde fase RS485 *disable*; de partner blijft RS485 *enable* + forcible *stop* |
| Charge Deadline, Helios | Logica ongewijzigd; ze plannen met het max vermogen per fase uit *Batteries (totals)* |
| Partials, Timed, Dynamic (prijsophaling: zie hieronder), Full stop, PID presets, Oscillation Guard, Strategy arbiter | Geen wijziging; wat ze uitvoeren gaat via Self-consumption of Max power, die de regels toepassen |
| Phase monitor | **Nieuw**, alleen-lezen: publiceert `hbc/phase/*` voor het dashboard elke 5 s (opnieuw bij wijziging, anders hooguit elke 30 s) |

### Gedeelde prijsophaling (Dynamic)

De sectie *API call to Data Source* van *HBC+ Strategy Dynamic* is een link-call-subroutine, zodat elke flow de actuele prijslijst kan ophalen zonder eigen kopie van de databronlogica. Binnen het Dynamic-tabblad roept *Cache check* hem aan bij een cache miss; de prijzen komen terug en gaan door naar *Determine strategy*, net als bij een cache hit.

Gebruik hem vanuit een andere flow met een **link call**-node: kies *Dynamic Fetch from Data Source* en stel een timeout van minstens 30 s in. De eerste node van de sectie, *Prepare request*, vult aan wat de aanroeper weglaat.

| msg-property | In / uit | Betekenis |
| --- | --- | --- |
| `dynamic.data_source` | in, optioneel | Prijsbron; standaard = `input_select.house_battery_strategy_dynamic_data_source` |
| `dynamic_use_cache` | in, optioneel | `true` = geef de gecachte prijzen van het Dynamic-tabblad terug als ze nog geldig zijn (zelfde regel als *Cache check*: na 13:00 moeten ze morgen dekken), anders ophalen |
| `dynamic` | uit | `{data_source, data_all: {list, list_marked, average, min, max, start, …}, no_data?}` |
| `dynamic_from_cache` | uit | `true` als de cache antwoordde |

- Bron *None*, of een bron die Node-RED niet kan lezen, komt direct terug met `dynamic.no_data = true` en een lege lijst, zodat de aanroeper nooit op de timeout wacht.
- Een geslaagde ophaling vanuit elke aanroeper ververst ook de cache van het Dynamic-tabblad.
- De rest van het bericht van de aanroeper komt ongewijzigd terug (`msg.template` wordt gebruikt en verwijderd).
- Mislukt een ophaling binnen de sectie, dan loopt de link call na 30 s in een timeout; de fout gaat naar *Strategy errors* in het Dynamic-tabblad.
- Levert een ophaling geen prijzen, dan komt de laatste geldige lijst van dezelfde bron terug met `dynamic.stale = true` zolang die het huidige interval nog dekt, anders `dynamic.no_data = true` (zie R3).

### Effect op planners

Omdat *Batteries (totals)* het effectieve maximum in de bestaande helpers schrijft, hebben Charge Deadline, HELIOS en de PID-anti-windup geen codewijziging nodig.

| Waarde | 3 batterijen (nu) | 6 batterijen, geen faseregel | 6 batterijen, Enforce |
| --- | --- | --- | --- |
| `house_battery_total_max_charge_power` | 7500 W | 15000 W | 7500 W |
| Bruikbare energie | ~15,4 kWh | ~30,7 kWh | ~30,7 kWh |
| Uren om 0→100 % te laden op max | ~2 u | ~2 u (maar zekering springt) | ~4 u |

De plannerwaarde volgt de zekeringruimte. Op *Enforce* trekt *Batteries (totals)* de gemiddelde huislast per fase (exponentieel gemiddelde over ongeveer 15 minuten) af van de zekeringruimte, rondt af op 100 W en past de waarde alleen aan als die 250 W of meer verschuift. Een warmtepomp die een half uur draait verlaagt de plannerwaarde; een waterkoker van een paar seconden niet. Voorbeeld: met een uur lang 2 kW huislast op L1 zakt het laadplafond naar ongeveer 6200 W in plaats van 7500 W, zodat Charge Deadline extra goedkope kwartieren boekt. Stopt de last, dan is de waarde binnen ongeveer 15 minuten terug.

### Ingebouwde veiligheid

- **Fail-open.** Planner, guard en totalen draaien in try/catch. Bij een fout waarschuwen ze en geven het bericht ongewijzigd door, dus aansturing zonder faseregels.
- **Geen afhankelijkheid van andere tabbladen** in de regellus: planner en guard zitten in *Home Battery Start*. Het Phase monitor-tabblad uitschakelen verandert niets.
- **Onafhankelijke alarmen.** `binary_sensor.hbc_phase_limit_exceeded` gaat aan als het netvermogen op een fase 10 s boven de netzekering ligt; `binary_sensor.hbc_phase_circuit_limit_exceeded` als de batterijen op een fase 10 s meer trekken dan de batterijgroep. Beide zijn puur Home Assistant en werken ook als Node-RED stilstaat.

## Strategieën en instellingen

Deze sectie legt uit wat elke strategie doet en met welke instellingen je hem stuurt. De ⓘ-links in het dashboard wijzen hierheen.

### Mastermodus

`input_select.marstek_master_battery_mode` bepaalt wie de Marsteks aanstuurt. HBC+ stuurt de batterijen alleen in **Full control**.

| Mastermodus | RS485-besturing | Wie stuurt |
| --- | --- | --- |
| Full control | enable | HBC+ (forcible charge / discharge) |
| Marstek control | disable | De Marstek-firmware, in de werkmodus die je in de Marstek-app koos |
| Manual control | disable | De Marstek-firmware, handmatige modus |

### Een strategie kiezen

Kies de strategie in `input_select.house_battery_strategy`. De *Strategy arbiter* is de enige die die helper schrijft: de Battery Oscillation Guard, en eigen flows (bijvoorbeeld een PV-limiter), kunnen tijdelijk een andere strategie vasthouden en geven je keuze daarna terug (zie *Installatie*, stap 3).

| Strategie | Wat het doet |
| --- | --- |
| Self-consumption | Houdt het netvermogen op 0 W door te laden uit PV-overschot en te ontladen naar het huisverbruik (PID-regeling) |
| Charge PV | Self-consumption zonder ontladen: laadt alleen uit PV-overschot |
| Zero import | Self-consumption zonder laden: ontlaadt om de netafname op 0 W te houden |
| Standby / peak shave | Batterijen staan stil (geen relaisklikken); met peak shaving aan grijpen ze toch in boven de netgrenzen |
| Charge | Laadt van het net tot een doel, en schakelt dan over |
| Sell | Ontlaadt naar het net tot een doel, en schakelt dan over |
| Charge Deadline | Laadt tot een doel vóór een deadline, in de goedkoopste kwartieren |
| Timed | Een andere strategie per tijdvak (A t/m E) |
| Dynamic | Een andere strategie voor goedkope, dure en normale prijsperiodes |
| Helios | Voert de beslissing van de HELIOS-optimizer uit (pyscript, optioneel) |
| Full stop | Alle batterijen op stop, 0 W; het relais gaat open, dus geen sluimerverbruik |

**EV-stoptrigger.** Zet het entity-id van een "EV laadt"-sensor of -boolean in `input_text.house_battery_strategy_ev_sensor_entity_id`. Zolang die `on` is, draait HBC+ de strategie uit `input_select.house_battery_strategy_ev_stop_trigger_strategy` (*Full stop* of *Standby / peak shave*), zodat de batterijen niet in de auto ontladen.

### Self-consumption en PID-afstelling

Self-consumption is de PID-regelaar van HBC+, en de meeste andere strategieën laten hem het eigenlijke werk doen. Elke tick neemt hij het verschil tussen netvermogen en doel (standaard 0 W), negeert verschillen onder 15 W, en berekent een batterijvermogen uit drie termen:

- **P (Kp)** reageert op het verschil van nu;
- **I (Ki)** werkt het verschil weg dat over tijd blijft staan;
- **D (Kd)** dempt snelle veranderingen.

*Load distribution* verdeelt dat vermogen daarna over de batterijen in volgorde van prioriteit, elk tot zijn eigen maximum. Bijna vol wordt het laden beperkt tot 1500 W vanaf 95 % en 1000 W vanaf 99 %.

Afstellen gaat het makkelijkst met een preset in `input_select.house_battery_control_pid_presets`:

| Preset | Kp | Ki | Kd | Ingangsdemping | Uitgangsdemping | Wanneer |
| --- | --- | --- | --- | --- | --- | --- |
| Very safe | 0.1 | 0.1 | 0 | 0 % | 10 % | Een systeem dat met elke andere preset gaat slingeren |
| Safe | 0.3 | 0.3 | 0.1 | 20 % | 0 % | Goed startpunt voor de meesten |
| Regular | 0.3 | 0.4 | 0.8 | 50 % | 10 % | Snellere reactie; vraagt een stabiele meter |
| Custom | — | — | — | — | — | Je eigen waarden in de PID-helpers |

Begin met *Safe*. Slingert het netvermogen heen en weer rond 0 W, dan is de regeling te scherp: ga een preset omlaag, of verlaag Kp en Ki. Komt het na een belastingsstap traag terug naar 0 W, dan is hij te zacht: ga een preset omhoog. Verander één ding tegelijk en kijk een paar minuten. De *Battery Oscillation Guard* zet de batterijen stil als ze toch gaan slingeren.

Andere instellingen in de Self-consumption-view:

- **Hysterese** (`input_number.house_battery_control_hysteresis_in_w`, 0–200 W): de PID-uitgang moet dit voorbij voordat de batterijen wisselen tussen laden en ontladen.
- **Fout- en uitgangsdemping** (`…_error_signal_dampening`, `…_pid_output_dampening`, 0–90 %): voortschrijdende gemiddelden op in- en uitgang; meer demping is rustiger maar trager.

### Charge en Sell

**Charge** laadt van het net tot het doel in `input_select.house_battery_strategy_charge_goal` bereikt is:

| Doel | Bereikt als |
| --- | --- |
| batteries are full | Elke batterij op zijn maximale SoC staat |
| state of charge | De gemiddelde SoC `input_number.house_battery_strategy_charge_target_soc` bereikt |
| energy reserve | De bruikbare energie `input_number.house_battery_strategy_charge_target_energy` bereikt |
| solar forecast | De bruikbare energie het maximum min het verwachte PV-overschot van vandaag bereikt (de verwachting min `input_number.house_battery_solar_reserved_for_house`) |

**Sell** ontlaadt naar het net tot `input_select.house_battery_strategy_sell_goal` bereikt is: *batteries are empty*, *state of charge* (`…_sell_target_soc`) of *energy reserve* (`…_sell_target_energy`).

Is het doel bereikt, dan draait de strategie bij *Then use* (`…_charge_goal_reached` / `…_sell_goal_reached`, standaard *Charge PV*).

**Vermogen.** Zonder netgrens laadt of ontlaadt elke batterij op zijn maximum. Staat peak shaving voor afname (Charge) of teruglevering (Sell) aan, dan regelt HBC+ in plaats daarvan op die netgrens (zie *Geavanceerde instellingen*). Op *Enforce* draait per gedeelde fase alleen de actieve batterij, binnen de zekeringruimte van die fase.

**Zonneverwachting.** Voor het doel *solar forecast* zet je de entity-id's van je verwachtingssensoren (kWh vandaag en kWh morgen, bijvoorbeeld van Forecast.Solar of Solcast) in `input_text.house_battery_strategy_solar_forecast_entity_id` en `…_solar_forecast_tomorrow_entity_id`. Zet `input_number.house_battery_solar_reserved_for_house` op wat het huis op een gewone dag zelf van de PV gebruikt.

### Charge Deadline

Laadt tot een doel vóór een deadline (`input_datetime.house_battery_deadline_start` / `_end`). Het doel staat in `input_select.house_battery_deadline_goal`: *batteries are full*, *state of charge* of *energy reserve*. Het kiest bij voorkeur de goedkoopste kwartieren uit de Dynamic-prijslijst, en doseert het vermogen naar prijs (`input_number.house_battery_deadline_price_ratio`: hoeveel harder het goedkoopste kwartier laadt dan het duurste dat het gebruikt). Het rekent ook op verwachte PV als `input_boolean.house_battery_deadline_reserve_pv` aan staat, en houdt het doel vast tot de deadline als `…_hold_after_target` aan staat. Na de deadline draait de strategie bij *Then use* (`input_select.house_battery_deadline_reached`). De planning wordt elke tick opnieuw berekend uit de resterende energie en tijd. Het heeft een werkende prijsbron nodig (zie *Dynamic*).

### Timed

Draait een andere strategie per tijdvak. Tijdvak A staat altijd aan; B t/m E zet je één voor één aan (`input_boolean.house_battery_strategy_timed_has_period_b` … `_e`). Elk tijdvak heeft een start, een einde (`input_datetime.house_battery_strategy_timed_period_a1` / `_a2` …) en een strategie (`input_select.house_battery_strategy_timed_strat_a` …). Het eerste ingeschakelde tijdvak waar de huidige tijd in valt, wint; een tijdvak met een einde vóór de start loopt door over middernacht. Buiten alle tijdvakken draait de basisstrategie (`…_timed_strat_0`). Het actieve tijdvak staat in `input_text.house_battery_strategy_timed_period_selected`.

### Dynamic

Kiest een strategie op basis van de energieprijzen van vandaag en morgen.

**Instellen.**

1. Installeer de macro [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours) (HACS).
2. Installeer een prijsintegratie en kies die bij **Tariff data source** (`input_select.house_battery_strategy_dynamic_data_source`).
3. Heb je meer dan één prijsintegratie, leg de sensor dan vast in `input_text.house_battery_strategy_dynamic_price_sensor` (zie R4).
4. Controleer de grafiek *Price intervals* in de Timed/Dynamic-view.

**Hoe het beslist.** Per dag koppelt HBC+ de goedkoopste en de duurste intervallen, van de uitersten naar binnen. Een paar telt alleen mee als het prijsverschil minstens **Minimum spread** is (`input_number.house_battery_strategy_dynamic_threshold_delta`, in centen). Zet die zo dat hij je laad-/ontlaadverliezen dekt. **Cheapest hours** en **Expensive hours** begrenzen het aantal gemarkeerde uren per dag (0 = geen grens). Het huidige interval bepaalt dan de strategie:

| Interval | Strategie (helper) | Keuzes |
| --- | --- | --- |
| Goedkoop | `…_dynamic_cheapest` | Charge, Charge PV, Charge Deadline, Standby / peak shave |
| Duur | `…_dynamic_expensive` | Self-consumption, Sell, Zero import, Standby / peak shave |
| Normaal | `…_dynamic_default` (*Default to*) | Charge PV, Self-consumption, Zero import, Standby / peak shave, Full stop |

De prijzen worden ververst om middernacht, om 13:15 en 15:00, na een bronwissel, en tot de prijzen van morgen binnen zijn. Valt de bron uit, dan houdt Dynamic de laatste geldige prijzen aan of valt terug op *Default to* (zie R3). Andere flows kunnen dezelfde prijzen ophalen via de link call (zie *Gedeelde prijsophaling*).

### Geavanceerde instellingen

- **Batterijprioriteit** (`input_select.house_battery_control_priority_change_interval`): Self-consumption gebruikt de batterijen in volgorde van prioriteit, te beginnen met `input_number.house_battery_control_prioritize_battery`. De prioriteit schuift door naar de volgende batterij elke 30 minuten (*Auto balance*), dagelijks om 02:00 (*Daily*), op zondag om 02:00 (*Weekly*), of helemaal niet (*Never*). Behalve bij *Auto balance* ontlaadt HBC+ in omgekeerde volgorde, zodat de batterij die als eerste laadt als laatste ontlaadt.
- **Stop na stilstand** (`input_number.house_battery_control_idle_time`, 0–60 min): een batterij die niet nodig is houdt zo lang 1 W (relais dicht) voordat hij *stop* krijgt. Dat scheelt relaisklikken als het verbruik op en neer gaat.
- **Peak shaving** (`input_boolean.house_battery_control_has_power_limit_import` / `_export` met `input_number.house_battery_control_power_limit_import` / `_export`): de batterijen houden netafname of teruglevering onder de grens, bijvoorbeeld voor een capaciteitstarief. Charge en Sell regelen op deze grenzen in plaats van op vol vermogen.
- **Cutoff-capaciteiten** (`input_number.marstek_mN_charging_cutoff_capacity` 80–100 %, `…_discharging_cutoff_capacity` 11–80 %): de SoC-grenzen die naar elke Marstek geschreven worden. HBC+ behandelt een batterij op zijn grens als vol of leeg.

## Achtergrond en ontwerpkeuzes

### Waarom fasebewaking nodig is

Zonder fasebewaking kent de regeling geen fasen. Dat ging alleen goed zolang M1, M2 en M3 elk op een eigen fase zaten. *Max power solution* (Charge, Sell en HELIOS Charge/Sell) zet elke batterij op zijn maximum, en *Load distribution* (Self-consumption) vult de batterijen in prioriteitsvolgorde, elk tot zijn eigen maximum. Met twee Marsteks op L1 komt er dan 2 × 2500 = 5000 W op die fase, ruim boven een zekering van 16 A (3680 W).

Daarnaast zou het plannerplafond de som van alle batterijen zijn (6 × 2500 = 15000 W) in plaats van wat er per fase echt kan (3 × 2500 = 7500 W). Charge Deadline zou dan maar de helft van de benodigde goedkope kwartieren boeken. En de heartbeat-fallback zou bij een storing elke batterij in firmware-anti-feed zetten, waarna twee batterijen op één fase elk 2500 W kunnen leveren.

### Randgevallen

| Situatie | Gedrag |
| --- | --- |
| HBC+ stilgevallen (heartbeat verouderd) | Per gedeelde fase gaat alleen de batterij met het laagste M-nummer naar firmware-anti-feed. De partner blijft RS485 *enable* + forcible *stop* en doet dus niets, ook niet als Node-RED of HA uitvalt. |
| Actieve batterij RS485 uit, offline of op zijn SoC-limiet | De partner neemt direct over (zonder verblijftijd), na break-before-make. |
| Actieve batterij onbereikbaar terwijl hij draaide | De partner blijft geblokkeerd, want de oude batterij kan nog zijn laatste opdracht uitvoeren. De fase staat stil en er gaat een melding uit. |
| Grote last schakelt in terwijl de fase op vol vermogen laadt | De zekering zit kort boven 16 A tot de volgende tick plus de reactietijd van de Marstek (enkele seconden). Zekeringen verdragen dat; de marge dekt meetfouten, geen grote stappen. Duurt het 10 s, dan gaat het alarm af. |
| Beide batterijen op een fase vol of leeg | De fase staat stil; de andere fasen merken niets. |
| Een strategie geeft twee actieve batterijen op een fase | De phase guard corrigeert het en logt het (regel 6). |
| Iemand wijzigt een batterij in de Marstek-app | De teruglezing wijkt af van het setpoint; *Set Batteries* schrijft opnieuw; het HA-alarm vangt een overbelasting binnen 10 s. |
| Guard-modus *Off* | Geen faseregels; alleen veilig met één batterij per fase. |

### Ontwerpkeuzes

- **Limieten:** een netzekering en een batterijgroep per fase, elk gelijk voor L1–L3 (standaard 16 A, 3680 W). De netruimte volgt de huislast op die fase; de batterijgroep telt alleen de batterijen.
- **Eén batterij per fase is de standaard.** *Shared headroom* (beide tegelijk binnen de zekeringruimte) is een optie in de instellingen.
- **Uitbreiding met drie Marsteks (M4–M6).** Standaard fasekaart M1/M4 L1, M2/M5 L2, M3/M6 L3, per batterij aan te passen.
- **Veiligheid boven snelheid.** De overdracht is break-before-make, en een batterij zonder verse teruglezing telt als bezig.
- **Fail-open.** Elke nieuwe stap valt bij een fout terug op aansturing zonder faseregels; het HA-alarm werkt los van Node-RED.
- **Tekens:** batterijvermogen is positief bij laden, P1-fasevermogen is positief bij import.
- **Eerst Monitor.** De fasebewaking kan al draaien met één batterij per fase; dan verandert er niets en test je de koppeling gratis, voordat er een tweede batterij op een fase komt.

## Verbeteringen in HBC+ v1.0

Naast de fasebewaking bevat HBC+ v1.0 de wijzigingen hieronder. Acht lossen bugs op, vier maken het systeem robuuster, vier maken de regellus sneller of schrijven minder naar Modbus, en vijf zijn features. Alles draait in de praktijk op een opstelling met drie batterijen (twee via RS485, één via Modbus TCP).

| # | Wijziging | Waar | Type |
| --- | --- | --- | --- |
| B1 | Geen `initial: 0` op de vijf totaal-helpers | `house_battery_control.yaml` | Bugfix |
| B2 | Batterijvermogen-template leest het echte entity-id | `house_battery_control.yaml` | Bugfix |
| B3 | Dynamic-prijscache gekoppeld aan de databron | Dynamic – *Cache check* | Bugfix |
| B4 | Dynamic-cache haalt opnieuw op tot morgen binnen is | Dynamic – *Cache check* | Bugfix |
| B5 | "Nu"-balk in prijsgrafiek op basis van start/eind | Dashboard | Bugfix |
| B6 | Prijsgrafiek tekent opnieuw bij een bronwissel | Dashboard + template-sensor | Bugfix |
| B7 | Debug board toont weer de trace | Start – *Set Batteries* | Bugfix |
| B8 | Dynamic *User input* luistert naar de sub-strategiekeuzes | Dynamic – *User input* | Bugfix |
| R1 | *Batteries (totals)* stuurt nooit NaN naar HA | Start – *Batteries (totals)* | Robuustheid |
| R2 | Eén consistente HA-servernode in elk bestand | Alle flows | Robuustheid |
| R3 | Mislukte prijsophaling: laatste geldige prijzen blijven, terugval op basisstrategie, melding | Dynamic + `house_battery_control.yaml` + dashboard | Robuustheid |
| R4 | Prijssensor vast te leggen | Dynamic – *Data source settings* + helper | Robuustheid |
| P1 | *Read HA states (fast)*: één node in plaats van ~43 reads | Start | Performance |
| P2 | *PID step*: 13 nodes in één, cache voor PID-instellingen | Self-consumption | Performance |
| P3 | *Pick period*: snel pad voor Timed met instellingencache | Timed | Performance |
| P4 | Minder Modbus-writes, per batterij op volgorde | Start – *Set Batteries* | Performance |
| F1 | Feed-forward-start voor geregeld laden | Charge – *Regulated power* | Feature |
| F2 | Grid Clock als Dynamic-databron | Dynamic + selector | Feature |
| F3 | Charge Deadline-strategie | Eigen tabblad + package | Feature |
| F4 | Heartbeat van de regellus met fallback in HA | Start + package | Feature |
| F5 | Recorder-uitsluitingen voor drukke entiteiten | Packages | Onderhoud |
| E1–E4 | Strategy arbiter, Battery Oscillation Guard, Modbus TCP-batterij, P1-alias | Eigen tabbladen en packages | Uitbreiding |

### Bugfixes

**B1 — Totaal-helpers sprongen na een HA-herstart terug naar 0.**

- *Probleem:* de vijf totaal-helpers (`house_battery_total_available_energy`, `_max_available_energy`, `_battery_power`, `_max_charge_power`, `_max_discharge_power`) hadden `initial: 0`. HA past `initial` bij elke herstart opnieuw toe. De flow schrijft deze waarden via een *on change*-filter, dus statische waarden zoals de maximale energie werden nooit opnieuw geschreven en bleven op 0 staan. Alles wat erdoor deelt ging stuk; *Required average power to deadline* gaf bijvoorbeeld 0 W.
- *Oplossing:* `initial:` is weggehaald uit die vijf helpers, met een commentaar waarom. `house_target_grid_consumption_in_w` houdt zijn `initial: 0`.

**B2 — Batterijvermogen-template las een entiteit die niet bestaat.**

- *Probleem:* een template las `sensor.house_total_battery_power_in_w`, maar het entity-id komt van de `name:` van de sensor (*House total battery power*) en is dus `sensor.house_total_battery_power`. De `unique_id` bepaalt het entity-id niet, dus de template las altijd `unknown`.
- *Oplossing:* de template probeert beide id's en gebruikt de eerste die een waarde heeft.

**B3 — Na een bronwissel bleven de oude prijzen in gebruik.**

- *Probleem:* *Cache check* in Dynamic zag elke gecachte prijslijst als geldig, ongeacht de bron. Na het wisselen van *Tariff data source* werden de prijzen van de oude bron gebruikt tot de volgende geplande leegmaak (00:01, 13:15 of 15:00), terwijl het dashboard al de nieuwe bron toonde.
- *Oplossing:* *Cache data source* slaat `data_source` op bij de gecachte data; *Cache check* vergelijkt die met `msg.dynamic.data_source` en gooit de cache weg als ze verschillen.

**B4 — Geen prijzen voor morgen tot 15:01.**

- *Probleem:* een lijst die om 13:16 was opgehaald, vóór publicatie van de day-ahead-prijzen, werd hergebruikt tot de leegmaak van 15:01 of 00:01. De Timed- en Dynamic-weergaven toonden dan geen prijzen voor morgen, hoewel de bron ze al had.
- *Oplossing:* na 13:00 telt *Cache check* de cache alleen als hit als `data_all.start + data_all.hours` voorbij middernacht reikt. Anders haalt hij bij elke run opnieuw op tot morgen binnen is. De nodestatus toont dan *Waiting for tomorrow (bron)*.

**B5 — De "nu"-balk bleef op een oud interval hangen.**

- *Probleem:* de prijsgrafiek kleurde het huidige interval op basis van de opgeslagen vlag `is_now`, die maar zo vers is als de laatste sensorupdate.
- *Oplossing:* de `data_generator` van de grafiek vergelijkt bij het tekenen `start` en `end` van elk interval met `Date.now()`; de markering volgt de klok.

**B6 — De prijsgrafiek tekende niet opnieuw bij een bronwissel.**

- *Probleem:* met `update_interval` ingesteld stopt apexcharts-card met hertekenen bij statuswijzigingen. De prijzen van een nieuwe bron verschenen pas na een browser-refresh.
- *Oplossing:* `update_interval` is weg uit de kaart *Price intervals*, en de trigger-sensor `update_energy_prices` heeft een attribuut `updated: "{{ now().isoformat() }}"` dat elke keer verandert. De kaart tekent dan opnieuw bij een bronwissel en bij elke Dynamic-run van 15 minuten; de "nu"-balk beweegt mee. De sensor is uitgesloten van de recorder (F5), dus dit geeft geen extra databaseregels.

**B7 — Het debug board toonde een setpoint in plaats van de trace.**

- *Probleem:* het awaited-write-pad stuurt het laatste schrijfbericht door naar het debug board. *Show on debug board* behandelt `msg.payload.data` als override voor zijn eventdata, dus HA kreeg het laatste setpoint (bijvoorbeeld `{value: 1733}`) in plaats van de trace en het log.
- *Oplossing:* de schrijfberichten dragen de `strategy.trace` en `log` van de cyclus mee, en achtergebleven `payload.data` wordt vóór de board-update verwijderd.

**B8 — Een Dynamic-sub-strategie wijzigen duurde tot 15 minuten.**

- *Probleem:* de Dynamic-trigger *User input* luisterde niet naar de drie sub-strategiekeuzes. Een wijziging in *Default to*, *Cheap periods* of *Expensive periods* werkte pas bij de volgende run van 15 minuten.
- *Oplossing:* `input_select.house_battery_strategy_dynamic_default`, `_cheapest` en `_expensive` staan nu in de entiteitenlijst van die trigger; een wijziging werkt binnen een paar seconden (prijzen komen uit de cache).

### Robuustheid

**R1 — Eén onbeschikbare batterijwaarde brak de totalen.**

- *Probleem:* *Batteries (totals)* telde `Number(battery.x)` op voor elke batterij. Was één entiteit `unavailable` of `unknown` (herverbinden, Modbus-hapering, HA-herstart), dan werd het totaal NaN. Dat kwam bij HA aan als `null` en gaf bij elke cyclus `HomeAssistantError: expected float at 'value'`; strategieën die met deze totalen vergelijken kregen ook NaN, en vergelijkingen met NaN zijn altijd false.
- *Oplossing:* een bewaking per batterij en per waarde. Een geldig getal wordt gebruikt en onthouden; een ontbrekende waarde gebruikt maximaal 5 minuten de laatste goede; daarna telt de batterij als 0, want een offline batterij levert niets. `msg.batteries` zelf blijft ongewijzigd. De nodestatus is groen als alles OK is, geel zolang een waarde wordt vastgehouden en rood zodra een batterij als 0 telt. Met geldige data geeft dit exact dezelfde totalen als voorheen (14 testgevallen).

**R2 — De HA-servernode verschilde per bestand.**

- *Probleem:* elk flowbestand heeft een eigen kopie van servernode `176d29a.6f648d6`, en het laatst geïmporteerde bestand overschrijft de live node. Zo kon het importeren van één strategiebestand heartbeat en connection delay uitzetten.
- *Oplossing:* elk HBC+-bestand bevat dezelfde servernode (*HA System*) met *Expose to global context* aan (nodig voor P1), heartbeat (30 s) en connection delay aan.

**R3 — Een mislukte prijsophaling bleef onopgemerkt en hield de laatste strategie aan.**

- *Probleem:* leverde de tariefbron geen prijzen, dan gooide *Cache data source* de gecachte lijst weg, kwam *Determine dynamic strategy* zonder nieuwe beslissing terug, en bleef Dynamic draaien wat het het laatst koos, ook *Charge* van het net. Niets meldde dat.
- *Oplossing:* drie lagen.
  - *Laatste geldige prijzen blijven:* mislukt een ophaling terwijl de gecachte lijst van dezelfde bron is en het huidige interval nog dekt, dan geeft *Cache data source* die lijst door (`dynamic.stale = true`) en bewaart hem; de volgende run probeert de bron opnieuw.
  - *Terugval:* zijn er helemaal geen geldige prijzen, dan draait Dynamic zijn basisstrategie (*Default to*) in plaats van de laatste.
  - *Melding:* `sensor.hbc_energy_prices_data` heeft een attribuut `status` (`ok`, `stale`, `no_data`). `binary_sensor.hbc_price_data_missing` gaat aan bij `no_data`; het dashboard toont een waarschuwing, en na 30 minuten maakt de automatisering *HBC+: alert when the tariff source delivers no prices* een persistente melding en roept `notify.notify` aan. De melding verdwijnt zodra er weer prijzen zijn.

**R4 — De prijssensor kon verkeerd geraden worden.**

- *Probleem:* voor EasyEnergy/EnergyZero, ENTSO-E, GE-Spot, Tibber en Nordpool (custom), Amber, Octopus, PVPC en Omie noemt *Data source settings* geen sensor, dus raadt de Cheapest Energy Hours-macro hem zelf. Met twee prijsintegraties kan hij de verkeerde kiezen.
- *Oplossing:* de optionele helper `input_text.house_battery_strategy_dynamic_price_sensor` (in te stellen via *Instellingen* → *Apparaten & diensten* → *Helpers*) legt de sensor vast, bijvoorbeeld `sensor.nordpool_kwh_nl_eur_3_10_021`. Hij overschrijft ook de ingebouwde sensor voor Nordpool en Tibber (core) en Frank Energie. Bronnen die hun eigen lijst doorgeven (Zonneplan, Grid Clock) negeren hem. De status van *Data source settings* toont welke sensor gebruikt wordt, *auto-detected*, of *not found* als de entiteit niet bestaat.

### Performance

Op een drukke Node-RED gaat elke extra node-hop opnieuw door de berichtenwachtrij, en de Start-flow overschreed regelmatig zijn link-call-timeout van 1 s. Elke wijziging hieronder behoudt de oorspronkelijke logica en uitvoer, en valt terug op de oorspronkelijke nodes als het snelle pad niet kan draaien.

**P1 — Read HA states (fast).** Was: ongeveer 43 *current state*-nodes achter elkaar (10 per batterij + 13 instellingen), daarna *Mapping*. Nu: één functie leest alles uit de HA-states in de global context en bouwt `msg.batteries` precies zoals *Mapping* deed. Ontbreken de globale states (optie uit, HA nog niet verbonden), dan stuurt output 2 het bericht door de oorspronkelijke keten en toont de node geel *fallback to old reads (reden) xN*. Vereist *Expose to global context* aan (R2).

**P2 — PID step in Self-consumption.** Was: 13 nodes achter elkaar plus 7 reads van PID-instellingen. Nu: één *PID step*-functie; zeven van de oorspronkelijke bodies zijn letterlijk overgenomen, *Calculate corrections* verschilt alleen door het feed-forward-blok (F1). Een template leest Kp, Ki, Kd, idle time, hysterese en beide dempingswaarden elke 60 s in de flow-context, bij het starten en zodra een helper wijzigt; is de cache ouder dan 10 minuten, dan leest *PID step* direct uit HA. Verder: vijf *Max 1 per 10 s*-delays vóór de writes naar de PID-helpers, en *Trace* is een functienode in plaats van JSONata.

**P3 — Pick period in Timed.** Was: 20 reads, 5 configfuncties, 5 tijdvak-switches en ~15 change- en switch-nodes. Nu: één *Pick period*-functie met dezelfde logica (periodes A t/m E, het eerste passende venster wint, een venster mag over middernacht lopen, start = eind is een lege periode). Gebruikt de tijd van HA, dus de tijdzone van Node-RED doet er niet toe. *Timed settings cache* rendert alle periode-instellingen elke 30 s en bij elke wijziging; is de snapshot ouder dan 5 minuten, dan draait de oude keten.

**P4 — Minder Modbus-writes.** Het schrijfontwerp blijft (awaited writes, *Write limiter*, failsafe van 30 s, *Collect completions*, *Write latency*). Daarbovenop: de **modus** wordt alleen geschreven als die verandert, als de teruglezing langer dan 20 s afwijkt, of als keep-alive elke 60 s (voorheen bij elke tick); van het **vermogen** wordt alleen het register van de huidige modus geschreven, en in `stop` niets; *Next write* voert de writes per batterij één voor één uit, eerst vermogen dan modus. Getest met 13 gesimuleerde scenario's.

### Features

**F1 — Feed-forward-start voor geregeld laden.** Bij de start van geregeld laden bereikte de PID de importlimiet alleen via de integrator, wat met een kleine Ki een minuut of langer duurde. Nu springt het vermogen direct naar huidig batterijvermogen + (importlimiet − netvermogen) − 150 W, begrensd op het max laadvermogen. Die waarde wordt 10 s vastgehouden, daarna neemt de PID het over zonder sprong (de integrator wordt ermee gevuld). Een pauze van meer dan 30 s telt als nieuwe sessie. Uitzetten: `FF_ENABLED = false` in *Regulated power*.

**F2 — Grid Clock als Dynamic-databron.** *Tariff data source* heeft Grid Clock-opties die `sensor.grid_clock_<zone>_prices` van de Grid Clock-integratie (gridclock.eu) lezen; het attribuut `prices` bevat `startsAt` en `total` in ct/kWh. Een `template_prefix` zet de lijst om naar `{start, price}` in EUR/kWh voor de Cheapest Energy Hours-macro. Een HA-automatisering in `house_battery_control_config.yaml` ververst de prijzen zodra de standaardzone van Grid Clock wijzigt. Vereist de Grid Clock-integratie.

**F3 — Charge Deadline-strategie.** Laadt tot een doel-SoC of doelenergie vóór een deadline, met voorkeur voor de goedkoopste vensters uit de Dynamic-prijslijst en bijladen van het net als PV tekortschiet. Bestaat uit het tabblad *HBC+ Strategy Charge Deadline*, het package `house_battery_deadline_charge.yaml` en een dashboardsectie (doel, schatting, geplande vensters, vervolgstrategie). *Charge Deadline* is ook kiesbaar als hoofdstrategie, in de Timed-lijst, als Dynamic-*cheapest* en als vervolgstap na *charge/sell goal reached*.

**F4 — Heartbeat met fallback in HA.** *HBC+ heartbeat (max every 60 s)* in de Start-flow publiceert naar MQTT `hbc/heartbeat` (retained), wat `sensor.hbc_last_run` voedt. Is die sensor ouder dan 5 minuten terwijl de mastermodus op *Full control* staat, dan geeft een HA-automatisering elke Marstek terug aan zijn firmware (RS485 uit, anti-feed) en stuurt een melding. Draait de lus weer, dan zet de master switch RS485 weer aan. Zonder dit blijven batterijen op hun laatste setpoint staan als Node-RED stopt. De fallback kent de fasen: op *Enforce* gaat per gedeelde fase alleen de batterij met het laagste M-nummer terug naar de firmware; zijn partner wordt eerst op RS485 *enable* + forcible *stop* gezet, zodat twee batterijen in firmware-anti-feed nooit samen één fase overbelasten. Batterijen alleen op hun fase of op *Own circuit*, en alle batterijen bij *Off* / *Monitor*, gaan terug zoals voorheen. De automatisering controleert ook opnieuw 5 minuten na een HA-herstart, schrijft naar het logboek en meldt via `notify.notify` (zet je eigen notify-actie in `packages/hbc_heartbeat.yaml`).

**F5 — Recorder-uitsluitingen.** `sensor.deadline_charged_at`, `sensor.deadline_window`, `sensor.deadline_cheap_blocks`, `sensor.deadline_goal_progress`, `sensor.hbc_energy_prices_data` en `input_number.house_battery_deadline_*_power` worden niet opgeslagen: ze renderen elke minuut opnieuw of dupliceren andere statistieken. Vooral `sensor.hbc_energy_prices_data` scheelt veel, omdat elke update van 15 minuten anders de hele prijslijst opnieuw opslaat.

### Uitbreidingen

| # | Onderdeel | Wat het doet |
| --- | --- | --- |
| E1 | *Strategy arbiter* + `hbc_strategy_arbiter.yaml` | Enige schrijver van `input_select.house_battery_strategy`; arbitreert tussen je eigen keuze, eigen flows (zoals een PV-limiter) en de Oscillation Guard (zie *Functionaliteit*) |
| E2 | *Battery Oscillation Guard* | Detecteert laad/ontlaad-golven en houdt via de arbiter *Full stop* vast; drempels via de omgevingsvariabelen van het tabblad, melding via de node *Notify phone* |
| E3 | Marstek via Modbus TCP | Een batterij via Modbus TCP werkt ongewijzigd met HBC+, zolang de entiteiten het patroon `marstek_mN_*` volgen |
| E4 | P1-alias uitgeschakeld in `house_battery_control_config.yaml` | Niet nodig als je meter al `sensor.p1_meter_power` levert (bijv. HomeWizard); zet hem aan bij een andere meter |

### Bekende open punten

1. **`value_conversion` bereikt alleen *Convert price*.** De macro rangschikt prijzen in de eenheid van de bron; Zonneplan en Grid Clock converteren daarom in `template_prefix`.

## Vereisten

HBC+ v1.0 is een complete, zelfstandige installatie: alle packages, flows en het dashboard staan in deze repository. Je hebt alleen de onderdelen hieronder nodig.

| Onderdeel | Vereiste | Waarom |
| --- | --- | --- |
| Home Assistant | Packages aan (`homeassistant: packages: !include_dir_named packages`) | Alle HBC+-helpers komen als packages |
| Node-RED | Add-on of standalone, met `node-red-contrib-home-assistant-websocket` 0.80 of nieuwer | Draait de regellus |
| Node-RED-palet | `node-red-contrib-time-range-switch`, `node-red-node-smooth` | Gebruikt door HBC+-tabbladen |
| MQTT | MQTT-integratie in HA met een broker | Status van de Phase monitor (`hbc/phase/*`) en de HBC+-heartbeat (`hbc/heartbeat`) |
| Batterijen | Marstek Venus E, maximaal 6, entiteiten `marstek_mN_*` (RS485 of Modbus TCP) | HBC+ leest SoC, vermogen, limieten en RS485-modus per batterij |
| Netmeter | Totaalvermogen `sensor.p1_meter_power` **en** vermogen per fase `sensor.p1_meter_power_phase_1` … `_3`, positief bij import | De zekeringruimte wordt per fase uit P1 berekend |
| Dashboard | `custom:apexcharts-card` (HACS) | Prijs- en historiegrafieken |
| Prijzen | [Cheapest Energy Hours](https://github.com/TheFes/cheapest-energy-hours)-macro (HACS) en een prijsintegratie | Nodig voor Dynamic en Charge Deadline |
| Optioneel | HELIOS-pyscript-optimizer; Grid Clock-integratie | HELIOS-strategie; Grid Clock als Dynamic-prijsbron |

De tekenconventies moeten kloppen: `sensor.marstek_mN_battery_power` is positief tijdens **laden**, `sensor.p1_meter_power_phase_N` is positief bij **import**. Gebruikt je meter het omgekeerde teken, corrigeer dat dan met een template-sensor vóór de installatie, anders wordt de zekeringruimte verkeerd berekend.

Beide limieten staan standaard op 16 A per fase (3680 W): de hoofdzekering (net) en de batterijgroep, de groep die de batterijen van één fase delen. Stel na de installatie je eigen waarden in (bijvoorbeeld een aansluiting van 3 × 32 A ≈ 7360 W met de batterijen op een groep van 16 A per fase ≈ 3680 W).

## Installatie

Download HBC+ van [github.com/CodeRubbere/HASS-HBC-Plus](https://github.com/CodeRubbere/HASS-HBC-Plus) (*Code* → *Download ZIP*, of clone de repository). De installatie duurt ongeveer 30 minuten en verandert niets aan het gedrag van de batterijen tot je de guard op *Enforce* zet.

### Wat er in de repository staat

**Hoofdmap**

| Bestand | Inhoud |
| --- | --- |
| `README.md` | Korte introductie, snelstart en credits |
| `LICENSE` | GPL-3.0-licentie |
| `.gitignore` | Houdt macOS- en editorbestanden buiten de repository |

**packages/** — Home Assistant-packages; kopieer ze alle zes naar de map `packages/` van HA.

| Bestand | Inhoud |
| --- | --- |
| `house_battery_control.yaml` | Kernhelpers en -sensoren: batterijaantal, totalen, PID-instellingen, strategiekeuze, Timed- en Dynamic-instellingen, prijsmelding |
| `house_battery_control_config.yaml` | Configuratie van jouw installatie: P1-alias (uitgeschakeld) en de automatisering die de prijzen ververst als de Grid Clock-zone wijzigt |
| `house_battery_deadline_charge.yaml` | Helpers en sensoren van Charge Deadline: doel, deadline, planning en goedkope vensters |
| `hbc_strategy_arbiter.yaml` | `input_text.hbc_strategy_arbiter`: de status van de Strategy arbiter, bewaard over herstarts heen |
| `hbc_heartbeat.yaml` | Fasebewuste HA-fallback als HBC+ stopt: `sensor.hbc_last_run`, `binary_sensor.hbc_heartbeat_stale` en de automatisering die de batterijen teruggeeft aan hun firmware |
| `hbc_phase_guard.yaml` | Fasebewaking: instellingen, fasekaart M1–M6, vermogen en zekeringruimte per fase, overbelastingsalarm, MQTT-statussensoren en het script met standaardwaarden |

**dashboards/**

| Bestand | Inhoud |
| --- | --- |
| `hbc_plus.yaml` | Het dashboard *Home Battery Control Plus* met de views Home, Self-consumption, Charge/Sell, Timed/Dynamic, Phases, Problem solver en Advanced settings |

**node-red/** — importeer `hbc-plus-all-flows.json` (alles in één keer) of de losse bestanden.

| Bestand | Tabblad | Wat het doet |
| --- | --- | --- |
| `hbc-plus-all-flows.json` | Alle 15 hieronder | Eén importbestand met alle tabbladen en de HA-servernode |
| `00 master-switch-flow (HBC+).json` | HBC+ Home Battery Master Switch v1.0 | Bepaalt wie de Marsteks aanstuurt (RS485, werkmodus); geeft per gedeelde fase maar één batterij terug aan de firmware |
| `00 presets-switch-flow (HBC+).json` | HBC+ Home Battery PID presets v1.0 | Zet een PID-preset (Very safe, Safe, Regular) op de PID-helpers |
| `01 start-flow (HBC+).json` | HBC+ Home Battery Start v1.0 | De regellus: leest de batterijen, telt de totalen, draait phase planner, strategie en phase guard, schrijft de setpoints, en publiceert de heartbeat |
| `02 strategy-charge (HBC+).json` | HBC+ Strategy Charge v1.0 | Laadt van het net tot een doel (vol, SoC, energie of zonneverwachting) |
| `02 strategy-charge-deadline (HBC+).json` | HBC+ Strategy Charge Deadline v1.0 | Laadt tot een doel vóór een deadline, in de goedkoopste kwartieren |
| `02 strategy-dynamic (HBC+).json` | HBC+ Strategy Dynamic v1.0 | Kiest een strategie per prijsperiode (goedkoop, duur, normaal); bevat de gedeelde prijsophaling |
| `02 strategy-full-stop (HBC+).json` | HBC+ Strategy Full stop v1.0 | Zet alle batterijen op stop |
| `02 strategy-helios (HBC+).json` | HBC+ Strategy Helios v1.0 | Voert de beslissing van de HELIOS-optimizer uit |
| `02 strategy-partials (HBC+).json` | HBC+ Strategy Partials v1.0 | Charge PV, Zero import en Standby / peak shave |
| `02 strategy-self-consumption (HBC+).json` | HBC+ Strategy Self-consumption v1.0 | PID-regelaar die het netvermogen op het doel houdt; verdeelt het vermogen over de batterijen |
| `02 strategy-sell (HBC+).json` | HBC+ Strategy Sell v1.0 | Ontlaadt naar het net tot een doel |
| `02 strategy-timed (HBC+).json` | HBC+ Strategy Timed v1.0 | Draait een strategie per tijdvak (A t/m E) |
| `03 battery-oscillation-guard (HBC+).json` | HBC+ Battery Oscillation Guard v1.0 | Herkent laad/ontlaad-golven en houdt via de arbiter Full stop vast |
| `03 phase-monitor (HBC+).json` | HBC+ Phase monitor v1.0 | Alleen-lezen: publiceert de fasestatus via MQTT voor het dashboard |
| `03 strategy-arbiter (HBC+).json` | HBC+ Strategy arbiter v1.0 | Enige schrijver van de strategiekeuze; kiest tussen je eigen keuze, eigen flows en de Oscillation Guard |
| `README.md` | — | Overzicht van de Node-RED-bestanden en installatie |

**docs/**

| Bestand | Inhoud |
| --- | --- |
| `user-guide.en.md` | Deze handleiding in het Engels |
| `gebruikershandleiding.nl.md` | Deze handleiding in het Nederlands |

### Stap 1 — Back-up maken

1. Node-RED: menu → *Export* → *All flows* → *Download*.
2. Home Assistant: maak een volledige back-up, of kopieer minstens je map `packages/` en de dashboard-YAML.
3. Draai je een eerdere versie en heb je een tabblad in Node-RED gewijzigd sinds je het laatst exporteerde, exporteer dat tabblad dan eerst. De HBC+-bestanden vervangen tabbladen met dezelfde node-id's.

### Stap 2 — Home Assistant-packages

1. Kopieer alle zes bestanden uit `packages/` naar de map `packages/` van HA (vervang oudere kopieën). Staat er nog een eerdere `nodered_heartbeat.yaml`, verwijder die dan: `hbc_heartbeat.yaml` vervangt hem, en met beide bestanden ziet HA dubbele ids en valt de fallback weg.
2. Controleer of de namen van je P1-sensoren kloppen (`sensor.p1_meter_power`, `sensor.p1_meter_power_phase_1` … `_3`). Zo niet, voeg dan template-aliassen toe in `house_battery_control_config.yaml`.
3. *Ontwikkelhulpmiddelen* → *Configuratie controleren*, en herstart Home Assistant.
4. Voer het script **HBC+ phase guard: apply defaults** één keer uit (*Instellingen* → *Automatiseringen & scènes* → *Scripts*). Nieuwe helpers zonder `initial:` starten op hun minimum of eerste optie; het script zet guard-modus *Monitor*, *One per phase*, *SoC balance*, 3680 W netzekering, 3680 W batterijgroep, 200 W marge, 5 % wisseldelta, 15 min verblijftijd, en de fasekaart M1/M4 = L1, M2/M5 = L2, M3/M6 = L3. HA herstelt de waarden na elke volgende herstart.

### Stap 3 — Node-RED-flows

1. Open na de import de Home Assistant-serverconfig-node (*HA System*, id `176d29a.6f648d6`) en controleer of het serveradres en het toegangstoken kloppen voor jouw opstelling.
2. Menu → *Import* → kies `hbc-plus-all-flows.json` → kies **Replace** voor bestaande nodes. Tabbladen met dezelfde node-id's (van een eerdere installatie) worden vervangen, niet gedupliceerd.
3. Controleer of de servernode **Expose to global context** aan heeft. *Read HA states (fast)*, de HBC+-planner en -guard en *Prepare request* in Dynamic hebben het nodig. Alle HBC+-bestanden bevatten de juiste kopie; een oudere Helios-export had een kopie met deze optie uit.
4. *Deploy* → *Modified flows*, op een rustig moment. HBC+ schrijft na een deploy één keer modus en vermogen opnieuw naar de batterijen; dat is normaal.
5. Zet je eigen notify-actie in de node *Notify phone* van *HBC+ Battery Oscillation Guard v1.0*; standaard is `notify.notify`. Stap 6 noemt alle drie de plekken die meldingen sturen.

**Eigen flows** kunnen een strategie aanvragen via de *Strategy arbiter*: een link call naar *Strategy request* met `msg.arbiter = {requester, action: 'hold' | 'release', strategy, reason}`. Geef de aanvrager een prioriteit in de node *Arbitrate*; de Battery Oscillation Guard heeft 100, elke andere naam voor de aanvrager krijgt 50, en bij gelijke prioriteit wint de hold die het eerst kwam. Een handmatige keuze wint altijd en wordt de nieuwe basis.

### Stap 4 — Dashboard

1. *Instellingen* → *Dashboards* → *Dashboard toevoegen* → *Nieuw dashboard vanaf nul*, noem het *Home Battery Control Plus*.
2. Open het → ⋮ → *Dashboard bewerken* → ⋮ → *Ruwe configuratie-editor*, plak de inhoud van `dashboards/hbc_plus.yaml` en sla op.
3. Open de view **Phases** en controleer of elke kaart waarden toont.

### Stap 5 — Fasekaart en zekering instellen

Zet op de Phases-view, onder *Which phase is each battery on?*, elke batterij op de fase waarop hij fysiek is aangesloten. Zet *Grid fuse per phase* op je hoofdzekering en *Battery circuit per phase* op de groep die de batterijen van één fase delen (A × 230 V; 16 A → 3680 W, voor beide de standaardwaarde). Geen aparte batterijgroep? Zet beide op de hoofdzekering. Ga daarna verder met het in bedrijf nemen hieronder.

### Stap 6 — Eerste start

1. **Onboarding.** Bovenaan de view *Home Battery Control Plus* staat een onboarding-checklist. Zet **Number of batteries** (`input_number.house_battery_count`, 1–6). Controleer dat *Grid Power Sensor* op *Configured* staat en *Node-RED* op *Configured and script deployed* (de Start-flow zet `input_boolean.house_battery_control_has_node_red` aan). Verberg de checklist daarna met *Finish onboarding*.
2. **Batterij-entiteiten.** Elke batterij heeft zijn entiteiten `marstek_mN_*` nodig, van M1 tot het aantal dat je instelde. Controleer op de Phases-view dat elke batterij SoC en vermogen toont.
3. **PID-preset.** Kies in de Self-consumption-view *Safe* (zie *Self-consumption en PID-afstelling*).
4. **Strategie.** Kies een eerste strategie; *Self-consumption* of *Charge PV* is een veilige start.
5. **Mastermodus.** Zet *Master Battery Mode* op **Full control**. Pas nu stuurt HBC+ de batterijen. Wil je ze teruggeven aan hun eigen firmware, kies dan *Marstek control*.
6. **Meldingen.** Zet je eigen notify-actie (bijv. `notify.mobile_app_<telefoon>`) op de drie plekken die een melding sturen; standaard is `notify.notify`.

| Waar | Stuurt een melding als |
| --- | --- |
| Node-RED, *HBC+ Battery Oscillation Guard v1.0*, node *Notify phone* | De batterijen slingeren en op *Full stop* worden gehouden |
| `packages/hbc_heartbeat.yaml`, automatisering *hand batteries back to firmware when the HBC heartbeat is stale* | De regellus stopte en de batterijen teruggingen naar hun firmware |
| `packages/house_battery_control.yaml`, automatisering *alert when the tariff source delivers no prices* | De tariefbron 30 minuten geen geldige prijzen leverde |

### HBC+ bijwerken

Een nieuwe HBC+-versie komt als nieuwe release van [de repository](https://github.com/CodeRubbere/HASS-HBC-Plus). Je instellingen blijven behouden: ze staan in de helpers, en Home Assistant zet ze na een herstart terug.

1. **Maak een back-up** zoals in stap 1.
2. **Lees de release notes** op hernoemde of verwijderde bestanden, en verwijder die uit de map `packages/` van HA (in v1.0: `nodered_heartbeat.yaml` werd `hbc_heartbeat.yaml`).
3. **Packages:** kopieer de nieuwe `packages/*.yaml` over de oude heen. Heb je zelf een package aangepast (de P1-alias in `house_battery_control_config.yaml`, een notify-actie), neem die wijziging dan over in het nieuwe bestand. Daarna *Configuratie controleren* en HA herstarten.
4. **Flows:** importeer `node-red/hbc-plus-all-flows.json` met **Replace** en deploy. Wijzigingen die je in HBC+-tabbladen maakte worden overschreven, dus zet je notify-actie in *Notify phone* opnieuw.
5. **Dashboard:** heeft de release `dashboards/hbc_plus.yaml` gewijzigd, plak hem dan opnieuw in de ruwe configuratie-editor.
6. **Nieuwe instellingen:** een helper die nieuw is in een release start op zijn minimum. Stel hem direct na het bijwerken in; de release notes noemen hem (bijvoorbeeld *Battery circuit per phase*). *HBC+ phase guard: apply defaults* zet hem ook, maar zet ook de fasekaart terug.

## Configuratiereferentie

De fasebewakingsentiteiten hieronder komen uit `packages/hbc_phase_guard.yaml`; hun instellingen staan op de Phases-view, en de standaardwaarden zijn wat *HBC+ phase guard: apply defaults* instelt. De overige HBC+-entiteiten staan onder *Overige HBC+-entiteiten*; de strategie-instellingen staan in *Strategieën en instellingen*.

### Instellingen

| Entiteit | Opties / bereik | Standaard | Wat het doet |
| --- | --- | --- | --- |
| `input_select.house_battery_phase_guard_mode` | Off · Monitor · Enforce | Monitor | Of de faseregels werken |
| `input_select.house_battery_phase_sharing` | One per phase · Shared headroom | One per phase | Eén batterij per fase, of beide binnen de zekeringruimte |
| `input_select.house_battery_phase_selection` | SoC balance · Fixed order · Rotate daily | SoC balance | Hoe de actieve batterij gekozen wordt |
| `input_number.house_battery_phase_limit_w` | 1000–17250 W | 3680 W | Netzekering per fase (hoofdzekering): huis en batterijen samen, import en export, gelijk voor L1–L3 |
| `input_number.house_battery_phase_circuit_limit_w` | 500–17250 W | 3680 W | Batterijgroep per fase: de groep die de batterijen van één fase delen; alleen de batterijen tellen |
| `input_number.house_battery_phase_margin_w` | 0–1000 W | 200 W | Phase limit margin: blijft vrij onder zowel de netzekering als de batterijgroep, voor meetfouten en laststappen |
| `input_number.house_battery_phase_switch_soc_delta` | 1–30 % | 5 % | SoC-verschil nodig om de actieve batterij te wisselen |
| `input_number.house_battery_phase_min_dwell` | 1–120 min | 15 min | Minimale tijd dat een batterij actief blijft vóór een SoC-wissel |
| `input_select.marstek_m1_phase` … `m6_phase` | L1 · L2 · L3 · Own circuit | M1/M4 L1, M2/M5 L2, M3/M6 L3 | Op welke fase elke batterij zit |

Het aantal batterijen komt nog steeds uit `input_number.house_battery_count` (max 6).

### Sensoren

| Entiteit | Bron | Wat het toont |
| --- | --- | --- |
| `sensor.hbc_phase_l1_active` … `l3` | MQTT `hbc/phase/L1` … `L3` | Actieve batterij (M1, M4 of none); attributen standby, mode, room, setpoint, would, reason, since |
| `sensor.hbc_phase_findings` | MQTT `hbc/phase/summary` | Aantal fasen waar HBC+ zou ingrijpen |
| `sensor.hbc_phase_l1_battery_power` … `l3` | Template | Gemeten som van het batterijvermogen op die fase |
| `sensor.hbc_phase_l1_charge_headroom` … `l3` | Template | Laadruimte onder de netzekering en de batterijgroep (zelfde formule als Node-RED) |
| `sensor.hbc_phase_l1_discharge_headroom` … `l3` | Template | Ontlaadruimte onder de netzekering en de batterijgroep |
| `sensor.house_battery_installed_max_charge_power` | Template | Gewone som van het max laadvermogen van alle batterijen, ter vergelijking |
| `binary_sensor.hbc_phase_limit_exceeded` | Template | Aan als het netvermogen op een fase 10 s boven de netzekering ligt |
| `binary_sensor.hbc_phase_circuit_limit_exceeded` | Template | Aan als de batterijen op een fase 10 s meer trekken dan de batterijgroep |
| `script.hbc_phase_guard_defaults` | Script | Zet alle HBC+-instellingen en de fasekaart terug op de standaardwaarden |

De template-sensoren en het alarm draaien alleen in Home Assistant en blijven dus werken als Node-RED stilstaat. De MQTT-statussensoren zijn alleen voor weergave en uitgesloten van de recorder.

### Overige HBC+-entiteiten

| Entiteit | Package | Wat het is |
| --- | --- | --- |
| `sensor.hbc_last_run` | `hbc_heartbeat.yaml` | Tijd van de laatste HBC+-heartbeat (MQTT `hbc/heartbeat`) |
| `binary_sensor.hbc_heartbeat_stale` | `hbc_heartbeat.yaml` | Aan als er meer dan 5 minuten geen heartbeat was; in *Full control* geeft dit de batterijen terug aan hun firmware |
| `sensor.hbc_energy_prices_data` | `house_battery_control.yaml` | De huidige prijslijst voor het dashboard; attribuut `status` is `ok`, `stale` of `no_data` |
| `binary_sensor.hbc_price_data_missing` | `house_battery_control.yaml` | Aan als er een tariefbron gekozen is maar geen geldige prijzen beschikbaar zijn |
| `input_text.house_battery_strategy_dynamic_price_sensor` | `house_battery_control.yaml` | Optioneel: legt de prijssensor voor Dynamic vast (zie R4) |
| `input_text.hbc_strategy_arbiter` | `hbc_strategy_arbiter.yaml` | Status van de Strategy arbiter, teruggezet na een herstart |
| `input_boolean.house_battery_control_has_node_red` | `house_battery_control.yaml` | Wordt aangezet door de Start-flow zodra die draait; gebruikt door de onboarding-checklist |
| `sensor.hbc_time` | `house_battery_control.yaml` | Lokale tijd (UU:MM) voor de badge *Time* op de dashboardviews |

### Waarden kiezen

- **Netzekering:** je hoofdzekering per fase in A × 230 V (3 × 16 A → 3680 W, de standaardwaarde; 3 × 25 A → 5750 W; 3 × 32 A → 7360 W). Een aansluiting heeft op elke fase dezelfde zekering, dus één waarde geldt voor L1–L3.
- **Batterijgroep:** de automaat van de groep die de batterijen van één fase delen (16 A → 3680 W). Andere verbruikers op die groep worden niet gemeten; verhoog dan de marge. Geen aparte batterijgroep? Gebruik de waarde van de netzekering.
- **Marge:** 200 W dekt meetfouten en kleine stappen; hij geldt voor beide limieten. Verhoog hem als een van de alarmen afgaat terwijl batterijen op vol vermogen draaien.
- **Wisseldelta en verblijftijd:** lagere waarden houden de SoC strakker in balans, maar geven meer wissels (relaisklikken). De standaardwaarden geven hooguit één wissel per 15 min per fase.
- **Own circuit:** gebruik dit voor een batterij op een eigen groep die zijn fase niet met een partner deelt achter de hoofdzekering. Hij wordt nooit door de faseregels begrensd.

## In bedrijf nemen: van Monitor naar Enforce

Laat HBC+ een paar dagen op *Monitor* draaien voordat twee batterijen een fase delen. Met één batterij per fase verandert ook Enforce niets, dus je kunt de koppeling kosteloos testen.

1. **Controleer de metingen.** Op de Phases-view moet *Batteries* per fase overeenkomen met de eigen vermogenssensor van elke batterij, en de netmeter moet kloppen met je meter. Controleer de tekens: laden geeft positief batterijvermogen, import geeft positief netvermogen.
2. **Kijk een paar dagen naar Monitor.** In Node-RED toont de status van *HBC+ phase planner* en *HBC+ phase guard* `would: …`. Met één batterij per fase moet de actieve batterij altijd die batterij zijn en hoort `sensor.hbc_phase_findings` op 0 te blijven, behalve als de zekeringruimte begrenst.
3. **Zet op Enforce** via de Phases-view. Zolang elke fase één batterij heeft, hoort er niets te veranderen.
4. **Voeg de tweede batterij op een fase toe** (bijvoorbeeld Marstek M4 op L1): maak zijn entiteiten `marstek_m4_*` aan, verhoog `input_number.house_battery_count` en zet `input_select.marstek_m4_phase` = L1.
5. **Test in deze volgorde**, terwijl je de Phases-view bekijkt:
   - [ ] Charge op max vermogen: één batterij per fase laadt, de partner staat op 1 W idle en stopt daarna
   - [ ] Sell op max vermogen: de volste batterij ontlaadt
   - [ ] Self-consumption met 4 kW last op één fase
   - [ ] Laden met 2 kW last op L1: de grens moet zakken naar ongeveer 1480 W
   - [ ] Full stop
   - [ ] RS485 uit op de actieve batterij: de partner neemt over na break-before-make
   - [ ] Netwerk van de actieve batterij loskoppelen: de partner moet geblokkeerd blijven en de fase staat stil
6. **Na batterij 5 en 6**: controleer 's nachts of Charge Deadline genoeg goedkope slots boekt voor het max vermogen per fase.

Houd tijdens het testen altijd het dashboard en de HA-alarmen in de gaten: `binary_sensor.hbc_phase_limit_exceeded` en `binary_sensor.hbc_phase_circuit_limit_exceeded` kleuren de Phases-view rood na 10 s boven hun limiet.

## Dashboard

Het dashboard *Home Battery Control Plus* heeft een view **Phases**, die drie vragen in één oogopslag beantwoordt: welke batterij werkt er op elke fase, hoe dicht zit elke fase bij zijn zekering, en waarom.

| View | Waarvoor |
| --- | --- |
| Home Battery Control Plus | Onboarding, mastermodus, strategiekeuze, batterijoverzicht |
| Self-consumption | PID-afstelling en -analyse |
| Charge/Sell | Doelen en limieten voor Charge, Sell en Charge Deadline |
| Timed/Dynamic | Tijdvakken, prijsbron en goedkope/dure periodes |
| **Phases** (nieuw) | Status van de phase guard, kaarten per fase, instellingen en fasekaart |
| Problem solver (spinnen-icoon) | *Flow trace* en *Insights*: de route van de laatste tick en de uitleg van elke node; zet *Insight mode* aan (gaat na 5 min vanzelf uit) |
| Advanced settings | Batterijlevensduur, peak shaving, laad-/ontlaadlimieten |

Op de Home-view verschijnen waarschuwingskaarten alleen als er iets aandacht nodig heeft:

- **Onboarding** — de checklist (aantal batterijen, netsensor, Node-RED, vermogensgrenzen), tot je hem verbergt.
- **No energy prices** — `binary_sensor.hbc_price_data_missing` staat aan; Dynamic draait zijn basisstrategie (zie R3).
- **Dynamic strategy: Full Stop** — Dynamic is gekozen terwijl *Tariff data source* op *None* staat.

De Phases-view, van boven naar beneden:

- **Badges** — *Choose strategy*, *Executing* (de actieve sub-strategie) en *Time*, net als op de andere views.
- **Alarmen** — rode kaarten, alleen zichtbaar zolang `binary_sensor.hbc_phase_limit_exceeded` (netzekering) of `binary_sensor.hbc_phase_circuit_limit_exceeded` (batterijgroep) aan staat.
- **Phase guard** — tegels voor guard-modus, sharing, netzekering, batterijgroep, limietmarge, en *Phases where HBC+ would act*.
- **L1 · L2 · L3** — per fase: een meter van het netvermogen tegen de zekering, de actieve batterij, het gemeten batterijvermogen op de fase, laadruimte en ontlaadruimte, plus de standby-batterij, het setpoint en de reden van de planner. Een tabel toont elke batterij op de fase met SoC, vermogen en rol: *active · charge*, *active · discharge*, *active · idle* of *standby*.
- **Instellingen** — alle HBC+-instellingen, en *Which phase is each battery on?* voor M1–M6.

De meter toont het netvermogen tegen de netzekering: afname (positief) in lichtrood en teruglevering (negatief) in lichtgroen; oranje vanaf ±3200 W, rood vanaf ±3680 W. De banden en het bereik van ±4000 W staan vast in de YAML: pas ze aan als je netzekering afwijkt.

## Problemen oplossen

| Symptoom | Waarschijnlijke oorzaak | Oplossing |
| --- | --- | --- |
| Phases-view toont *unknown* bij de actieve batterij | MQTT niet ingesteld, of Phase monitor-tabblad uitgeschakeld | Controleer de MQTT-integratie; schakel *HBC+ Phase monitor v1.0* in |
| *Read HA states (fast)* geel: `fallback to old reads` | *Expose to global context* staat uit op de servernode | Zet het aan in *HA System*, Deploy |
| Plannerstatus toont niets of `guard off` | Guard-modus staat op Off | Zet Monitor of Enforce |
| Laadruimte altijd 0 of veel te laag | Verkeerd teken op de P1-fasesensoren of het batterijvermogen | Maak import en laden positief (Vereisten) |
| Beide batterijen op een fase draaien tegelijk bij *One per phase* | Guard op Off of Monitor, of de fasekaart klopt niet | Zet Enforce; controleer `input_select.marstek_mN_phase` |
| Partner neemt nooit over | Teruglezing van de oude batterij verouderd (break-before-make blokkeert bewust) | Herstel de Modbus-verbinding van de oude batterij |
| Overbelastingsalarm gaat kort af bij het inschakelen van een grote last | Laststap vóór de volgende tick | Normaal voor enkele seconden; verhoog de marge als het 10 s duurt |
| Nieuwe instellingen staan na installatie op hun minimum | Standaardwaarden nooit toegepast | Voer *HBC+ phase guard: apply defaults* uit |
| Charge Deadline boekt te weinig uren | Guard niet op Enforce met 6 batterijen, dus het telt 15000 W | Zet Enforce |
| Link call naar *Dynamic Fetch from Data Source* loopt in een timeout | Ophaling mislukt in de sectie, of timeout korter dan de ophaling | Bekijk *Strategy errors* in het Dynamic-tabblad; zet de timeout op minstens 30 s |
| Dashboard: *No energy prices*, of `binary_sensor.hbc_price_data_missing` aan | De tariefbron levert geen prijzen (integratie offline, sensor hernoemd, verkeerde sensor geraden) | Controleer de prijsintegratie; zet `input_text.house_battery_strategy_dynamic_price_sensor` op de juiste sensor; de status van *Data source settings* in het Dynamic-tabblad toont welke sensor gebruikt wordt |
| Dynamic-status geel: *(last prices)* | De laatste ophaling mislukte; de vorige prijzen van dezelfde bron zijn nog in gebruik | Niets doen als het bij de volgende run verdwijnt; anders als hierboven |
| Batterijen draaien ineens op hun eigen firmware; melding *HBC stopped - batteries on firmware* | De regellus stond 5 minuten stil (Node-RED offline, deployfout, HA-verbinding kwijt), dus gaf de heartbeat-fallback de batterijen terug | Start of herstel Node-RED; zodra de lus weer draait, neemt de Master Switch-flow het in *Full control* weer over |
| Onboarding toont *Setup Node-RED* | De Start-flow heeft nog niet gedraaid | Importeer en deploy de flows (stap 3); controleer de servernode *HA System* |
| De gekozen strategie blijft niet staan, of verandert vanzelf | Een hold in de Strategy arbiter (Oscillation Guard of een eigen flow) | Bekijk `input_text.hbc_strategy_arbiter` en het HA-logboek; een handmatige keuze wordt de nieuwe basis, de hold eindigt als de aanvrager hem loslaat |

Wil je zien wat HBC+ besliste en waarom, open dan de view **Problem solver** (spinnen-icoon) en zet *Insight mode* aan.

Elk tabblad heeft een commentaar **📖 How this flow works – HBC+ v1.0**: open het en lees de Info-zijbalk. Het laatste guard-resultaat staat in de Node-RED global context als `hbcplus_guard_last`; correcties gaan ook naar het HBC+-debugboard.

## Hulp en feedback

Vragen, bugs en ideeën: open een issue in [de repository](https://github.com/CodeRubbere/HASS-HBC-Plus/issues). Noem de HBC+-versie, wat je verwachtte en wat er in plaats daarvan gebeurde. Voeg als het kan de status van de betrokken Node-RED-nodes toe en het HA-logboek rond dat moment.

## Gerelateerd

- [HASS-HBC-Plus op GitHub](https://github.com/CodeRubbere/HASS-HBC-Plus) — de repository.
- [English user guide](user-guide.en.md) — de Engelse versie van deze handleiding.
- [node-red/README.md](../node-red/README.md) — overzicht per tabblad van de HBC+-wijzigingen.

