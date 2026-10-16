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
python agents/wds/tools/meeting-live/live.py watch .wds/live/<fil>.jsonl --every 30
```

Bevakningen skriver ut `== MÖTET ÄR SLUT: <skäl> ==` och avslutas när Fireflies slutar spela in, och `== FEL: … ==` om något går fel.

**Copilot och Codex** har ingen bevakning som väcker dem. Läs nya rader med `transcript` när personen frågar, eller mellan varje svar.

### Hela mötet som text

```bash
python agents/wds/tools/meeting-live/live.py transcript .wds/live/<fil>.jsonl
```

### Lokal reserv (fel språk, eller Fireflies spelar inte in)

Lyssnar på datorns ljud ut och mikrofonen och skriver ut lokalt med Whisper var 15:e sekund, i samma format. Ljudet lämnar aldrig datorn. Windows. Svenska använder KB-Whisper, som laddas ned första gången (några minuter). Kör i bakgrunden och bevaka filen med `watch` som vanligt:

```bash
python agents/wds/tools/meeting-live/local.py .wds/live/<tid>-lokal.jsonl --them "<de andra>" --me "<personen>" --lang sv
```

Talarna skiljs bara åt som "de andra" och "jag". Använd den när Fireflies transkriberar på fel språk (då blir texten obegriplig redan första minuten) eller inte kommer igång.

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
