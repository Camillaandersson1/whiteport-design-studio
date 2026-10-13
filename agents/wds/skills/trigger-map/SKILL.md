---
name: trigger-map
description: Builds the WDS Trigger Map in workshops with the person: business goals, personas with driving forces, the four-layer map and feature impact. Use when the product brief exists and the project needs to know whom it serves and what drives them, or when a trigger map needs updating.
used_by: [saga]
version: 2.0
tools: [wds/trigger-map-render, wds/git]
---

# Trigger Map

The Trigger Map connects what the business wants to what drives the people it depends on: business goals → the product → target groups → their driving forces. Freya designs the scenarios from it, and every later choice can be checked against it: which person does this serve, and which force does it answer? It is built in workshops with the person, because the forces have to be recognised, not invented.

It needs the product brief (`A-Product-Brief/01-product-brief.md`). Without it, start there.

## Content and form are kept apart

The content lives in one data file, `B-Trigger-Map/trigger-map.yaml`. The documents, the map and the persona pages are **rendered** from it with [trigger-map-render](../../tools/trigger-map-render.md), so every trigger map has the same template and the client's visual identity, or the neutral WDS look until the client has one. You write the data and render; you never write or edit the rendered files by hand.

An existing map written by hand is brought in with the tool's `import` before you change it.

## The workshops

One workshop at a time, one question at a time. Write each result into the data file and render as soon as the person confirms it, so they see the documents grow.

| Workshop | Done when the data file holds |
|---|---|
| 1. Business goals | A vision in one or two sentences, and three goals, the primary outcome first, then the two that make it possible. Each goal has three SMART objectives with a target. Goals are directions that last; objectives are measurable and dated. |
| 2 to 4. One persona each | An alliterative name (Harriet the Hairdresser), priority, who they are, how they think, what they feel, how they come to the product, three to five forces toward and three to five away from, each as WHAT + WHY + WHEN and scored Frequency + Intensity + Fit (1 to 5 each), and how they serve each goal. Highest strategic value first. |
| 5. Feature impact | Features derived from the strongest forces, each scored 0 to 3 against the forces it serves, with what it means for the design. Saga derives this herself and presents it for review. |

Good openings: "What does winning look like for this business, not in numbers but as a vision?", "What has to be true for that to happen?", "How will you know you have achieved it?", "Tell me about [Name]'s world", "What would make [Name] feel they have won?", "What is [Name] most afraid of here?". Follow the person rather than the list. Method and examples: [trigger-mapping.md](references/trigger-mapping.md).

## What makes it good

- **Only what came out of the conversation.** No invented psychology. Where Saga proposes something from the material before a workshop, the status says so and the person confirms or changes it.
- **Forces are specific.** "Figures he can't check, when he reads the deck, because one unverifiable figure makes him doubt them all" says something a generic "wants trust" never does.
- **Scores are honest.** A 15 is rare. The scores decide what Freya designs for first.
- **No trigger points or success states.** They belong in the UX scenarios.
- **The key read** says in a sentence or two what the pattern of the strongest forces means for the design.

## Done

- `trigger-map.yaml` holds every workshop, and the rendered files are current.
- The person has read the map and the persona pages and agreed.
- The design log records the Trigger Map as complete, and the project outline's phase is updated.
- The work is committed. Saga offers the handover to Freya for the UX scenarios.
