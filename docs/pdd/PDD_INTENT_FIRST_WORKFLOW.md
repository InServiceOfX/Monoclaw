# PDD for Humans: Intent In, Evidence Out

This document resolves an easy and reasonable source of confusion in
Prompt-Driven Development:

- the official introductory videos say that humans control **prompts and
  tests**;
- the current PDD CLI also introduces **user stories**, generated contracts,
  `.pddrc`, `architecture.json`, prompt paths, development units, and several
  commands.

Both descriptions can be true, but they are different layers of the system.
The current CLI exposes too many of those layers to a new user at once.

The confusion is also present in the current written product surface, not just
in the reader's interpretation. `docs/generating_user_stories.md` in PDD
labels the story file as human-owned and “edited by a person, by hand,” while
the agent-oriented workflow can draft that story and ask the human only to
approve or correct its meaning. The durable artifact needs human authority; it
does not require human keystrokes. Future PDD documentation should state that
distinction explicitly.

## The shortest correct explanation

The human owns:

1. **Intent:** what the product should and should not do.
2. **Acceptance:** whether the agent understood that intent.
3. **Evidence:** what observations or tests would make the human believe it
   works.

The AI agent and PDD own the mechanics:

1. preserving the original request;
2. updating the appropriate `.prompt` source;
3. maintaining `.pddrc`, `architecture.json`, names, paths, and dependencies;
4. deciding whether an independent user story is useful;
5. generating or updating tests and code;
6. running the checks and reporting honest evidence.

The human retains authority over prompts and tests without having to type their
file formats. **Control means approving meaning and proof, not performing every
keystroke.**

For ordinary use, the interface should feel like:

```text
human intent -> agent interpretation -> human correction/approval
             -> prompt/test/code mechanics -> evidence
```

## Why prompts and tests are not always sufficient by themselves

The videos accurately describe the core PDD mold:

- a versioned prompt specifies the software;
- tests constrain its observable behavior;
- generated code can be replaced from that mold.

But suppose an agent misunderstands the original request while writing the
prompt. If it then derives tests from the same misunderstood prompt, the prompt,
tests, and generated code can all agree with one another and still implement
the wrong product.

For a mechanical analogy, imagine that the customer needs a shaft to fit a
12 mm assembly. An erroneous engineering drawing says 10 mm, and an inspection
gauge is then made from that same drawing. Every manufactured shaft can pass the
10 mm gauge while still failing the customer's actual need.

The PDD user story is intended to be an independent check against that circular
agreement. PDD's own guide describes it as an **independent oracle** authored
from the original issue or request, never from the prompt or generated code.
It can therefore detect that the technical mold drifted away from what the
person originally asked for.

This gives the artifacts different jobs:

```text
Original request        what the person actually said
Accepted interpretation what the person confirms they meant
PDD prompt              technical, regenerable specification
Tests                   executable behavioral evidence
User story              independent acceptance check against the request
Generated code          replaceable implementation
```

The story is not a second programming language and is not the main compiler
input. It is a small acceptance checkpoint.

## Why Greg could ask about both prompt files and user stories

These questions test different failure modes:

- “Where is your prompt file?” asks whether the desired behavior has become
  durable PDD source rather than remaining only in chat or a code patch.
- “Did the human check the user story?” asks whether the system's short
  interpretation still matches the human's original intent.
- “What tests prove it?” asks whether the claimed behavior has executable or
  observable evidence.

A team may have one person perform all three reviews, but the roles are still
different. A product or domain expert may be well qualified to approve the
meaning and examples without being the person who reviews interfaces, test
isolation, or exact `.prompt` syntax.

## What the human actually has to modify

For normal, agent-assisted use, the human must not be required to manually edit
any PDD-specific file.

| Artifact | Human's normal responsibility | Manual file editing required? |
|---|---|---|
| Typed or dictated request | Explain the need, corrections, examples, constraints, and priorities | This is the primary human input |
| Accepted interpretation or review card | Say “yes,” correct it, or answer a consequential open question | No; conversation is enough |
| Product Intent / PRD | Approve important whole-product meaning when one is useful | No; the agent may maintain the Markdown |
| Human user story | Confirm that the short acceptance meaning is right when a story is warranted | No; tell the agent what is wrong and it edits the file |
| `.prompt` files | Approve consequential behavior; a technical owner reviews important interfaces and constraints | No syntax editing required |
| Tests | Supply important examples and judge claimed outcomes; a technical owner reviews critical coverage | No test-code editing required |
| `.pddrc` | None in ordinary use | No |
| `architecture.json` | Approve consequential architecture decisions, not JSON mechanics | No |
| Generated story contract | None; do not hand-edit it | No |
| Generated code | Acceptance and review proportional to risk | No for routine use; expert review remains necessary for high-risk code |
| Logs and evidence | Decide whether the result is convincing and what remains uncertain | No |

“No manual editing required” does not mean “humans should never inspect it.”
The exact prompt, test, architecture, or generated code should be inspectable.
It means knowledge of filenames, schemas, command flags, and directory layouts
is not the price of admission.

## User stories should be selective, not mandatory paperwork

Do not generate a story merely because another message arrived.

A separate story is valuable when the request describes:

- user-visible acceptance behavior;
- behavior spanning several generated parts;
- a regression that must never return;
- a critical `MUST` or `MUST NOT`;
- an outcome whose independent statement could expose prompt drift.

A story is often unnecessary for:

- a spelling correction;
- internal refactoring with no behavior change;
- a mechanical dependency update;
- a temporary experiment;
- a tiny prompt clarification already proven by focused tests.

When a story is useful, the agent should draft it from the preserved original
request, show its meaning to the human, and let the human approve or correct it
in conversation. The user should not need to know `pdd story add`,
`--devunit`, `--prompt`, the story slug, or its output path.

## One human-facing review card

Instead of presenting every internal artifact, the agent should normally show
one compact review card:

```text
What I heard:
What will change:
What must stay unchanged:
Important examples:
How we will prove it:
Affected product areas:
Open decisions:
```

The human only needs to correct the card's meaning. After acceptance, the agent
can translate it into the repository's Product Intent, prompt graph, selective
story coverage, tests, architecture metadata, and generated artifacts.

For low-risk changes, explicit approval may be unnecessary when the request is
unambiguous and the resulting diff is easy to reverse. For consequential,
ambiguous, expensive, security-sensitive, or safety-sensitive changes, the
agent must pause on the review card or the specific unresolved decision.

## The current CLI is too exposed

Today a new user can encounter all of these choices:

- `pdd generate`, `pdd change`, `pdd story`, `pdd test`, and `pdd sync`;
- GitHub issue URL, local file, or inline text;
- greenfield versus existing-project workflows;
- prompt paths and “dev units”;
- story, contract, regression, and output paths;
- `.pddrc` and `architecture.json`.

Those concepts remain useful to PDD implementers and advanced operators. They
should not all be first-class decisions for the product user.

The largest practical gap is local intent intake. The current agentic
`pdd change` workflow is centered on a GitHub issue URL, while its manual mode
requires technical prompt/code paths. `pdd story add` accepts local files and
inline text, but it only builds acceptance coverage and still requires the
caller to identify prompt or development-unit targets. It is not a universal
“implement what I just asked for” command.

## Implemented fork workflow: `pdd intent plan` and `pdd intent apply`

The PDD fork now has a beginner-facing local planning and application facade.
Existing commands remain available for backward compatibility and advanced
control.

Current interface:

```bash
pdd intent plan --text \
  "Highlight out-of-limit pressure intervals without changing the uploaded data."
pdd intent plan docs/requests/pressure-trace.md
printf '%s\n' "Add offline PDF export." | pdd intent plan
pdd intent plan --text "Add offline PDF export." --json
pdd intent apply --text "Add offline PDF export." \
  --approve INTENT_ID_FROM_PLAN --json
```

An AI harness could invoke the same functionality through a structured tool
call. The person would normally never type these commands. Planning classifies
and explains without writing. Apply requires the exact reviewed plan ID before
it mutates the selected project or subproject.

It handles four adoption routes without changing the human interaction:

1. existing standalone project without PDD:
   `existing_project_adoption` / `characterize_then_adopt`;
2. completely new standalone project:
   `new_project_design` / `design_greenfield`;
3. existing monorepo subproject without PDD:
   `existing_subproject_adoption` / `characterize_then_adopt`;
4. proposed new monorepo subproject:
   `new_subproject_design` / `design_greenfield`.

For routes 3 and 4, `--project-root` is the subproject directory, not the
monorepo root. A proposed new directory need not exist during planning.

When an independent story is warranted, apply stops with
`awaiting_story_approval`, its path, and its SHA-256. The agent presents the
story in ordinary language. Only after the human approves that exact wording
does the agent rerun apply with `--approve-story <sha256>`; regression
generation and synchronization do not run before that gate.

### `pdd intent` responsibilities

1. **Implemented:** accept ordinary text, a local file, or standard input
   without GitHub.
2. **Implemented:** preserve the original request unchanged for independent
   traceability.
3. **Implemented:** classify greenfield, existing PDD, conventional
   brownfield, repository, and scoped monorepo-subproject cases.
4. **Implemented for existing PDD inventories:** discover candidate logical
   parts conservatively without requiring the human to supply a “dev unit.”
5. **Implemented:** produce the human-facing review card and stable JSON.
6. **Implemented:** record corrections/removals as new immutable events with
   explicit `--supersedes`, without erasing the original request.
7. **Implemented:** maintain Product Intent and per-intent machine status.
8. **Implemented:** update or create architecture and `.prompt` source through
   existing local PDD workflows.
9. **Implemented:** create an independent story selectively and require
   approval of its exact SHA-256.
10. **Implemented:** generate story regression coverage after approval,
    synchronize the scoped project, and request evidence.
11. **Implemented:** report changed prompt/test/code paths without requiring
    the human to manipulate them.
12. **Implemented:** reject mismatched approval IDs, uncharacterized
    brownfield adoption, missing prompt mappings, and failed child workflows.

### A possible durable intent packet

The exact schema needs implementation design, but a local, versionable record
could look like:

```markdown
# Intent: pressure-trace-limits

## Original Request
<!-- immutable after capture -->

## Accepted Interpretation

## Must

## Must Not

## Examples

## Affected Product Areas

## Verification Plan

## Status
```

This is not another form the human must learn. It is the agent's durable record
of the conversation. The human can approve it through the review card.

## What belongs in the PDD fork versus the agent playbook

The split should be:

- **PDD fork:** parsing and persistence of local intent, target discovery,
  deterministic status, orchestration APIs, validation, and evidence.
- **Agent playbook:** when to invoke the workflow, how to speak with the human,
  what requires approval, how to preserve unrelated work, and how to summarize
  results.
- **Project repository:** the actual intent, prompts, stories, tests,
  architecture, and generated source for that product.

Markdown instructions alone can teach an AI agent to hide today's CLI
complexity, and that is the correct immediate compatibility layer. Code changes
are still worthwhile because every harness should not have to independently
reimplement the same routing and bookkeeping.

The official “Architecting with AI” demonstration reinforces this split. It
shows the presenter using Claude Code or Cursor to help write the specification
and to turn `architecture.json` dependencies into synchronization automation.
See
[`PDD_VIDEO_ARCHITECTING_WORKFLOW_NOTES.md`](PDD_VIDEO_ARCHITECTING_WORKFLOW_NOTES.md).
The proposed facade should make that agent orchestration a supported workflow
instead of a workaround each user reconstructs.

## Recommended implementation order

1. **Done in fork commit `fefa9a1fc`:** add a read-only `pdd intent plan` path
   that accepts text/file/stdin and prints the review card plus proposed
   targets without modifying the project.
2. **Done in fork commit `3365d04ac`:** add local `pdd intent apply`, exact
   plan approval, durable intent/correction records, brownfield safety,
   selective story approval, regression generation, scoped sync, and
   `pdd.intent.apply.v1` status.
3. Pilot it on one small Python unit and one coupled C++ header/source unit
   before treating target discovery as reliable.
4. Add a dedicated `pdd intent status` convenience command if operational
   experience shows that reading the apply JSON/status record is insufficient.

The implementation should reuse existing PDD story, prompt, sync, test, and
verification internals. It should not replace them or alter their advanced
command contracts unnecessarily.

## The final beginner rule

The human should be able to say:

> Here is what I want. Tell me what you understood, ask only the decisions that
> matter, handle the PDD files and commands, and show me what proves it worked.

That is sufficient human input for agent-assisted PDD.
