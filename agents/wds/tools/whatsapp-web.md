---
name: whatsapp-web
source: wds
type: script
description: Läser en chatt i WhatsApp Web i tidsordning, med text och röstmeddelanden, och laddar ner den som filer. Läser bara, skickar och ändrar ingenting. Skriptet är whatsapp-web/collector.js och körs i webbläsarfliken.
used_by: []
---

# Tool: whatsapp-web

Hämtar hela chatten med en kontakt, så att den kan arkiveras och analyseras. WhatsApps egen lista över meddelanden är facit, så att inget saknas.

**Ännu ingen WDS-skill.** Arkivet (sammanfogning, utskrift av röstmeddelanden, läsbar version) görs tills vidare av projektets eget tool, till exempel `agents/welqora/tools/kommunikationsarkiv/` i welqora-analysis. Skillen för ett kommunikationsarkiv i WDS är inte skriven än; när den finns står den i `used_by:`.

## Förutsättningar

- WhatsApp Web är inloggat i personens Chrome, och agenten når fliken via webbläsarverktyget (`javascript_exec`).
- Chrome tillåter flera nedladdningar från web.whatsapp.com.
- Personen har sagt ja till att chatten arkiveras, och arkivet följer projektets policy för data och sekretess (`governance/`). Arkivet hamnar bara i ett privat repo.

## Åtgärder

Öppna web.whatsapp.com och chatten med kontakten. Kör sedan i fliken, ett anrop i taget. Varje anrop håller sig under cirka 38 sekunder så att det ryms i webbläsarverktygets tidsgräns.

1. **Installera:** klistra in hela `whatsapp-web/collector.js`. Svaret är `installed`.
2. **Facit:** `await __wa.list('<kontaktens namn>')` ger antal meddelanden och första och sista tid, ur WhatsApps lokala lagring.
3. **Texten:** `await __wa.collect()`, upprepat tills `missing` är 0.
4. **Röstmeddelandena:** `await __wa.voice()`, upprepat tills `voice` är lika med `of`. Varje röstmeddelande spelas ljudlöst en kort stund så att ljudfilen kan hämtas.
5. **Exportera:** `await __wa.export('<prefix>')` laddar ner två filer till Hämtade filer:
   - `<prefix>-messages.jsonl`: ett meddelande per rad med `n`, `id`, `time`, `t`, `from` (`me` eller `them`), `type` och `text`
   - `<prefix>-voice.json`: röstmeddelandena som base64, nycklade på meddelandets id

## Begränsningar

- Meddelandetexten är krypterad i WhatsApps lagring och läses därför från sidan. Listan över id och tider kommer ur lagringen.
- Video som "visas en gång" går inte att spara. Bilder, video och dokument laddas ned med WhatsApps egen nedladdning och sparas utanför repot.
- WhatsApp laddar inte äldre meddelanden när skriptet sätter scrollpositionen hårt, så `collect()` bläddrar stegvis och kan behöva köras flera gånger.

## Aldrig

- Skicka något i WhatsApp utan personens uttryckliga ja för det enskilda meddelandet.
- Spara exporten i ett publikt repo.
