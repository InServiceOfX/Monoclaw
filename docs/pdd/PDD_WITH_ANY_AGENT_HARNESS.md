# Prompt-Driven Development with Any AI Agent Harness

This is a standalone operating guide for an AI coding agent using the `pdd`
command-line interface. It is not specific to Claude Code, Codex, Gemini,
OpenCode, OpenClaw, Cursor, or any repository.

For the workspace-to-Monoclaw instruction-loading architecture, read
[`PDD_WORKSPACE_BOOTSTRAP.md`](PDD_WORKSPACE_BOOTSTRAP.md).

If you are a product owner, domain expert, mechanical engineer, or anyone who
wants to begin with an ordinary-language description rather than PDD commands,
start with [`PDD_START_HERE.md`](PDD_START_HERE.md).

For automatic `pdd story` input selection, dev-unit discovery, output
interpretation, human approval, and regression routing, follow
[`PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md`](PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md).

For the conceptual model, the Agile/Extreme Programming origin of user stories,
PDD's adaptation of the Three C's, and a source-level walkthrough of the current
implementation, read
[`PDD_CONCEPTS_AND_USER_STORIES.md`](PDD_CONCEPTS_AND_USER_STORIES.md).

For the recurring workflow after a project is configured, including the
distinction between conversational intent, Product Intent, component prompts,
and user stories, read [`PDD_AFTER_SETUP.md`](PDD_AFTER_SETUP.md).

For project-wide prompt suites, C++ header/source pairs, and the distinction
between logical regeneration units and physical files, read
[`PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md).

Assume one of these is true:

- `pdd` is installed and available on `PATH`; or
- a project-provided wrapper runs `pdd` inside a Docker container.

In either case, commands in this guide use `pdd ...`. If a wrapper is required,
substitute the wrapper while preserving the arguments.

The installed CLI is authoritative. Before relying on an option copied into an
instruction file, run:

```bash
pdd --version
pdd --help
pdd <command> --help
```

PDD changes quickly. Prefer command help over remembered flags.

---

## 1. The operating model

PDD treats human-authored intent as source and conventional code as generated
output:

```text
prompt + contracts + stories + tests + context
                         |
                         v
                 generation / sync
                         |
                         v
              code + examples + evidence
```

The durable assets are:

- `.prompt` files: intent, interfaces, requirements, and durable rules
- tests: executable behavioral constraints that accumulate over time
- user stories: independent acceptance-level oracles
- generated story contracts: machine-checkable expansions of human stories
- context and examples: project conventions and dependency interfaces
- `architecture.json`: the dev-unit graph, when the project uses it

Code is generated output only when the repository explicitly manages that code
through PDD. Do not assume every `src/` directory or every source file is
generated. Confirm that a matching prompt or architecture entry exists.

### The minimum safe mold

Regeneration is safe only when the dev unit has:

1. A declared or frozen public interface.
2. Behavioral tests for its important requirements.
3. A negative test for every important `MUST NOT` rule.

Without these walls, regeneration is a gamble. Characterize current behavior
before regenerating an established or brownfield module.

### Ownership

- The agent explores, diagnoses, and drafts intent.
- The prompt owns intended behavior.
- Tests own enforced behavior.
- User stories own independent acceptance intent.
- PDD owns compilation, synchronization, and evidence.
- Generated code remains reviewable, but it is not automatically the source of
  truth.

When a chat or manual code edit discovers new intended behavior, promote that
behavior into a prompt, story, or test. Do not leave the decision only in chat
history.

---

## 2. First determine whether PDD applies

Use PDD when at least one of these is true:

- the target has a matching `.prompt` file;
- the target appears in `architecture.json`;
- repository instructions identify it as a PDD-managed dev unit;
- the task explicitly asks to adopt, generate, synchronize, or repair PDD
  artifacts.

Do not force PDD onto:

- a tiny conventional file with no prompt or test mold;
- a performance micro-optimization whose correctness depends on implementation
  detail;
- novel algorithm research without a stable interface;
- safety-critical behavior without strong independent tests;
- legacy code with hidden coupling that has not yet been characterized.

For brownfield adoption, follow Section 8 instead of immediately regenerating.

### Repository inspection

Before choosing a command:

1. Read the repository and nearest-directory agent instructions.
2. Inspect `git status` and preserve unrelated changes.
3. Look for `.pddrc`, `architecture.json`, `prompts/`, `user_stories/`,
   `context/`, and matching tests.
4. Identify the exact dev unit and output path.
5. Run the relevant baseline tests.
6. Inspect `pdd <command> --help`.

If this is a read-only review, explanation, or diagnosis request, do not run a
mutating PDD workflow merely because the project uses PDD. Inspect and report
unless implementation was requested.

---

## 3. Command router: when to invoke PDD

This table is the primary routing policy.

| Situation | Route |
|---|---|
| Ordinary-language product request, correction, removal, or PDD-adoption request in any standalone/monorepo new/existing layout | Run `pdd intent plan --text "<exact request>" --project-root "<exact project/subproject scope>" --json`; it is read-only intake, so continue with the applicable implementation route after review |
| Current runtime symptom: crash, stack trace, failing command, regression, wrong CLI/API/UI output, or incorrect generated behavior | `pdd bug <issue-url>` then `pdd fix <issue-url>` |
| Explicit product, specification, or source-truth change with no current runtime failure to reproduce | `pdd change <issue-url>` then synchronize the affected dev units |
| PRD or requirements issue must become architecture and prompts | `pdd generate <issue-url>` |
| Existing PDD dev unit needs the complete generate/verify/test/fix/update loop | Run baseline tests, then `pdd --force sync <dev-unit>` |
| Whole PDD project needs dependency-ordered synchronization | Run only when explicitly in scope: `pdd --force sync` |
| Need to preview synchronization | Use the sync command's current dry-run option shown by `pdd sync --help` |
| Oversized dev unit needs diagnosis and decomposition | `pdd split <target-file>` |
| Need implementation or PR health review | `pdd checkup ...`; inspect `pdd checkup --help` for issue, PR, or report-only modes |
| Issue or interview must become an independent user story | `pdd story add ...` |
| Stories must be checked against linked prompts | `pdd detect --stories` |
| Approved story must become an executable regression | `pdd test --from-story <story-file>` |
| Prompt must become code | `pdd generate <prompt-file>` |
| Prompt and code need a runnable example | `pdd example <prompt-file> <code-file>` |
| Existing prompt/code need generated or enhanced tests | `pdd test --manual <prompt-file> <code-file>` |
| Failing tests need repair | `pdd fix`; choose issue, story, or manual mode from command help |
| Runtime example crashes | `pdd crash`; inspect command help for required files |
| Program output must be judged against intent | `pdd verify`; inspect command help for required files |
| Code changed first and durable behavior must be back-propagated | `pdd update` |
| Prompt dependencies need discovery | `pdd auto-deps <prompt-file>` |
| Prompt includes/directives need local expansion or snapshotting | `pdd preprocess <prompt-file>` |
| Expanded prompt context may exceed the model window | `pdd context <prompt-file>` |
| Two prompts may conflict | `pdd conflicts ...` |
| Prompt contract structure needs deterministic linting | `pdd contracts check <prompt-or-directory>` |
| Contract rules need story/test coverage analysis | `pdd checkup coverage <prompt-or-directory>` |

### The most important routing distinction

Use `bug -> fix` for a current observable failure, even when an issue claims the
prompt or specification should change. Reproduce the symptom as a failing test
before repairing it.

Use `change -> sync` for new or changed intent when there is no current failure
to reproduce.

This distinction prevents a flawed specification from generating a test that
forces correct code to become incorrect.

### Read-only versus mutating commands

Do not infer authorization for writes, remote comments, pushes, pull requests,
or broad regeneration from a request to inspect or explain.

Before running an agentic issue workflow, determine from command help and
repository instructions whether it may:

- modify prompts, code, tests, or metadata;
- create branches or worktrees;
- commit or push;
- read or comment on GitHub issues and pull requests;
- invoke a paid or remote model;
- overwrite generated files.

`--force` suppresses interactive safety prompts and may allow overwrites. Use it
only when the requested scope is clear, unrelated work is protected, and
baseline tests exist.

---

## 4. Standard workflows

### A. Runtime bug from an issue

```bash
# Confirm clean scope, branch policy, credentials, and command behavior first.
pdd bug https://github.com/OWNER/REPO/issues/123

# Review the generated failing test. It must fail for the reported symptom.
pdd fix https://github.com/OWNER/REPO/issues/123

# Run the repository's full relevant test suite.
```

Do not let the fixer weaken, delete, or rewrite a correct reproduction test.
Use the current protect-tests option when available and appropriate.

The durable outcome is not merely repaired code. It is repaired intent plus a
regression wall that fails on the pre-fix behavior and passes on the fix.

### B. Product or specification change

```bash
pdd change https://github.com/OWNER/REPO/issues/456

# Review the source-truth changes, then synchronize the affected dev units.
pdd --force sync <dev-unit>
```

Use an issue-URL form of sync only when current command help and project
instructions call for it. Do not blindly synchronize the whole project.

### C. One established dev unit

```bash
# 1. Establish the safety baseline with the repository's own test command.
pytest path/to/relevant/tests

# 2. Preview if the installed sync command supports a dry-run.
pdd sync --help

# 3. Synchronize only the intended dev unit.
pdd --force sync <dev-unit>

# 4. Run the relevant and then broader test suites.
pytest path/to/relevant/tests
pytest

# 5. Review prompt, test, generated-code, and evidence diffs.
git diff
```

A large source-code diff is not automatically a failure. Behavioral differences
are failures when they violate tests, contracts, stories, or declared
interfaces.

### D. PRD or requirements to a new PDD project

```bash
pdd generate https://github.com/OWNER/REPO/issues/789
```

Review the generated:

- `architecture.json`
- `.pddrc`
- prompt files
- architecture visualization, if produced
- output path and language mapping

Then synchronize incrementally. Do not accept generated architecture as
authoritative without checking it against the repository's real interfaces and
dependency directions.

### E. Manual prompt workflow

```bash
pdd generate prompts/<module>_<language>.prompt
pdd example prompts/<module>_<language>.prompt <generated-code-file>
pdd test --manual prompts/<module>_<language>.prompt <generated-code-file>
```

Use `--merge` or the installed equivalent when enhancing an existing test
suite. Existing behavioral tests accumulate; they are not disposable
generation output.

### F. Story workflow

Canonical PDD stories are independent oracles. Author them from the issue,
interview, or explicitly supplied source intent—not from the implementation or
the prompt they will later grade.

```bash
pdd story add <issue-url-or-local-issue-file> --devunit <dev-unit>

# Human gate: read and approve the plain-language Story.
pdd detect --stories

pdd test --from-story user_stories/story__<slug>.md \
  --output tests/story_regression/test_story_<slug>.py

pytest -m story
```

The usual two-file model is:

```text
user_stories/story__<slug>.md
user_stories/contracts/<slug>.contract.md
```

- The human Story is the source of truth and should remain short.
- The contract is generated and should not be hand-edited.
- After changing the Story, use the repository's documented contract
  re-alignment mechanism.

An agent may separately read code to produce an implementation-status report
with `Implemented / Partial / Not built` findings. That is useful product
analysis, but it is not the independent canonical Story. Keep status evidence
separate so current implementation does not redefine desired behavior.

---

## 5. Prompt and contract rules

Start with the smallest prompt that fully states observable intent:

```xml
% You are an expert <language/framework> engineer. Implement <module>.

<include>context/project_preamble.prompt</include>

<pdd-interface>
{"type":"module","module":{"functions":[
  {"name":"<function>","signature":"(<args>) -> <ReturnType>","returns":"<ReturnType>"}
]}}
</pdd-interface>

% Requirements
1. <Primary behavior>
2. <Input and validation contract>
3. <Output and error contract>
4. <Important invariant>

<contract_rules>
R1 (MUST): <observable required behavior>.
R2 (MUST NOT): <observable forbidden behavior>.
</contract_rules>

<dependencies>
<include mode="interface">path/to/dependency</include>
</dependencies>
```

### Prompt-writing rules

- State each fact once.
- Specify outcomes and interfaces, not private implementation steps.
- Put project-wide style in a shared preamble.
- Put edge cases in accumulated tests unless they express a general durable
  rule.
- Define ambiguous domain terms in a vocabulary section.
- Give every durable contract rule a stable ID.
- Never renumber stable rule IDs; deprecate or leave gaps.
- Every rule must be observable and testable.
- Every important `MUST NOT` needs a negative test.
- Back-propagate behavior, not private helper names, exact internal API calls,
  or non-observable internal ordering.

Use the test:

> Could a different, equally correct implementation satisfy this sentence?

If not, the prompt probably transcribes the current implementation rather than
specifying durable intent.

### Preprocessing and context

`pdd preprocess` is a local preprocessing operation. It expands or transforms
prompt directives and can write replayable snapshots; it does not itself
perform model generation.

Dynamic inputs such as shell output, web content, or semantic query includes
can vary across machines and time. Snapshot contract-critical context rather
than relying on live expansion.

`pdd context` accepts one prompt path in current versions. Use it once per
important prompt and use the threshold option shown by current command help.
For example, a current installation may support:

```bash
pdd context prompts/example_python.prompt --threshold 80
```

Do not assume a directory or multi-file glob is accepted without checking help.

---

## 6. Tests are permanent mold walls

When generating or editing tests:

- preserve every valid existing behavioral case;
- add a test before fixing a reproduced bug;
- assert public behavior, state transitions, emitted events, or external calls;
- avoid assertions about private helper names or incidental implementation;
- use negative tests for forbidden side effects, writes, calls, and leaks;
- hold back independent tests for high-risk behavior when overfitting is a
  concern;
- run the repository's real tests after PDD's own verification.

For each contract rule, track its evidence level:

1. Prompt-only: documented but unenforced.
2. Story-backed: independently described.
3. Test-backed: executable failure proves violation.
4. Policy-backed: automatically gated in CI.

High-risk `MUST` and `MUST NOT` rules should reach level 3 or higher, or carry
an explicit, expiring waiver.

### Drift check

Periodically regenerate an unchanged prompt and run the full test suite.

Report:

- whether all tests pass;
- which observable behaviors changed;
- which differences are not constrained by a test or contract;
- which missing wall should be added.

An unconstrained behavioral difference is a hole in the mold.

---

## 7. CI gates

Use deterministic and inexpensive checks before LLM-backed checks.

Example building blocks—adapt paths and commands to the installed version:

```bash
# Repository behavior
pytest
pytest -m story

# Deterministic prompt structure; TARGET is required.
pdd contracts check prompts/ --stories user_stories/

# Context budget; invoke once per prompt.
pdd context prompts/example_python.prompt --threshold 80

# LLM-backed story validation.
pdd detect --stories \
  --stories-dir user_stories \
  --prompts-dir prompts \
  --no-fail-fast \
  --json

# Rule-to-story/test coverage.
pdd checkup coverage prompts/
```

Useful project-specific structural gates include:

- generated output changed without a corresponding prompt change;
- an existing test file lost cases;
- a stable contract rule ID was renumbered;
- a generated story contract was hand-edited;
- a dynamic dependency was used without a reproducible snapshot;
- generated output or evidence contains credentials or private data.

Do not put networked, credentialed, or paid checks into forked-PR CI without an
explicit secret and trust policy.

---

## 8. Brownfield adoption

Do not convert an existing codebase all at once.

1. Pick one high-churn, strong-fit module with a stable public interface.
2. Write characterization tests against the untouched implementation.
3. Include negative assertions for forbidden side effects.
4. Reverse-derive a prompt at the behavior and interface level.
5. Regenerate and run the characterization suite.
6. Refine the mold until repeated regeneration is behaviorally stable.
7. Promote the prompt to source of truth for that dev unit.
8. Add CI gates, then choose the next module.

Be faithful to current intended behavior during conversion. Make improvements
only after the baseline mold is stable, one verified behavioral change at a
time.

Strong first candidates include:

- validation and business rules;
- adapters and API wrappers;
- data transformations;
- CRUD and persistence boundaries;
- internal tools;
- policy enforcement;
- deterministic scripts.

---

## 9. Credentials, models, and execution environment

Run `pdd setup` for the installed version. Authentication differs by execution
mode and command:

- PDD Cloud may use its own authenticated cloud path.
- Local model-backed commands may need provider credentials or an authenticated
  local/device-flow provider.
- Agentic issue workflows may call an installed coding-agent CLI and use that
  CLI's subscription, OAuth, keyring, or provider configuration.
- Some deterministic commands, including local preprocessing and structural
  checks, do not require model credentials.

Do not assume every prompt command requires an API key, and do not assume an
agentic CLI login covers every model-backed operation. Let `pdd setup`, command
help, project configuration, and a non-destructive smoke check determine the
actual requirements.

Never print, commit, or include provider secrets in prompts, snapshots, logs,
evidence, issues, or pull requests.

### Docker/container execution

If PDD runs in a container, the wrapper must provide:

- the repository mounted at a stable working path;
- the correct working directory;
- write access only where the requested workflow needs it;
- `.git` access for workflows that inspect history or manage branches;
- required GitHub and model credentials, preferably mounted read-only or
  injected through a secret mechanism;
- network access only when the chosen command requires it;
- any agentic backend CLI used by issue workflows;
- host UID/GID mapping or equivalent, so generated files are not root-owned.

Before a mutating run, verify inside the container:

```bash
pwd
git status --short --branch
pdd --version
pdd <command> --help
```

Do not bake long-lived secrets into the image or command line. Do not mount an
entire home directory when a narrower credential mount is sufficient.

---

## 10. Harness behavior

The surrounding AI harness may explore and edit, but it should delegate the
repeatable compile-and-verify loop to PDD when the router in Section 3 applies.

Add this compact block to the harness's project instructions when appropriate:

```markdown
## Prompt-Driven Development

- Use PDD only for explicitly PDD-managed dev units or when adoption is requested.
- Current runtime symptom -> `pdd bug <issue-url>` then `pdd fix <issue-url>`.
- New product/spec intent with no current symptom -> `pdd change <issue-url>`,
  then synchronize only the affected dev units.
- Before regenerating established code, run its baseline tests.
- Prompts, human stories, context, and accumulated tests are source.
- Generated code is output only where a matching prompt/architecture entry says so.
- Never delete or replace valid existing tests.
- Every important `MUST NOT` rule requires a negative test.
- Do not run mutating, remote, paid, `--force`, whole-project, commit, or push
  actions unless the request and repository policy authorize them.
- Read `pdd <command> --help` before execution; installed help is authoritative.
```

Harness-specific configuration filenames are discovery mechanisms, not durable
PDD artifacts. The PDD prompt suite and tests should remain useful when the
harness or model changes.

---

## 11. Common failure modes

| Failure | Correction |
|---|---|
| Agent patches generated code and stops | Promote intended behavior into the prompt or test, then synchronize |
| Agent assumes all source files are generated | Confirm matching prompt or architecture ownership first |
| Agent rewrites the test suite | Preserve valid tests and append/merge new cases |
| Story is reverse-engineered from code | Author the canonical Story from source intent; keep code-status analysis separate |
| Prompt names private helpers and exact steps | Back-propagate observable behavior instead |
| Prompt grows toward code size | Move project style to context and edge cases to tests |
| `MUST NOT` exists without a negative test | Add an executable forbidden-outcome test |
| Whole-project sync runs for a one-module task | Scope synchronization to the exact dev unit |
| `--force` is used reflexively | Establish tests, scope, and authorization first |
| Copied CLI flags have drifted | Re-read installed command help |
| Container creates root-owned output | Map host UID/GID or repair the wrapper |
| Credentials appear in evidence or logs | Redact, rotate if exposed, and narrow secret mounts |
| Model output changes despite an unchanged prompt | Run the drift check and strengthen missing mold walls |

---

## 12. One-page checklist

```text
DISCOVER
  Read repository instructions and git status.
  Confirm the target is PDD-managed.
  Resolve the exact dev unit, prompt, output, tests, and side effects.
  Read installed command help.

ROUTE
  Runtime symptom -> bug -> failing test -> fix.
  New intent without a symptom -> change -> scoped sync.
  Existing prompt dev unit -> baseline tests -> scoped sync.
  Brownfield conventional code -> characterize first; do not regenerate yet.

AUTHOR
  Prompts state intent, interfaces, and stable contract rules.
  Stories come from source intent, independent of code and prompts.
  Tests accumulate and enforce behavior.
  Every important MUST NOT gets a negative test.

EXECUTE
  Protect unrelated changes.
  Avoid broad, remote, paid, or forceful actions outside authorization.
  In Docker, verify mounts, working directory, credentials, git, and file ownership.

VERIFY
  Run relevant tests, then broader tests.
  Validate stories and contract coverage where applicable.
  Review prompts, tests, generated output, evidence, and git diff.
  Treat every unconstrained behavioral difference as a missing mold wall.

PRESERVE
  Back-propagate behavior, not implementation.
  Never renumber stable rule IDs.
  Never hand-edit generated story contracts.
  Keep secrets and private data out of durable artifacts.
```

Prompts encode intent. Tests preserve behavior. Regeneration sustains integrity.
