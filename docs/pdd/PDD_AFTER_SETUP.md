# PDD After Setup: Stay in Prompt Space

This guide answers the practical question that begins after a repository has
been configured for Prompt-Driven Development:

> What does the human say, what does the AI agent maintain, and what did Greg
> Tanaka mean by “Where is your prompt file?” and “stay in prompt space”?

The short answer is:

> The human may keep talking in ordinary language. The AI agent turns accepted
> meaning into one or more versioned PDD `.prompt` files, presents their
> behavioral meaning for approval, then regenerates and verifies the affected
> software. User stories and tests independently check that the prompts and
> software still deliver the intended outcome.

The human does **not** need to hand-author formal prompts or user-story syntax.
But a PDD-managed part of the product does need a durable `.prompt` file. If the
intent exists only in chat, a PRD, a ticket, or generated code, the work has not
yet fully entered PDD's prompt space.

## Three meanings of “prompt”

The overloaded word *prompt* causes much of the confusion.

### 1. Intent message

This is what the human types, dictates, pastes, or says to an AI agent:

> Merge pressure-limit intervals that are separated by less than two seconds.

It may be rough, incomplete, conversational, or one correction in a longer
discussion. This is valid **input**, but chat history alone is not durable PDD
source.

Call this an **intent message** or **request** when precision matters.

### 2. Product Intent document

This is an optional but useful current, consolidated explanation of the product
or larger change. A friendly conventional name is:

```text
docs/PRODUCT_INTENT.md
```

Its first heading can be:

```markdown
# Product Intent (PRD)
```

“Product Intent” is easier to understand than “product requirements document,”
while “PRD” in the heading preserves the familiar project-management term.
This document can contain users, goals, workflows, constraints, non-goals,
examples, and unresolved questions.

The Product Intent document is the human-readable map of the product. It is
useful, especially for a new product or a large change, but it is not required
for every small request and is not the file PDD compiles for each software
component.

### 3. PDD prompt file

This is a versioned file such as:

```text
prompts/pressure_trace_analyzer_python.prompt
```

It is source specification for a bounded logical part of the product. The
project's prompt suite collectively governs the project. A logical part may
produce one file or a coherent artifact bundle such as a C++ header and source
file, although current PDD `0.0.309` implements each primary output as a
separate prompt/architecture entry. The prompt source should state the part's
purpose, interface, dependencies, requirements, constraints, examples,
outputs, and important `MUST NOT` behavior.

This is the prompt Greg was asking about. PDD's own README calls `.prompt`
files its human-authored source language, and its doctrine calls prompts the
primary artifact. An AI agent may draft and maintain the file, but the file
must exist, be versioned, and remain reviewable.

## The four durable layers

The recommended model is:

```text
ordinary human intent messages
              |
              v
Product Intent (optional whole-product, human-readable current truth)
              |
              v
versioned PDD .prompt files (source for each generated part)
              |
              v
generated implementation

user stories + contracts + tests
              |
              +---- independently check the prompts and behavior
```

Each layer has a different job:

- **Intent messages** are the easy human input.
- **Product Intent** consolidates the current product-level meaning.
- **PDD `.prompt` files** are the source PDD uses for separately generated
  parts.
- **User stories, contracts, and tests** are independent acceptance and
  verification assets. They do not replace the PDD prompts.

If these disagree, the agent must stop and reconcile the meaning before
regeneration. It must not quietly pick whichever file is most convenient.

## What “stay in prompt space” means

It means making durable behavior changes at the level of intent before treating
generated code as the answer.

For a PDD-managed part:

1. Change or clarify the relevant `.prompt` file.
2. Add or update independent tests and, when valuable, a user story.
3. Regenerate or synchronize the implementation.
4. Verify the result.
5. Put discoveries made during implementation back into the prompt or tests.

It does **not** mean:

- the human must learn prompt-file syntax;
- every chat message becomes a new `.prompt` file;
- all requests must be rewritten as user stories;
- one enormous prompt should contain the whole repository;
- every physical file boundary is automatically a good prompt boundary;
- a PRD alone is sufficient;
- generated code may never be inspected or temporarily patched while
  diagnosing a problem.

Exploration can happen in code or chat. The important discipline is that a
durable decision must not remain only there. Before the PDD change is complete,
the accepted behavior must be back-propagated into the relevant prompt and
verification assets.

## What happens after setup

After one-time PDD adoption, the human can continue naturally:

> Add a visual warning for out-of-limit intervals.

> Actually, merge gaps shorter than two seconds.

> Remove CSV export.

> Never modify the uploaded samples.

For each material request, the AI agent should:

1. **Understand the change.** Classify it as an addition, clarification,
   correction, removal, example, constraint, or observed bug.
2. **Preserve it.** Update Product Intent when the request changes
   product-level current truth and, when useful, preserve the original request
   in a dated request record.
3. **Find the affected part.** Inspect the architecture and existing prompts;
   do not ask the human for a “dev unit.”
4. **Update prompt source.** Add, modify, or remove the requirement in the
   affected `.prompt` file. If no suitable prompt exists, use the PDD
   architecture/change workflow to create or split one.
5. **Add independent coverage selectively.** Create or update a user story for
   an important user outcome, cross-part behavior, regression, or critical
   `MUST`/`MUST NOT` rule. Do not manufacture a story for every sentence.
6. **Strengthen tests.** Preserve passing tests and add observable positive and
   negative checks.
7. **Regenerate and verify.** Use the installed PDD workflow for only the
   affected part, then run repository tests.
8. **Report meaning and evidence.** Explain what changed in the prompt, what
   was generated, what tests passed, and what remains uncertain.

No recurring magic phrase is required. The repository's agent instructions
make this the default behavior for PDD-managed parts.

## Do not keep an unorganized pile forever

A pile of rough prompts is a perfectly good inbox. It is a poor long-term
specification because later messages can silently contradict earlier ones.

The agent should preserve history without confusing history with current truth:

```text
docs/
├── PRODUCT_INTENT.md
└── requirements/
    └── requests/
        └── YYYY-MM-DD-<short-description>.md
```

- `PRODUCT_INTENT.md` says what is currently intended.
- Dated request records explain how that intent changed.
- `prompts/*.prompt` carry the current requirements into generated parts.

If the repository already has equivalent locations, use them rather than
creating a second system.

## When to create a user story

A user story is useful when it supplies an independent acceptance-level oracle:

- a user-visible outcome;
- behavior spanning multiple generated parts;
- a critical edge case or regression;
- a safety, security, or data-integrity `MUST NOT`;
- behavior a human should be able to read and approve.

A story is not automatically required for:

- a wording clarification that does not change behavior;
- a small implementation repair already required by the prompt;
- routine maintenance with no meaningful user outcome;
- every individual sentence in Product Intent.

PDD's user-story methodology deliberately derives a story from independent
issue or request text rather than from the prompt or generated code. That
independence lets the story detect prompt drift. This is why the story is a
check on the prompt, not the main prompt itself.

## Feature, correction, removal, and bug routing

| Human meaning | Durable agent action |
|---|---|
| New product behavior | Update Product Intent when product-level; update or create the affected `.prompt`; add story/tests when valuable; regenerate |
| Correction to desired behavior | Reconcile the current intent; replace the affected prompt rule; update impacted story/tests; regenerate |
| Intentional removal | Mark the old request/story retired when applicable; remove the behavior from Product Intent and prompt; intentionally update tests; regenerate |
| New example or boundary | Add it to the prompt or grounding and encode an observable test when feasible |
| Current code violates an existing prompt | Reproduce with a failing test and fix/synchronize; change the prompt only if the intent itself is missing or wrong |
| Pure implementation detail with unchanged behavior | Keep it out of product stories; update the prompt only if the detail is a durable constraint |

Omission is not removal. A later short message must not silently erase earlier
accepted requirements.

## A concrete example

The human says:

> I want uploaded pressure traces to highlight readings outside a permitted
> band. Never alter the original data.

The agent may:

1. Add the capability and data-integrity rule to `docs/PRODUCT_INTENT.md`.
2. Create or update
   `prompts/pressure_trace_analyzer_python.prompt`, including its input/output
   interface and an explicit `MUST NOT` modification rule.
3. Draft one human story about locating out-of-limit intervals.
4. Add a negative test proving the input samples remain unchanged.
5. Regenerate the analyzer and run the focused tests.

Later the human says:

> Merge intervals separated by less than two seconds.

The agent should update the existing Product Intent and analyzer prompt, add
boundary examples/tests around exactly two seconds, and regenerate that part.
It should not create an unrelated component or require the human to name a PDD
command.

## What the human reviews

The human's highest-value review is meaning:

- Does Product Intent describe the product actually wanted?
- Does the agent's summary of each affected prompt preserve that meaning?
- Are the examples, limits, and `MUST NOT` rules correct?
- Do the user stories describe valuable outcomes?
- Does the reported evidence prove the important behavior?

The human need not author `.prompt` syntax, but a prompt is not an ignorable
generated byproduct. It is the source that will recreate the code.

For each meaningful prompt change, the agent should present:

- the affected part and purpose;
- inputs and outputs;
- behavior added, changed, or removed;
- `MUST` and `MUST NOT` rules;
- important examples and edge cases;
- dependencies and unresolved assumptions;
- tests that provide evidence.

The product/domain human approves this meaning. A technical owner reviews the
actual prompt diff, interfaces, dependencies, and critical tests. For routine,
low-risk work those may be different people; when one person fills both roles,
that person can review the plain-language summary first and inspect the
consequential prompt sections directly.

The short human story should also be read and approved, but it is not sufficient
by itself. It checks one outcome; the prompt contains the fuller specification
that governs regeneration.

The AI agent is the editor; PDD is the build and verification layer; the human
owns product intent and consequential decisions. See
[`PDD_VIDEO_CLEAR_WALKTHROUGH_NOTES.md`](PDD_VIDEO_CLEAR_WALKTHROUGH_NOTES.md)
for the full artifact-by-artifact review matrix.

## Agent rule to copy into a repository

```text
For every PDD-managed part, treat ordinary user messages as intent intake, not
as durable source by themselves. Maintain Product Intent when product-level
current truth needs it, and maintain versioned PDD .prompt files for generated
parts. Propagate each accepted behavior change into the affected .prompt before
completing implementation. Use user stories and tests as independent acceptance
checks; do not substitute stories or a PRD for the component prompt. Regenerate
and verify only the affected parts, and report meaning-level prompt changes
plus test evidence. Do not require the user to write formal prompts, stories,
PDD commands, or internal component names.
```

## Source basis

This model was checked against the local PDD fork at commit `17b41a779`
(PDD `0.0.309`), especially:

- `README.md`: `.prompt` files are the source language and generated code is
  not the primary source of truth;
- `docs/prompt-driven-development-doctrine.md`: prompts are the primary
  artifact, regeneration is the default for strong-fit work, and
  implementation learnings must be back-propagated;
- `docs/prompting_guide.md`: for a new feature, update prompt contract rules,
  update product-level stories when useful, regenerate, and test;
- `docs/generating_user_stories.md`: a story is an independent behavioral
  oracle derived separately from the prompt/code so it can detect drift.

Those sources establish the key distinction: Product Intent and user stories
support PDD, but the versioned `.prompt` is the central source artifact for the
generated part.

The official-channel video
[`Prompt Driven Development: A Clear Walkthrough`](https://youtu.be/esZhNrUrul8)
reinforces this with its “prompt and tests are the mold” explanation. Analysis
and transcript archive details are in
[`PDD_VIDEO_CLEAR_WALKTHROUGH_NOTES.md`](PDD_VIDEO_CLEAR_WALKTHROUGH_NOTES.md).

The companion video
[`Prompt Driven Development Intro`](https://youtu.be/UsdgyHBFE0g) repeats the
one-prompt/one-file claim. Our refined prompt-graph and C++ artifact-bundle
policy is documented in
[`PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md).
