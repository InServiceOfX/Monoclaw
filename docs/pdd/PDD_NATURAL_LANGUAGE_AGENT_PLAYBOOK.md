# PDD Natural-Language Intent Playbook for AI Agents

This is an execution playbook for an AI coding agent. Its purpose is to remove
PDD terminology, command selection, input-format selection, internal target
discovery, filenames, and output interpretation from the human user's mental
workload.

This policy is versioned in Monoclaw and is loaded through the workspace
bootstrap described in
[`PDD_WORKSPACE_BOOTSTRAP.md`](PDD_WORKSPACE_BOOTSTRAP.md). The PDD fork
supplies the executable implementation; it is not the source of these harness
rules.

There is no required trigger phrase. In a repository that is already configured
to use PDD, ordinary product conversation is the input:

> Highlight every out-of-limit interval in the pressure trace.

Later messages are input too:

> Actually, combine intervals separated by less than two seconds.

> We no longer need CSV export.

> Never modify the original samples.

The agent must recognize these as additions, corrections, removals, or
constraints; preserve them durably; and choose the appropriate current PDD
workflow. Do not require the user to know that `pdd story` exists, whether the
input should be a GitHub issue, local Markdown file, or `--text`, what PDD calls
the affected internal target, or where generated files belong.

## What are we trying to do?

The goal is not to teach the user PDD commands. The goal is to maintain a
faithful, versioned chain from what the user means to what the software does:

```text
ordinary user messages
        |
        v
Product Intent and request history
        |
        v
versioned PDD prompts
        |
        v
generated software

human stories + contracts + tests
        |
        +---- independently check prompts and behavior
```

The user's messages are sufficient **intake**. Chat history alone is not a
sufficient durable source of truth. The agent must write accepted intent into
the repository before depending on it for future regeneration. For each
PDD-managed part, the affected `.prompt` file is the operative source for
generation. Product requirements and user stories support that source; they do
not replace it.

The distinction between a conversational request, Product Intent, a PDD prompt,
and a user story is defined in
[`PDD_AFTER_SETUP.md`](PDD_AFTER_SETUP.md). Read it before executing ongoing
PDD work.

## Plain-language terminology

PDD documentation and CLI flags use **dev unit** or `--devunit`. This means one
separately specified part of the product, usually represented by a PDD prompt
and its generated code/tests. Examples are “pressure-trace analyzer,” “CSV
exporter,” or “login screen.”

This is internal routing vocabulary. In conversation with the user, say
“affected part of the product” or name the part directly. Never require the
user to understand or supply a “dev unit.”

A logical product part is not necessarily one physical file. The project's
prompt suite collectively governs the project, and a coherent unit may own
coupled outputs such as a C++ header and implementation. Current PDD may expose
those outputs as several linked prompt entries. In that case, preserve one
canonical shared contract, update all affected prompt projections, and
synchronize/verify the group. Do not expose the mechanical split to the user.
See
[`PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md).

This playbook was checked against PDD `0.0.309` at source commit `17b41a779` on
2026-07-26. The installed CLI is authoritative. Before execution, run:

```bash
pdd --version
pdd story --help
pdd story add --help
pdd test --help
```

## Agent contract

When a user expresses product intent in a PDD-managed repository, the agent
owns these decisions:

1. Determine whether the message adds, corrects, removes, replaces, or clarifies
   accepted intent.
2. Preserve the message and update the current human-readable requirements.
3. Discover the affected product part and its PDD prompt mapping or linked
   prompt group from repository evidence.
4. Propagate accepted behavior into the affected `.prompt` source before
   completing implementation. If no appropriate prompt exists, route through
   the architecture/change workflow rather than pretending a story is enough.
5. Present consequential prompt or prompt-group changes for meaning-level
   human approval. The
   agent may write the file, but must not treat prompt source as an ignorable
   generated artifact.
6. Select the least complicated story source form that remains durable when an
   independent user story is valuable.
7. Preview the operation when useful.
8. Choose the relevant PDD command; do not assume every message means
   `pdd story add`.
9. Find and review every output rather than assuming generation succeeded.
10. Present any human story for approval in plain language.
11. Generate executable regression coverage separately when authorized.
12. Report prompt-source changes, deterministic tests, semantic/LLM checks,
    and unproven claims
    separately.

The agent must not shift these mechanics back to the user merely because the
CLI exposes several options.

## Minimum input from the user

Only one thing is required:

> What should happen, stop happening, or change?

Everything else is optional but useful:

- who experiences the behavior;
- why it matters;
- a normal example;
- a difficult or failure example;
- something that must always happen;
- something that must never happen;
- something that is out of scope.

The agent should extract what is present and ask only for a missing
product/domain decision that materially changes the result.

## Input forms the user may provide

Any of these is sufficient to start:

- a dictated or typed need;
- rough notes;
- an existing PRD or requirements file;
- a GitHub issue URL;
- an existing human story;
- an ordinary feature request without mentioning PDD;
- a request such as “preserve this behavior so regeneration cannot lose it.”

The input does not have to use the
`As a <persona>, I want <capability>, so that <benefit>` format. The agent may
draft that sentence from ordinary domain language.

The agent should ask the user only for a product/domain decision it cannot
infer safely. Do not ask the user:

- which `pdd story` subcommand to use;
- whether the CLI needs `--text` or a file;
- the prompt path when repository inspection can find it;
- PDD's internal name for the affected product part;
- a slug, story directory, contract directory, or test filename.

## Treat later messages as changes to intent

Each new user message is an intent event. Classify it by meaning:

- **Add:** introduces compatible new behavior.
- **Clarify:** explains existing behavior without changing it.
- **Correct/replace:** changes previously accepted behavior.
- **Remove:** explicitly says behavior is no longer wanted.
- **Example:** supplies evidence that sharpens acceptance criteria.
- **Constraint:** adds a must/must-not boundary.
- **Contradiction/unclear:** conflicts with current intent and requires one
  product-level question.

Do not treat omission as removal. Do not silently delete a prior story because
a newer prompt sounds different. For a correction or removal:

1. identify the exact current requirement/story affected;
2. show the meaning-level change when it is consequential;
3. preserve history by recording that the earlier intent was superseded or
   retired;
4. update the current Product Intent/requirements and any affected human
   stories;
5. propagate the accepted change to the affected PDD prompts and tests;
6. regenerate/synchronize only after the source artifacts agree.

Never reverse the direction by treating generated code as the explanation of
what the user must have meant.

## Persist conversational intent

Prefer the repository's established product-requirements structure. If none
exists, use a simple versioned fallback:

```text
docs/
├── PRODUCT_INTENT.md
└── requirements/
    └── requests/
        └── YYYY-MM-DD-<descriptive-slug>.md
```

The request file should preserve the user's meaning faithfully and record:

- received date;
- inferred action: add, clarify, correct, remove, example, or constraint;
- affected current requirement/story when known;
- status: proposed, accepted, superseded, retired, or rejected;
- the original intent text, excluding secrets/private data that policy forbids
  committing;
- the resulting requirement/story links.

`PRODUCT_INTENT.md` is the current consolidated truth; request records preserve
how it changed. A repository may use different names. Follow its established
layout rather than creating a second requirements system.

## First routing decision: does an affected PDD-managed part exist?

`pdd story add` creates acceptance coverage for prompts that already exist. It
does not create a greenfield architecture.

Inspect, from the target project root:

```bash
git status --short --branch
rg --files --hidden \
  -g 'AGENTS.md' \
  -g '.pddrc' \
  -g 'architecture.json' \
  -g '*.prompt' \
  -g 'story__*.md'
```

Also read applicable instruction files in ancestor directories. If `rg` is not
available, use the repository's next-best file search. Respect the nearest
`AGENTS.md`, branch policy, privacy rules, and unrelated working-tree changes.

Classify the project:

### Existing PDD-managed product part

At least one relevant `.prompt` file or `architecture.json` module mapping
exists. Continue to the story-source and target-discovery steps.

### PDD project, but no matching product part

The intent may be a new feature rather than acceptance coverage for an existing
part. Do not invent a prompt association merely to make `pdd story add` run.
Draft/refine the requirement and route through the project's PDD change or
architecture workflow first. Add story coverage after prompts exist.

### Greenfield project

No PDD configuration, architecture, or prompts exist. Do not ask the user to
choose “greenfield” as a CLI concept. Explain simply:

> This project does not yet have a PDD specification for the story to validate.
> I will first preserve your idea as a draft PRD/story and prepare the initial
> architecture workflow.

The current supported automatic greenfield PRD-to-architecture workflow uses a
GitHub issue URL. Creating or posting that issue is an external action and
requires user approval. This GitHub requirement is separate from ordinary
story/contract generation.

## Choose the story source automatically

PDD calls the independent behavioral input an “issue source,” but it does not
have to be a GitHub issue.

Choose in this order:

### 1. User supplied an existing source

- GitHub issue URL or number: use it only if the user supplied/approved it.
- Existing local requirements/PRD/issue Markdown: use that file.
- Existing human `story__*.md`: do not create a duplicate. Inspect its prompt
  links and use `pdd story link` if links are missing or stale.

### 2. User supplied chat or dictated intent

By default, preserve the accepted message in the repository's versioned
requirements/request structure and pass that local Markdown file to PDD. This
keeps the original intent reviewable even when `.pdd/` runtime state is ignored
by Git.

Internal command shape:

```bash
pdd story add docs/requirements/requests/<request>.md \
  --title "<short human title>" \
  --devunit <internally-discovered-name>
```

Do not make the user type this command.

The `--text` form is also supported. Use it when the repository intentionally
tracks or otherwise preserves `.pdd/story_sources/`, or when the user explicitly
wants a lightweight local run:

```bash
pdd story add \
  --text "<the user's intent, faithfully preserved>" \
  --title "<short human title>" \
  --devunit <internally-discovered-name>
```

### 3. User supplied multi-story intent

Draft a local Markdown requirements source under the repository's established
requirements location. If none exists, use a clear path such as:

```text
docs/requirements/<descriptive-slug>.md
```

Keep the source independent of the current prompt/code implementation. Then use
that file with `pdd story add`.

Internal command shape:

```bash
pdd story add docs/requirements/<descriptive-slug>.md \
  --title "<short human title>" \
  --devunit <internally-discovered-name>
```

If the input contains several independent user outcomes, propose separate
stories. Do not compress unrelated capabilities into one story merely to make
one command.

## Discover the affected product part automatically

`pdd story add` requires at least one `--devunit`, `--prompt`, or
`--from-changed-files`. Determine the target from evidence:

1. If the user names a feature/module, inspect `architecture.json` entries whose
   `filename`, `filepath`, `description`, or tags match that intent.
2. Resolve the corresponding `.prompt` file and generated-code mapping.
3. If the current task changed exactly one relevant prompt, that prompt is a
   strong target.
4. Inspect prompt interfaces and requirements; do not choose from filename
   similarity alone when multiple candidates exist.
5. Internally prefer `--devunit` when PDD resolves the basename unambiguously.
6. Use explicit `--prompt <path>` when nested configurations or duplicate
   basenames make the path clearer.
7. Use `--from-changed-files` only when every changed prompt belongs to this
   story. Never sweep unrelated user changes into the mapping.

For a story that genuinely spans multiple existing units, pass multiple
`--devunit`/`--prompt` options and `--cross-devunit`. Do not mark a story
cross-unit simply because target discovery is uncertain.

If two plausible targets remain after inspection, ask one product-level
question explaining the responsibilities of the candidates. Do not ask the
user to interpret filenames without that explanation.

## Preflight

Before an LLM-backed write:

1. Run `pdd story list --with-regression-status`.
2. Check for a duplicate or semantically equivalent story.
3. Choose a stable title/slug.
4. Run `pdd story add ... --dry-run` when its output will clarify the proposed
   story path and links.
5. Review `git status` again.
6. Confirm the task authorizes the required model call. A local source avoids a
   GitHub fetch, but story and contract authoring still use an LLM.

Always give a source-file invocation an explicit `--title` during dry-run.
Without it, the dry-run may only be able to display the generic proposed name
`story__new_story.md`.

## Execute and discover outputs

Run the selected command from the target project root. Do not parse success
from exit code alone. Inspect the command message and working-tree diff.

Expected artifacts:

| Artifact | Expected behavior |
|---|---|
| `.pdd/story_sources/<slug>.md` | Created only for `--text`; durable copy of inline input |
| `user_stories/story__<slug>.md` | Human-facing story plus `pdd-story-prompts` metadata |
| `user_stories/contracts/<slug>.contract.md` | Best-effort generated machine-oriented contract |
| linked `.prompt` files | Normally read/linked, not rewritten by `story add` |
| regression test | Not created by `story add`; separate `pdd test --from-story` step |

Repository configuration may override conventional directories. Use the paths
reported by PDD and the project configuration rather than assuming this exact
layout.

Important current behavior:

- Story generation uses the independent source text, not the target prompt
  content, to author the human story.
- The story receives metadata linking it to the prompts it validates.
- Contract generation is best-effort. PDD can successfully write the story
  while reporting that contract generation was skipped or failed.
- `pdd story add --generate-regression` only prints a handoff command. It does
  not generate or run a regression test.
- `pdd story add --update` currently refreshes links on an existing story; it is
  not a general “rewrite story and regenerate contract” command.

## Human approval gate

Prompt approval and story approval are related but different.

Before regenerating from a consequential prompt change, show the product/domain
human a plain-language prompt review card:

1. the affected part and its purpose;
2. inputs and outputs;
3. behavior added, changed, or removed;
4. `MUST` and `MUST NOT` rules;
5. important examples and edge cases;
6. dependencies, architecture effects, and unresolved assumptions;
7. tests intended to prove the behavior.

The human need not write prompt syntax, but must be able to correct its meaning.
A technical owner must inspect consequential `.prompt` diffs, interfaces,
dependencies, and critical tests. Apply stricter direct review for safety,
security, privacy, financial, performance-sensitive, or otherwise high-risk
behavior.

After story generation, show the user:

1. the one-sentence human story;
2. the source it was derived from;
3. the affected product part(s), explained by responsibility rather than
   internal name or filename;
4. a short summary of the generated contract;
5. any assumptions, over-broad criteria, or missing negative cases.

Ask the user to approve or correct the **meaning**, not the PDD syntax.

The human story is editable. The generated contract is derived output and must
not be hand-edited. If the story meaning is wrong, correct the story/source and
regenerate/re-align the contract through supported tooling.

Approval of the one-sentence story does not implicitly approve the full prompt.
The story checks one acceptance outcome; the prompt is the fuller source that
governs regeneration.

The current PDD library contains `sync_user_story_contract()`, but version
`0.0.309` does not expose a dedicated public CLI command for it. Do not pretend
that `--update` performs this synchronization. If re-alignment is required and
the installed CLI still lacks a command, report that tooling gap rather than
silently editing the contract.

## Generate executable regression coverage

After the story/contract is approved and the model call is authorized, inspect
`pdd test --help` and run:

```bash
pdd test \
  --from-story user_stories/story__<slug>.md \
  --output tests/story_regression/test_story_<slug>.py
```

Then inspect the generated test:

- Prefer a behavioral test with a real entry point and observable assertions.
- A text-pin/staleness test is weaker evidence; label it honestly.
- Check that important `MUST NOT` behavior has a negative assertion.

Run:

```bash
pytest -m story
```

Also run the focused repository tests for the affected product part.

## Validate story-to-prompt alignment

When authorized to use the required model:

```bash
pdd detect --stories
```

This is semantic/LLM validation of stories and generated contracts against
linked prompts. It is not the same as executing the product behavior.

Keep the evidence categories separate:

- human approval: the story says what the user means;
- generated contract review: the detailed oracle is faithful;
- `pdd detect --stories`: semantic alignment with prompts;
- `pytest -m story`: executable story regression;
- repository tests: implementation behavior;
- inspection only: an inference, not proof.

## Existing-story commands

Use these without burdening the user with command selection:

```bash
# Inventory and coverage status
pdd story list --with-regression-status

# Add or refresh a prompt mapping on an existing human story
pdd story link user_stories/story__<slug>.md \
  --prompt prompts/<module>_<language>.prompt
```

`pdd story link` changes metadata; it does not generate a new story or contract.

## Failure routing

| Situation | Agent response |
|---|---|
| No PDD prompts exist | Preserve intent, then route to greenfield architecture |
| PDD exists but no matching part | Route through PDD change/architecture first |
| Target is ambiguous | Inspect deeper, then ask one product-level choice |
| Equivalent story exists | Reuse/link it; do not create a duplicate |
| Story slug exists | Inspect it; do not overwrite automatically |
| Contract generation fails | Preserve/report the story; do not claim contract success |
| User corrects the story | Re-align through supported tooling; never hand-edit contract |
| Only a text-pin test is generated | Report weaker evidence explicitly |
| Unrelated prompts are dirty | Do not use `--from-changed-files` broadly |
| GitHub source is private/unavailable | Use an approved local source when possible |
| No model provider is authorized | Preserve the source and report the exact blocked step |

## Completion report

Report in plain language:

- what human intent was preserved;
- which part(s) of the product it covers and why;
- every created/changed path;
- whether the contract was actually generated;
- whether the story was human-approved;
- whether semantic validation ran and passed;
- whether a behavioral or text-pin regression was generated;
- exact test results;
- remaining uncertainty or tooling gaps;
- cost/model information when PDD reports it.

Do not make the final report a list of commands the user must memorize. The
agent owns the procedure; the user owns the intent and approval.

## Minimal trigger for repository instruction files

An `AGENTS.md`, `CLAUDE.md`, or equivalent harness instruction can point here
with:

```text
In a PDD-managed repository, treat ordinary product requests, corrections,
removals, examples, and constraints as natural-language intent input. Read
docs/pdd/PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md. Preserve accepted intent
durably, update current requirements, discover the affected product part,
choose the supported PDD workflow, present meaning-level changes for approval
when needed, and report contract/test evidence. Do not require a PDD trigger
phrase or make the user learn PDD terms, commands, flags, or filenames.
```
