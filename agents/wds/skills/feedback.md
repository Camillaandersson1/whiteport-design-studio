---
name: feedback
description: Live feedback rounds. User browses and reports issues in natural language, agent captures every one as a structured FB-XX item in a round file and sorts it. No code changes until the user picks; then one item at a time, fix, test in the browser, update the file, ask for the next. Spec issues go through the spec first, then to Mimir as a spec delta. Use when the user says "I want to give feedback", "I have feedback", "let's review", or /feedback.
used_by: [freya, saga, mimir]
argument-hint: "[optional: area to focus on, e.g. 'checkout', 'home page']"
---

# Feedback — Live Review & Fix Rounds

## Overview

This skill turns live browsing sessions into structured fix plans with tracked outcomes. The user speaks freely while the agent does all the structuring, investigating, and fixing.

Every WDS agent can run it. Freya owns the spec route.

**Three rules:**

1. **Document first.** Every item goes into the round file as `FB-XX` with root cause and proposed fix. No code changes while the round is open, and none until the user has picked which item to take.
2. **One at a time.** Fix one item, test it in the browser, update the round file, then ask which one is next. No batches, no parallel fixes: with several fixes at once nobody can tell what worked.
3. **Spec before code.** Feedback never goes to code when the spec is what's wrong. Each item is either a **bug** (the spec is right, the code doesn't follow it: fix it) or a **spec issue** (the spec is wrong or missing something: change the spec first, then brief Mimir with the spec delta).

Users give feedback in bursts: spoken, fast, jumping between things. The round file catches all of it so nothing is lost between sessions, even though the fixing goes one by one.

---

## On Activation

1. Create a feedback file: `{output_folder}/E-Development/WO-{N}-{NN}-{area}-feedback.md`
   - Link it to the nearest relevant WO, or create a standalone one
   - Initialize with a header, date, reporter, and empty summary table

2. Respond:

```
I'm listening. Browsing or reporting?
```

If the dev server isn't running, start it. If the user is browsing live, follow along with screenshots.

---

## Feedback Loop

Repeat for each issue the user reports:

### 1. Receive

Let the user describe the issue in their own words. Any language. Do not interrupt. Do not ask for clarification you can find yourself in the code.

### 2. Investigate

Actively look for the issue:
- Read the relevant files — note file path and line number(s)
- Check git log for recent changes to affected areas
- If a browser is available, reproduce visually with screenshot
- Understand the root cause, not just the symptom
- Read the spec for the page (`{output_folder}/D-UX-Design/[page-slug].md`) and decide the **type**:

| Type | Meaning | Route |
|---|---|---|
| Bug | The spec is right, the code doesn't follow it | Fix (triage below) |
| Content gap | Something is missing from the spec | Spec |
| Content conflict | The spec says one thing, the feedback another | Spec |
| Behavior change | An interaction or state needs to change | Spec |
| Structure change | Layout, hierarchy or flow needs to change | Spec |
| Out of scope | New work, not in the current spec | Backlog |
| Unclear | Can't be mapped without more information | Ask one focused question |

### 3. Log

Add the issue to the feedback file immediately as `FB-{XX}`:

```markdown
## FB-XX: [Short title]

**Observed:** [What the user described]

**Root cause:** [What you found in the code]

**File:** `path/to/file.tsx:line`

**Type:** Bug | Content gap | Content conflict | Behavior change | Structure change | Out of scope

**Fix:** [Concrete change needed, or the spec change for spec issues]

**Severity:** Low | Medium | High
**Proposed:** [Self | Mimir | Codex | Spec | Deferred]
**Status:** Open
```

Update the summary table at the bottom of the file. Do not touch the code yet, not even for a one-line fix.

### 4. Acknowledge

Keep it short:

```
Noted — FB-XX. Next?
```

Do NOT summarize what they just said back to them. Do NOT give lengthy explanations unless asked.

---

## Proposed handling

Sort each item while logging it, as a proposal. Nothing is fixed during the round.

| Item | Proposed |
|-----------|--------|
| Bug, small (CSS, label, < 20 lines) | Self. Visual fixes follow `../data/taste.md` |
| Bug, architectural or multi-file | Mimir or Codex, still one item at a time |
| Spec issue | Spec (see "Spec issues" below) |
| Needs a design decision | Open, discuss with the user |
| Not needed now | Deferred, with the reason |

---

## When the User Is Done

### 1. Present and commit the round

Show the summary table: every FB-XX with its type, severity and proposed handling. Commit the round file:

```
git add [round file]
git commit -m "docs: capture feedback round FB-01 through FB-XX"
```

Ask: "Which one first?" Wait. The user picks; do not start on your own priority order.

### 2. One item at a time

For the item the user picked:

1. **Fix it.** Yourself, or hand that one item to Mimir/Codex with the exact file paths, what to change and why, and no other files to touch. Wait for it to finish.
2. **Test it in the browser.** Reload, walk the affected flow, screenshot. A fix is not done until it is visually confirmed. Check that nothing next to it broke.
3. **Update the round file:** status Fixed (or what happened instead), what changed, the file and line.
4. **Commit** that one item: `fix: FB-XX <short title>`.
5. **Ask:** "FB-XX done. Next?"

Spec items follow the same order: when the user picks one, run it through "Spec issues" below before any code.

New feedback that comes up while fixing goes into the round file as a new FB-XX, and waits its turn.

---

## Spec issues

Handled when the user picks them, page by page. The spec is the source of truth.

1. **Analyse.** Group the spec items per page and present them: "[Page]: [item] → [type]: [what changes in the spec]". Out-of-scope items listed separately. Wait for confirmation.
2. **Propose the edit.** Per change: section, before, after. Wait for explicit approval. Never update the spec before it.
3. **Update the spec** with [spec-writer](../freya/subagents/spec-writer.md) in update mode: only the approved changes, nothing else rewritten.
4. **Brief Mimir** with [mimir-brief](../freya/subagents/mimir-brief.md): the approved spec changes, the affected pages and acceptance criteria. The original feedback is context only. Mimir builds from what the spec now says, not from what anyone felt.
5. **Close.** Mark the FB items done in the feedback file, log it in the design log (feedback received, spec updated, Mimir briefed), and offer to add out-of-scope items to the backlog.

---

## Feedback File Format

```markdown
# WO-{N}-{NN} — {Area} Feedback

**Status:** Open | Complete
**Reporter:** [name]
**Date:** [YYYY-MM-DD]
**Context:** [what was being reviewed]

---

## FB-01: [Title]

**Observed:** ...
**Root cause:** ...
**File:** `path/to/file.tsx:line`
**Fix:** ...
**Severity:** Low | Medium | High
**Proposed:** ...
**Status:** Open | Fixed | Spec updated | Deferred

---

## Summary

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| FB-01 | ... | Low | Fixed |
| FB-02 | ... | High | Open |

---

_Feedback collected by [agent] — Whiteport Design Studio_
```

---

## Tone

Stay in character. Keep responses short during the listening phase — one-line acknowledgments, not paragraphs. The user is in flow and doesn't want to read essays between observations.

Save the full summary for after they say they're done.

---

## Key Principles

1. **Never disable the user's flow.** Capture fast, investigate async.
2. **Document first, fix later.** The whole round is written down before any code changes, and the user picks what to take.
3. **One item at a time.** Fix, test in the browser, update the file, ask for the next. Never batch, never parallel.
4. **Spec before code.** A spec issue changes the spec first. Only bugs go straight to code.
5. **Verify in browser.** Fixes aren't done until they're visually confirmed.
6. **The feedback file is the source of truth.** Everything tracked there, not in conversation memory.
