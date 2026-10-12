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
| Python-paket | `python -m pip install "python-socketio[client]"` (en gång per dator) |
| Mötesfilen | `.wds/live/` i repots rot. `.wds/` är gitignorerad, så råtexten hamnar aldrig i git av misstag. |

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

### Avsluta

Stoppa bakgrundsprocessen. Joinen skriver själv en slutrad när mötet inte längre pågår i Fireflies (kontrolleras varje minut).

## Filformat

En rad per händelse, i ordning:

```json
{"event": "joined", "title": "…", "meeting_id": "…", "participants": ["…"], "at": "…"}
{"n": 1, "start": 3.2, "speaker": "Anna", "text": "…", "seed": true}
{"n": 2, "start": 61.0, "speaker": "Mårten", "text": "…", "id": "<chunk_id>"}
{"event": "ended", "reason": "…", "at": "…"}
```

`seed: true` är repliker från före anslutningen. `start` är sekunder från mötets början.

## Fel

| Vad som händer | Säg och gör |
|---|---|
| Bitwarden är låst | "Lås upp Bitwarden: `bw unlock`, och klistra in BW_SESSION." Skicka den i miljön per kommando, spara den aldrig. |
| `Inga pågående möten` | "Fireflies spelar inte in just nu. Starta inspelningen, så går jag med om 30 sekunder." |
| `auth failed` | Nyckeln är fel eller har gått ut. Kontrollera Bitwarden-posten. |
| `Paketet saknas` | Installera `python-socketio[client]` och gå med igen. |
| Bakgrundsprocessen avslutas oväntat | Läs dess utskrift, och gå med igen. Den nya filen får en ny tid i namnet; läs den gamla med `transcript`. |

Fördröjningen från tal till fil är några sekunder (Fireflies taligenkänning), plus bevakningens intervall.
