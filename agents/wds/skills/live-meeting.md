---
name: live-meeting
source: wds
description: Agenten är med i ett pågående möte via Fireflies. Den dokumenterar beslut, åtgärder och frågor medan mötet pågår, faktakollar påståenden mot repot och webben, och svarar när någon frågar. Mötesanteckningen skrivs live i repot.
used_by: [idun, saga, freya, mimir]
version: 1.0
tools: [wds/meeting-live, wds/git]
---

# Live-möte: med i mötet, inte efteråt

Ett långt möte blir användbart först när det är dokumenterat, och ett påstående är värt mest medan det fortfarande går att fråga om det. Agenten lyssnar på hela mötet, skriver anteckningen medan mötet pågår och kontrollerar fakta under tiden. Personen kan hålla blicken på mötet och läsa anteckningen när det passar.

**Användning:** `/live-meeting`, eller `/live-meeting <projekt>` när anteckningen ska till ett visst projekt.

<workflow id="live-meeting">

  <constraints>
    - Agenten deltar bara i möten som Fireflies redan spelar in med deltagarnas vetskap.
    - Allt körs lokalt enligt [meeting-live-toolet](../tools/meeting-live.md). Ingen server, ingen MCP.
    - Råtexten stannar i `.wds/live/` (gitignorerad). I repot hamnar anteckningen, och råtexten bara om repots `AGENTS.md` säger att mötestexter sparas.
    - Personen sitter i ett möte. Chatten får bara korta rader: svar på frågor och motsägelser som spelar roll nu. Allt annat står i anteckningen.
    - Skilj på vad som sades och vad som stämmer. Ett påstående som inte gått att kontrollera står som det, aldrig som fakta.
  </constraints>

  <step id="1-join">
    Gå med i det senaste pågående mötet enligt toolet: `join` i bakgrunden, sedan bevakningen.
    Är Bitwarden låst eller inget möte igång: en rad om vad personen ska göra, enligt toolets feltabell.

    Bestäm var anteckningen ska ligga:
    - där repots `AGENTS.md` säger att möten dokumenteras, annars
    - i projektets input-mapp för den fas mötet matar, `projects/<projekt>/<fas>/input/<datum>-<titel>.md`.
    Oklart vilket projekt: fråga en gång, med ett förslag.
  </step>

  <step id="2-catch-up">
    Läs det som redan sagts (`transcript`). Skapa anteckningen med rubrikerna nedan och fyll i det som finns.
    Skriv en rad i chatten: att agenten är med, var anteckningen ligger och mötet så här långt i en mening.
  </step>

  <step id="3-follow">
    För varje klump nya repliker:

    1. **Uppdatera anteckningen** direkt, under rätt rubrik:

       | Rubrik | Innehåll |
       |---|---|
       | Deltagare | namn och roll, så fort de framgår |
       | Beslut | vad som beslutades och av vem |
       | Åtgärder | vem gör vad, och när |
       | Påståenden | påståendet, vem som sa det, tidpunkt i mötet, status och källa |
       | Öppna frågor | det som lämnades utan svar |
       | Förlopp | en kort rad per avsnitt av mötet, med tidpunkt |

    2. **Faktakolla** påståenden som spelar roll för beslut: siffror, datum, namn, påståenden om företag och personer, tekniska och juridiska påståenden. Sök först i repot (brief, tidigare möten, `communication/`, `people/`, `timeline.md` på den nivå de gäller), sedan på webben. Status är *bekräftat*, *motsägs* eller *inte verifierat*, alltid med källa.
    3. **Säg till i chatten** bara när ett påstående motsägs av en källa och det påverkar det som diskuteras, eller när någon i mötet riktar en fråga till agenten. En eller två rader.
    4. **När bevakningen löper ut,** starta den igen med samma kommando. Inget går förlorat.
  </step>

  <step id="4-close">
    När bevakningen visar att mötet är slut:

    1. Slutför anteckningen: en sammanfattning överst, med de tre viktigaste besluten och alla åtgärder.
    2. Kontrollera de påståenden som fortfarande står som *inte verifierat* en sista gång.
    3. Lägg en rad i projektets designlogg om mötet, med länk till anteckningen.
    4. Committa och pusha anteckningen och loggen (git-toolet).
    5. Visa sammanfattningen i chatten och fråga om något ska vidare till en annan agent. Det tas med wrap eller handoff.
  </step>

</workflow>
