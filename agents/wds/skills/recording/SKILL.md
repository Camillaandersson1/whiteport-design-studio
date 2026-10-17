---
name: recording
description: Spelar in allt som hörs, och på begäran det som syns, på personens dator, skriver ut det live och grundligt efteråt, och sparar det personen väljer i rätt projekt. Använd när personen säger "starta inspelning", vill ha ett samtal, ett möte, en video eller ett webbinarium utskrivet, eller vill att agenten följer det som visas på skärmen.
used_by: [idun, saga, freya, mimir]
version: 1.0
tools: [wds/meeting-live, wds/git]
---

# Inspelning

Ett samtal är värt mest när allt finns kvar: vad som sades, vad som visades och vad som bestämdes. Inspelningen sker på personens egen dator, utan bot i mötet, så den fungerar i alla samtal och på alla plattformar (Meet, Teams, Zoom, Messenger, telefon via datorn) och för allt annat ljud, som videor och webbinarier. Ljudet tolkas på datorn. Allt spelas först in privat; det personen vill behålla flyttas sedan till rätt projekt.

Hur det görs står i [meeting-live-toolet](../../tools/meeting-live.md): `local.py --dir` för inspelningen, `refine.py` för den grundliga utskriften och `live.py archive` för arkivet.

## Starta

När personen säger "starta inspelning":

1. **Fråga en sak:** skärm och ljud, eller bara ljud? Bara datorns ljud (`--no-mic`) passar en video eller ett webbinarium.
2. **Mappen:** `recordings:` i `.wds/me.md` säger var personens inspelningar ligger, till exempel personens egen Google Drive. Saknas raden: föreslå en plats i personens privata Drive, fråga en gång och skriv svaret där. Skapa aldrig något i Drive innan platsen är bekräftad. Varje inspelning får en egen mapp: `<datum>_<tid>-<kort titel>`.
3. **Starta** inspelningen i bakgrunden och bevaka utskriften, enligt toolet. Säg i en rad att den är igång och vad som spelas in.

Alla i samtalet vet att det spelas in. Det är lagligt att spela in ett samtal man själv deltar i; i arbetssammanhang säger personen till de andra att en agent läser med, eftersom texten går vidare till en AI-tjänst. Om privata samtal bestämmer personen själv.

## Under inspelningen

Inspelningen går vidare tills personen säger stopp, också när ingen säger något och när ingen sitter vid datorn: ljudet är lika långt som inspelningen, och datorn hålls vaken. Locket ska vara öppet. Följ samtalet som i [live-meeting](../live-meeting.md): korta rader i chatten bara när någon frågar något eller något behöver sägas nu. Med skärmen igång finns en bild för varje gång skärmen ändrats (`== Bild … ==` i bevakningen). Titta på den när det som sägs hänger på det som visas: en siffra i en presentation, ett dokument, en sajt.

## Stoppa

När personen säger "stoppa":

1. **Stoppa ordentligt** genom att lägga filen `STOP` i inspelningens mapp, så att ljud och video avslutas hela.
2. **Den grundliga utskriften:** kör `refine.py` på mappen. Säg ungefär hur lång tid den tar, och gör den i bakgrunden.
3. **Fråga vad personen vill spara och i vilket projekt.** Föreslå projektet utifrån vad samtalet handlade om och vilka som var med. Valen:
   - utskriften i projektets mötesarkiv (`live.py archive` med `final.jsonl`, i projektets repo)
   - ljudet och skärmvideon i projektets mapp i Drive (flytta, inte kopiera)
   - en sammanfattning med beslut, åtgärder och öppna frågor (som i live-meeting, steg 4)
   - ingenting: det ligger kvar privat, eller raderas om personen säger det
4. **Gör det som valdes,** committa i projektets repo och säg i en rad var allt hamnade.

Media hör aldrig hemma i git: ljud och video ligger i Drive, utskrift och sammanfattning i repot.
