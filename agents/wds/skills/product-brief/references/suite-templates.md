# Product Brief suite: the documents and their structure

What each document in the suite contains. Read it when you write or update a document.

## What to write

The files are numbered in reading order. The numbers are fixed: a document that is not written leaves its number free.

Always write:
- `{output_folder}/A-Product-Brief/01-product-brief.md`

Write if content & language data was collected:
- `{output_folder}/A-Product-Brief/02-content-language.md`, a short pointer to the tone of voice plus what only applies to this project. The voice itself is the company's and goes in `brand/tone-of-voice.md` at the level it serves, usually the repo root (`agents/wds/data/repo-structure.md`). If it exists, update it there.

Write if visual direction data was collected:
- `{output_folder}/A-Product-Brief/03-visual-direction.md`, a short pointer to the visual identity plus what only applies to this project. The direction itself goes in `brand/visual-identity/visual-direction.md` at the level it serves, usually the repo root. If it exists, update it there.

When no `brand/` exists yet and you write the voice or the visual direction for the first time, write the company-wide part into `brand/` and only the project's own part into the project file.

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

[One paragraph: the voice is the company's, so it lives in brand/tone-of-voice.md. This page adds only what is the project's own.]

## Language Strategy
## SEO Keywords
## Content Structure
```

`brand/tone-of-voice.md` structure:

```
# Tone of Voice — [Client or Organisation]

## What We Believe
## Brand Personality
## How We Sound
## Words We Use
## How We Tell the Story
```

## 03-visual-direction.md structure

```
# Visual Direction — [Project Name]

[One paragraph: the visual direction is shared by every project, so it lives in brand/visual-identity/visual-direction.md, with the moodboard, mark and assets beside it, and the tokens in brand/design-system/. This project's own components are in D-Design-System/.]

## Only for this project
[What applies to this project alone, if anything]
```

`brand/visual-identity/visual-direction.md` structure:

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
