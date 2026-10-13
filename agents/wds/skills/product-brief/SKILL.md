---
name: product-brief
description: Produces the WDS Product Brief suite through a discovery conversation. Use when a project needs its strategic foundation (why it exists, for whom, what success is) or when a brief needs updating.
used_by: [saga]
version: 2.0
tools: [wds/git]
---

# Product Brief

The Product Brief is the strategic foundation every later decision is checked against. A good brief lets Freya design and Mimir build without guessing why, and lets the client recognise their own business in it. It is written together with the person in conversation, one question at a time, because the brief's value is the understanding behind it, not the document.

## The suite

The brief is a suite in `projects/<project>/A-Product-Brief/` (the `output_folder` in `AGENTS.md`). The files are numbered in reading order: why and for whom, how it speaks, how it looks, and last what is built and within which limits, which leads on to the PRD. The numbers are fixed: a skipped document leaves its number free, nothing is renumbered, and new documents take 05, 06 and on.

| File | When |
|---|---|
| `01-product-brief.md` | Always |
| `02-content-language.md` | Brand voice, tone, language, SEO or content strategy came up. A short pointer to the tone of voice (`brand/tone-of-voice.md` at the level it serves, see `agents/wds/data/repo-structure.md`), plus what only applies to this project. If the voice exists, read it and discuss only what differs. |
| `03-visual-direction.md` | Design style, aesthetics, references, colour or typography came up. A short pointer to the visual identity (`brand/visual-identity/`), plus what only applies to this project. If the identity exists, read it and discuss only what differs. |
| `04-platform-requirements.md` | Something is to be built: platforms, integrations, limits, complexity, knowledge gaps. Strategic boundaries readable by the client, not a technical spec; the master PRD in `E-Development/` comes after it. |

The structure of each document is in [suite-templates.md](references/suite-templates.md). When no `brand/` exists yet and the voice or the visual direction is written for the first time, the company-wide part goes into `brand/` and only the project's own part into `02` or `03`.

## What the brief must cover

Before writing `01-product-brief.md`, you and the person have a confirmed understanding of each of these. The order is a sensible default, not a script: follow the conversation, and come back for what is missing.

| Topic | Understood when you can state |
|---|---|
| Vision | Why it exists and what change it creates |
| Positioning | Who it is really for, and why they would choose it over what they do today |
| Business model | How it makes money: B2B, B2C or both, and the pricing approach |
| Business customers | Only for B2B: who decides and buys, and how they differ from the daily users |
| Target users | Two or three behavioural profiles: what they try to get done and what stops them |
| Product concept | What kind of product it *is*, in one sentence, and its core structural idea |
| Success | What numbers change 12 months after launch, and the timeline |
| Alternatives | What people use instead, including doing nothing, and what is genuinely different |
| Constraints | The hard walls: technical, budget, time, regulation |

For the extensions, the same applies to: brand personality, tone of voice, languages, search intent and content structure (`02`); references, style, colour, typography and imagery (`03`); platforms, integrations, platform limits, complexity and open questions with an owner each (`04`). For `04`, build on the constraints already known and ask only for what is new.

## How the conversation goes

- **One question per message.** Reflect what you heard, check it, deepen it. The guide is [discovery-conversation.md](references/discovery-conversation.md).
- **Existing material first.** If the person has documents (a pitch, research, an old brief), read them before asking anything, show what you found per topic, confirm it, and ask only about the gaps. See [working-with-existing-materials.md](references/working-with-existing-materials.md).
- **Opening questions** that tend to work: "Why does this product exist? What change does it create?", "Who is this really for, and why would they choose it over what they do today?", "What does success look like 12 months after launch?", "What are the hard walls?" Use your own when the conversation calls for it.
- **For the extensions:** [content-structure-principles.md](references/content-structure-principles.md) and [seo-strategy-guide.md](references/seo-strategy-guide.md) for content and language, [strategic-documentation.md](references/strategic-documentation.md) for tone, [inspiration-analysis.md](references/inspiration-analysis.md) for visual direction. Taste's styles can serve as reference words in the visual conversation (`agents/wds/data/taste.md`), offered as examples, never as the answer.
- **Draft live.** Write the documents as the understanding grows, so the person sees them take shape, and mark what is not yet agreed.
- **Where in doubt, say so.** An answer the person was unsure of, or a claim nobody has checked, is written as such, never as fact.

## Done

The brief is done when the person has read the suite and agreed that it says what they mean.
- Every topic above is covered in `01`, and each triggered extension is written.
- Nothing in the suite is the agent's own idea presented as the client's.
- The design log (`_progress/00-design-log.md`) records the Product Brief as complete, and the project outline's phase is updated.
- The work is committed. The next step, usually the Trigger Map, is offered.
