---
name: meeting-live
source: wds
type: script
description: Strömmar ett pågående Fireflies-möte till en lokal fil och väcker agenten med nya repliker. Allt körs på datorn, utan server och utan MCP. Skriptet ligger i meeting-live/live.py.
used_by: [live-meeting]
---

# Tool: meeting-live

Fireflies realtid går direkt till en jsonl-fil på datorn. Agenten bevakar filen och får nya repliker ungefär var 30:e sekund.

```
Fireflies (socket.io) → live.py join (i bakgrunden) → .wds/live/<tid>-<titel>.jsonl → live.py watch → agenten
```

Strömmen och bevakningen är två processer. Bevakningen kan startas om när som helst utan att mötet tappas, och den fortsätter där den slutade (`<fil>.seen`).

## Konfiguration

| Vad | Var |
|---|---|
| Fireflies språk | **Multi-Language på alla möten** (Mårten, 2026-10-17), i Fireflies inställningar: flera språk i samma möte, beta. Språket går inte att sätta i kalenderinbjudan. |
| Fireflies-nyckeln | Bitwarden-posten `Fireflies API Key`, lösenordsfältet. Hämtas vid körning, skrivs aldrig till fil. |
| Python-paket | `python -m pip install "python-socketio[client]"` (en gång per dator). Den lokala reserven: `pyaudiowpatch faster-whisper numpy`. |
| Mötesfilen | `.wds/live/` i repots rot, arbetsmaterial under mötet. `.wds/` är gitignorerad. |
| Mötesarkivet | `communication/meetings/` på den nivå det gäller (repots rot för en kund), med registret `communication/meetings.md`. Repots `AGENTS.md` kan ange en annan plats. |

Skriptet: `agents/wds/tools/meeting-live/live.py`. I ett repo utan `agents/wds/` används sökvägen i WDS-repot.

## Åtgärder

### Pågående möten

```bash
FIREFLIES_API_KEY="$(bw get password 'Fireflies API Key')" python agents/wds/tools/meeting-live/live.py list
```

### Gå med (i bakgrunden)

Det senaste pågående mötet, eller ett visst med `--id <id>`. Kör med Bash `run_in_background`, eftersom processen lever lika länge som mötet:

```bash
FIREFLIES_API_KEY="$(bw get password 'Fireflies API Key')" python agents/wds/tools/meeting-live/live.py join --number 1
```

Utskriften börjar med `Ansluten till "<titel>"` och `Fil: <sökväg>`. Mötets tidigare repliker skrivs in först, så att agenten kommer ikapp.

**Joinen håller sig vid liv.** Faller anslutningen till Fireflies och kommer inte tillbaka inom 20 sekunder, bygger joinen en ny i samma fil och fyller luckan ur Fireflies sparade transkript. Bevakningen visar `== Anslutningen föll, ansluter igen ==` och `== Luckan fylld med N repliker ==`. Ingen replik skrivs två gånger.

**Har processen dött,** fortsätt i samma fil i stället för att starta en ny:

```bash
FIREFLIES_API_KEY="$(bw get password 'Fireflies API Key')" python agents/wds/tools/meeting-live/live.py join --continue .wds/live/<fil>.jsonl
```

### Bevaka

**Claude Code:** Monitor med kommandot nedan och `timeout_ms: 1800000`. Varje utskrift är en klump nya repliker. När bevakningen löper ut efter 30 minuter startas den igen med samma kommando.

```bash
python agents/wds/tools/meeting-live/live.py watch .wds/live/<fil>.jsonl --every 10
```

Bevakningen skriver ut `== MÖTET ÄR SLUT: <skäl> ==` och avslutas när Fireflies slutar spela in, och `== FEL: … ==` om något går fel.

**Copilot och Codex** har ingen bevakning som väcker dem. Läs nya rader med `transcript` när personen frågar, eller mellan varje svar.

### Hela mötet som text

```bash
python agents/wds/tools/meeting-live/live.py transcript .wds/live/<fil>.jsonl
```

### Lokal utskrift, utan bot (fel språk, Fireflies spelar inte in, eller allt annat ljud)

Lyssnar på datorns ljud ut, alltså det personen hör, och mikrofonen, och skriver ut lokalt med Whisper när talaren pausar, i samma format. Ljudet lämnar aldrig datorn. Ingen bot går med i mötet, så det fungerar oavsett vem som bjudit in och på vilken plattform. Med `--no-mic` bara datorns ljud: videor, webbinarier, poddar.

**De andra ska veta om det.** En bot syns i mötet; den lokala utskriften syns inte. Använd den bara när alla i samtalet vet att det skrivs ut, och aldrig i privata samtal som inte gäller arbetet. Börjar ett samtal handla om något annat, stoppa utskriften.

Whisper hittar ibland på text i brus och korta ljud (".", "000", `<|nospeech|>`, påhittade ord). Sådant sorteras bort med modellens egna mått på om det var tal och hur säkra orden är; i provet behölls alla 32 riktiga yttranden. Windows. Svenska använder KB-Whisper, som laddas ned första gången (några minuter). Kör i bakgrunden och bevaka filen med `watch` som vanligt:

```bash
python agents/wds/tools/meeting-live/local.py .wds/live/<tid>-lokal.jsonl --them "<de andra>" --me "<personen>" --lang sv
```

`--lang auto` upptäcker språket för varje bit, för möten som byter språk.

Uppmätt 2026-10-17 på Mårtens dator (8 kärnor, ingen grafikkort-acceleration) med ett svenskt röstmeddelande på 131 sekunder:

| Modell | Tid mot realtid | Svenska |
|---|---|---|
| `KBLab/kb-whisper-small` (`--lang sv`, standard) | 0,17 | Bäst: namn och ord rätt |
| `small` (`--lang auto`) | 0,18 | Upptäcker svenska, men fler fel |
| `medium` (`--lang auto`) | 0,49 | Inte bättre än KB-Whisper; med två ljudkällor nära realtid |

Båda små modellerna hinner med live med god marginal.

**Fördröjning:** ljudet klipps vid pauser (0,5 s) och senast efter 8 sekunder (`--pause`, `--max`). Mätt med samma inspelning matad i realtid: text **4 sekunder** efter första ordet (median), högst 8,4. Bitar om 15 sekunder gav 15 till 20. Ett lägre tak (6 s) klipper oftare mitt i meningar. Riktig strömning ord för ord tolkar om ljudet varje sekund och räcker troligen inte för två källor på en dator utan grafikkort-acceleration. Talarna skiljs bara åt som "de andra" och "jag". ```bash
python agents/wds/tools/meeting-live/local.py .wds/live/<tid>-<titel>.jsonl --no-mic --them "<videon>"
```

Använd den när Fireflies transkriberar på fel språk (då blir texten obegriplig redan första minuten) eller inte kommer igång.

### Arkivera

Efter mötet: hela mötet till repots mötesarkiv, sammanfogat från alla filer som hör till mötet (flera anslutningar, en ny inspelning på rätt språk, den lokala reserven). Det färdiga transkriptet hämtas från Fireflies när det finns, eftersom det är renare än liveutskriften; annars används liveutskriften.

```bash
FIREFLIES_API_KEY="$(bw get password 'Fireflies API Key')" python agents/wds/tools/meeting-live/live.py archive .wds/live/<fil>.jsonl [<fil>.jsonl …] --out communication/meetings --lang sv --title "<mötets namn>"
```

Det skriver `communication/meetings/<datum>-<titel>.md` och lägger till en rad i `communication/meetings.md` (datum, möte, längd, Fireflies-id, transkript, sammanfattning). Sammanfattningskolumnen fylls i när sammanfattningen är skriven. Fireflies färdiga transkript kan dröja några minuter efter mötet; `--no-fetch` arkiverar liveutskriften direkt.

### Avsluta

Stoppa bakgrundsprocessen. Joinen skriver själv en slutrad när mötet inte längre pågår i Fireflies (kontrolleras varje minut).

## Filformat

En rad per händelse, i ordning:

```json
{"event": "joined", "title": "…", "meeting_id": "…", "participants": ["…"], "at": "…"}
{"n": 1, "start": 3.2, "speaker": "Anna", "text": "…", "seed": true}
{"n": 2, "start": 61.0, "speaker": "Mårten", "text": "…", "id": "<chunk_id>"}
{"event": "reconnecting", "at": "…"}
{"event": "filled", "count": 4, "at": "…"}
{"event": "ended", "reason": "…", "at": "…"}
```

`seed: true` är repliker från före anslutningen, `fill: true` repliker som fyllde en lucka. `start` är sekunder från mötets början.

## Fel

| Vad som händer | Säg och gör |
|---|---|
| Bitwarden är låst | "Lås upp Bitwarden: `bw unlock`, och klistra in BW_SESSION." Skicka den i miljön per kommando, spara den aldrig. |
| `Inga pågående möten` | "Fireflies spelar inte in just nu. Starta inspelningen, så går jag med om 30 sekunder." |
| `auth failed` | Nyckeln är fel eller har gått ut. Kontrollera Bitwarden-posten. |
| `Paketet saknas` | Installera `python-socketio[client]` och gå med igen. |
| Bakgrundsprocessen avslutas oväntat | Läs dess utskrift och fortsätt i samma fil med `join --continue <fil>`. |
| Texten är obegriplig eller på fel språk | Fireflies har fel språkinställning. Säg det direkt, starta den lokala reserven, och be personen byta språk i Fireflies (det ger ett nytt mötes-id; gå med i det också). `archive` tar med alla delarna. |

Fördröjningen från tal till fil är några sekunder (Fireflies taligenkänning), plus bevakningens intervall.

## Inte tillgängligt

**Agenten kan inte tala i mötet.** Två vägar finns om det behövs, så att det inte behöver utredas igen:

| Väg | Hur | Passar |
|---|---|---|
| Virtuell ljudkabel | Text till tal till en virtuell mikrofon: VB-Cable och VoiceMeeter (Windows), BlackHole och Loopback (Mac). Personen väljer kabeln som mikrofon, och agenten talar i personens plats. Billigt men ömtåligt. | Eget bruk |
| Mötesbot som tjänst | Recall.ai eller Meetstream.ai går med som egen deltagare med egen mikrofon. Betalas per minut. Att bygga själv kräver tre integrationer (Zoom, Teams, Meet). | Kunder |

Börja med ljudkabeln för eget bruk och byt till en mötesbot när det ska användas av kunder (bedömt 2026-04).
