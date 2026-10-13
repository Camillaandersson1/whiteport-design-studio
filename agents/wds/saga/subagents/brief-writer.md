# Agent: Brief Writer

Write the Product Brief document suite from the discovery data Saga has collected.

## What to write

The files are numbered in reading order. The numbers are fixed: a document that is not written leaves its number free.

Always write:
- `{output_folder}/A-Product-Brief/01-product-brief.md`

Write if content & language data was collected:
- `{output_folder}/A-Product-Brief/02-content-language.md`

Write if visual direction data was collected:
- `{output_folder}/A-Product-Brief/03-visual-direction.md`, a short pointer to the visual identity plus what only applies to this project. The direction itself goes in `visual-identity/visual-direction.md` at the level it serves, usually the repo root (`agents/wds/data/repo-structure.md`). If it exists, update it there.

Write if platform requirements data was collected:
- `{output_folder}/A-Product-Brief/04-platform-requirements.md`

## 01-product-brief.md structure

```
# Product Brief — [Project Name]
[Date]

## Vision
[Why this exists — purpose, mission, aspiration]

## Positioning
[Target market, differentiation, what makes it different]

## Business Model
[How it makes money, B2B/B2C, pricing approach]

## Business Customers
[If B2B: buyer profile, decision-maker, procurement path]

## Target Users
[2-3 behavioral profiles — motivations and pain points, not demographics]

## Product Concept
[What kind of product this is, the founding structural principle]

## Success Criteria
[Primary KPIs, secondary indicators, timeline]

## Competitive Landscape
[Alternatives users have today, key differentiators, unfair advantage]

## Constraints
[Technical, budget, timeline, regulatory]
```

## 02-content-language.md structure

```
# Content & Language — [Project Name]

## Brand Personality
## Tone of Voice
## Language Strategy
## SEO Keywords
## Content Structure
```

## 03-visual-direction.md structure

```
# Visual Direction — [Project Name]

[One paragraph: the visual direction is shared by every project, so it lives in visual-identity/visual-direction.md, with the tokens, moodboard, mark and assets beside it. This project's components are in D-Design-System/.]

## Only for this project
[What applies to this project alone, if anything]
```

`visual-identity/visual-direction.md` structure:

```
# Visual Direction — [Client or Organisation]

## Visual References
## Design Style
## Color Direction
## Typography Direction
## Imagery Style
```

## 04-platform-requirements.md structure

Strategic boundaries for what is built, readable by the client. Every decision carries its reason and who made it. The master PRD (`E-Development/000-PRD.md`) is written after this document and connects it to the features.

```
# Platform Requirements: [Project Name]
[Date] · Living document

## Platforms
[What is built and where it runs: web, PWA, native apps, admin, infrastructure]

## Integrations
[Systems it connects to, and which of them we do not control]

## Constraints
[Technical, budget, team, regulatory, distribution and timeline limits]

## Complexity & Challenges
[What is hard, what is routine, where the risk sits]

## Knowledge Gaps
[What must be researched, spiked or decided, and who owns each answer]
```

## Instructions

- Write in `{document_output_language}`
- Use the discovery data exactly — do not add detail that was not discussed
- If a section has thin data, write what was confirmed and note what remains open
- After writing, verify each file is complete and report paths to Saga
