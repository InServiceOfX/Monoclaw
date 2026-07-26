# PDD Concepts, User Stories, and What the Code Actually Does

For a beginner workflow that starts with an ordinary-language idea or dictated
user need, read [`PDD_START_HERE.md`](PDD_START_HERE.md) first.

This is the conceptual companion to
[`PDD_WITH_ANY_AGENT_HARNESS.md`](PDD_WITH_ANY_AGENT_HARNESS.md). Read that
guide for the operational command router and safety rules. Read this document
for the mental model: what Prompt-Driven Development is, where user stories
come from, how PDD adapts them, and how the current PDD implementation realizes
the workflow.

The implementation inspected for this note is the local PDD checkout at:

`repos/PromptDrivenDevelopment/promptdriven/pdd`

Inspection baseline: PDD `0.0.309`, repository commit `17b41a779`, on
2026-07-25. PDD changes quickly; installed command help and current source take
precedence over examples in this document.

## Short answer

Prompt-Driven Development treats durable, reviewable intent as source:

```text
issue / product intent
        |
        v
human user story -----> generated story contract
        |                         |
        +----------+--------------+
                   v
prompt + interface + context + accumulated tests
                   |
                   v
          PDD generation / sync
                   |
                   v
       code + examples + evidence
                   |
                   v
       tests, verification, and review
```

A `.prompt` file is not merely a chat message. For a PDD-managed development
unit, it is a versioned source artifact that declares observable behavior,
interfaces, dependencies, and durable constraints. PDD compiles and
synchronizes that source into conventional code, examples, and tests, then
uses multiple checks to keep them aligned.

Code is generated output only when the repository explicitly says it is. A
matching prompt, `.pddrc` mapping, or `architecture.json` entry must establish
ownership. PDD is not permission to regenerate every source file in a
repository.

## Greg's point about user stories

Greg is directionally right: user stories are widely used in product and
project-management work, especially in Agile teams. The more precise history is:

- User stories originated in **Extreme Programming (XP)**, not in the Agile
  Manifesto and not as a mandatory Scrum artifact.
- Product owners, customers, users, analysts, developers, and testers refine
  them together. They are a bridge between product intent and implementation,
  not merely a ticket written by a project manager and handed over.
- Scrum defines generic **Product Backlog items**. The Scrum Guide does not
  require those items to use the user-story format.

The [Agile Alliance user-story reference](https://agilealliance.org/glossary/user-stories/)
traces user stories to XP and describes them as small functional increments
that contribute product value. The
[2020 Scrum Guide](https://scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-US.pdf)
defines the Product Backlog as an ordered list of what is needed to improve the
product, while leaving the form of its items open. Scrum.org likewise describes
the [user-story format as a complementary, non-mandatory
practice](https://www.scrum.org/resources/blog/user-story-format).

That distinction matters. A user story is not:

- a complete requirements document;
- a technical implementation task;
- a mandatory Scrum ceremony or artifact;
- a substitute for conversation; or
- proof that the behavior works.

### The traditional Three C's

Ron Jeffries' Three C's are
[Card, Conversation, Confirmation](https://agilealliance.org/glossary/three-cs/):

1. **Card** — a short, durable reminder of the desired value.
2. **Conversation** — the collaboration that develops shared understanding.
3. **Confirmation** — evidence that the intended outcome was achieved.

The familiar template is a useful card:

```text
As a <persona>,
I want <capability>,
so that <benefit>.
```

It is not the whole story. The
[Agile Alliance template reference](https://agilealliance.org/glossary/user-story-template/)
calls the format a reminder to preserve who, what, and why, not a reason to
force every requirement into one sentence. This fits the Agile principles of
customer collaboration, changing requirements, frequent working software, and
daily cooperation between business and development
([Agile Manifesto principles](https://agilemanifesto.org/principles)).

## How PDD adapts the Three C's

PDD makes the Three C's durable and machine-actionable:

| Traditional concept | PDD artifact or activity |
| --- | --- |
| Card | `user_stories/story__<slug>.md` |
| Conversation | issue/interview/source intent plus human review and refinement |
| Confirmation | generated contract, story-to-prompt validation, executable regression, and product acceptance |

This is an adaptation, not a literal copy of XP. Classical user stories resist
becoming exhaustive contracts because their main purpose is to provoke
conversation. PDD deliberately adds formal machinery around the small human
story so an AI generator cannot silently lose the behavior later.

The important design choice is the **two-file model**:

```text
user_stories/story__checkout.md
user_stories/contracts/checkout.contract.md
```

The first file remains a small human-owned card. The second is a generated,
machine-oriented expansion containing acceptance criteria, oracle and
non-oracle boundaries, negative cases, non-goals, and candidate prompts.

This separation prevents two opposite failures:

- turning the human story into a giant pseudo-specification that nobody can
  quickly approve;
- leaving the generator with a one-sentence story too weak to detect drift.

The human story must still be reviewed by a person. An LLM-generated contract
does not replace the conversation or product decision. It only makes the
confirmation layer more explicit.

## The PDD source hierarchy

These artifacts have different jobs:

### 1. Issue or source intent

The issue, interview, PRD, or explicit product decision says what should change
and why. PDD story authoring deliberately derives the human story from this
source, not from existing prompts or code.

### 2. Human user story

The human story states one stable user capability and benefit. It is an
independent acceptance oracle because it is not reverse-engineered from the
implementation it will later judge.

Example from PDD itself:

```markdown
As a maintainer keeping prompts, code, tests, and examples aligned,
I want PDD to synchronize the right scope from my sync request,
so that local modules, whole projects, or issue-driven work stay consistent.
```

Source:
`user_stories/story__pdd_sync.md`

### 3. Generated story contract

The generated sibling contract expands the reviewed story and original issue
into testable acceptance detail. PDD's own sync story contract distinguishes:

- acceptance criteria such as dispatching global, dev-unit, and issue-driven
  sync correctly;
- oracle details such as routing and option propagation;
- non-oracle details such as console styling and exact generated code;
- negative cases such as rejecting invalid durable-mode combinations.

Source:
`user_stories/contracts/pdd_sync.contract.md`

Do not hand-edit generated story contracts. Edit the human story or source
intent and regenerate/re-align the contract.

### 4. Prompt

The prompt owns a development unit's implementation intent and declared public
interface. It should specify observable behavior and constraints without
transcribing private helper structure.

PDD itself is substantially self-hosting. For example, its
`architecture.json` maps:

```text
pdd/prompts/user_story_tests_python.prompt
    -> pdd/user_story_tests.py
```

The architecture entry also declares the module's public functions and prompt
dependencies. This lets generation be checked against a declared interface
instead of relying only on whatever code the model happens to emit.

### 5. Accumulated tests

Tests are permanent mold walls. A valid behavioral test should survive
regeneration and healthy refactoring. Tests constrain the implementation more
precisely than prose without making private implementation structure the source
of truth.

### 6. Generated code, examples, and evidence

These are reviewable artifacts produced and repaired by the tool. They are not
disposable: PDD contains gates against public-interface loss, excessive test
churn, empty-output overwrites, and other destructive regeneration failures.

## What the current code does

All paths below are relative to the PDD repository.

### CLI registration

`pdd/cli.py` imports the root Click group and registers commands:

```python
from .core.cli import cli
from .commands import register_commands

register_commands(cli)
```

`pdd/commands/__init__.py` adds `generate`, `test`, `fix`, `change`, `update`,
`sync`, `detect`, `story`, `contracts`, and the other commands to that group.
The implementation is a real CLI router, not a single prompt sent to one model.

### `pdd story add`

`pdd/commands/story.py` defines the `story` Click group and its `add`, `list`,
and `link` subcommands. `story add`:

1. accepts a GitHub issue, local Markdown source, or inline text;
2. requires one or more linked prompts/dev units;
3. resolves and validates those prompt paths;
4. supports a non-writing `--dry-run`;
5. calls `generate_user_story(...)`.

It also refuses `--update` when the story does not already exist, avoiding an
unexpected LLM-backed creation path.

### Independent story generation

`pdd/user_story_tests.py::generate_user_story()` enforces the independence
rule directly:

```python
# The issue -- not the prompt -- is the behavioral input.
issue_title, issue_text, issue_ref = resolve_issue_source(issue)

# The prompt is deliberately withheld so the story is an independent oracle.
story_markdown, story_cost, story_model = _llm_generate_story_markdown(
    title=title,
    issue_text=issue_text,
    issue_ref=issue_ref or issue,
    ...
)
```

The function rejects missing/non-`.prompt` targets, resolves the issue before
an LLM call, writes the human story, adds prompt-link metadata, and then
best-effort generates the sibling contract.

The contract is wrapped with a header containing:

```text
derived-from-story="..."
story-hash="..."
issue-ref="..."
```

`sync_user_story_contract()` compares the current human-story hash with that
header and regenerates the contract when they differ.

### Semantic story-to-prompt validation

`pdd/user_story_tests.py::run_user_story_tests()`:

1. discovers `story__*.md` files and prompts;
2. reads prompt links from story metadata;
3. combines the human story with its generated contract;
4. calls `detect_change(...)` against the linked prompts;
5. reports PASS only when no missing/stale behavior is found and all links
   resolve.

In the current implementation this is an **LLM-backed semantic check**. It can
catch a prompt that no longer promises the user outcome, but it depends on
provider availability and model judgment. It is not the same thing as running
the product.

### Deterministic story regressions

`pdd/story_test_generation.py::generate_story_regression_test()` reads the
story/contract bundle, extracts oracle and negative clauses, computes a stable
bundle hash, and writes a pytest file tagged with the story identity.

There are two coverage levels:

- **Behavioral**, when the contract declares a machine-readable entry point and
  the generated test can call the implementation.
- **Text-pin fallback**, when the generated test proves the story/contract
  bundle has not drifted but does not exercise runtime behavior.

That difference should be reported honestly. A fresh text-pin test is
traceability and staleness evidence, not proof that the feature works.

### Code generation and overwrite protection

`pdd/code_generator_main.py::code_generator_main()` resolves configuration and
output paths, preprocesses prompt/context inputs, selects local or cloud
generation, and writes the result.

Before overwriting established Python code, the current implementation checks
for public-surface regression and excessive test churn. If a compatibility
gate fails, it attempts to restore the prior file contents. It also refuses to
replace a non-empty existing artifact with empty generated output unless the
explicit escape hatch is set.

These checks are important because "code is generated" must not mean "mature
behavior can be erased without evidence."

### `pdd sync`

`pdd/sync_main.py::sync_main()` validates options, finds the prompt and
`.pddrc` context, detects target languages, resolves paths, and dispatches the
dev unit to `sync_orchestration()`.

The orchestration loop can choose and execute operations such as:

```text
generate -> example -> crash repair -> verify -> test/test_extend -> fix -> update
```

It runs actual tests, persists fingerprints/run reports, tracks cost and
attempts, and uses compatibility gates around model-written changes. The
precise next operation is state-dependent; `sync` is a bounded state machine,
not a fixed shell macro.

Because it can invoke models and rewrite multiple artifacts, use scoped sync
only after baseline tests and command-help review. Whole-project sync and
`--force` require explicit scope and authorization.

## How to use PDD

Start every task with discovery:

```bash
git status --short --branch
find .. -name AGENTS.md -print
find . -maxdepth 3 \
  \( -name '.pddrc' -o -name 'architecture.json' -o -name '*.prompt' \)
pdd --version
pdd <command> --help
```

Then route the work by intent.

### Existing PDD dev unit

```bash
# Run the repository's focused baseline tests first.
pytest path/to/relevant/tests

# Inspect the installed options and preview mechanism.
pdd sync --help

# Synchronize only the intended dev unit.
pdd --force sync <dev-unit>

# Re-run focused and broader repository tests.
pytest path/to/relevant/tests
pytest

# Review source and generated changes together.
git diff
```

Use `--force` only when overwrite scope is already understood and authorized.
It is not a default convenience flag.

### Current observable bug

```bash
pdd bug <issue-url>
# Review the reproduction and prove that it fails for the reported symptom.
pdd fix <issue-url>
# Run the repository's real tests.
```

The reproduction must fail before the fix and pass afterward. Do not let the
fixer weaken a valid regression.

### New product/specification intent

```bash
pdd change <issue-url>
# Review the source-truth changes.
pdd --force sync <affected-dev-unit>
# Run the repository's real tests.
```

Do not use `change` to skip reproduction of a current runtime failure.

### Add a user story

```bash
pdd story add ./issue.md --devunit <dev-unit> --dry-run
pdd story add ./issue.md --devunit <dev-unit>
```

Then:

1. read and approve/edit the human story;
2. re-align the generated contract if the story changed;
3. inspect the contract for false or over-broad criteria;
4. run `pdd detect --stories`;
5. repair prompt drift with `pdd fix user_stories/story__<slug>.md`;
6. generate a regression with `pdd test --from-story ...`;
7. run `pytest -m story` plus the normal repository suite.

The local issue file makes issue retrieval reproducible, but story and contract
authoring still require a configured model provider.

### Brownfield adoption

Do not convert a repository wholesale:

1. choose one high-churn module with a stable public interface;
2. write characterization and negative tests against untouched code;
3. write a prompt describing observable behavior and the interface;
4. regenerate and run the characterization suite;
5. refine the mold until repeated generation is behaviorally stable;
6. only then promote the prompt to source of truth and add CI gates.

## What to keep straight

### Story versus prompt

- **Story:** user-level outcome and benefit, potentially spanning dev units.
- **Prompt:** implementation intent and interface for a particular dev unit.

A story can judge several prompts. A prompt can satisfy several stories. They
are not interchangeable.

### Story validation versus runtime tests

- `pdd detect --stories` semantically compares stories/contracts with prompts.
- `pytest -m story` runs deterministic tests linked to stories.
- ordinary unit/integration/end-to-end tests verify the implementation.
- human acceptance verifies that the product actually delivers the intended
  value.

No single layer replaces the others.

### Generated contract versus human authority

The generated contract is precise but fallible. Humans approve the story and
must spot-check the contract. If the contract invents behavior, correct the
story/source or regenerate it; do not quietly enshrine the hallucination as a
test.

### Prompt source versus implementation freedom

Prompts should constrain observable behavior and public interfaces. They should
not freeze private helper names, incidental call order, or today's internal
structure. A different, equally correct implementation should still satisfy
the prompt.

## Practical assessment

PDD's strongest idea is not "LLMs write code from prose." Many tools do that.
Its stronger idea is a versioned chain of intent and independent constraints:

```text
product intent
  -> human story
  -> generated acceptance contract
  -> prompt/interface
  -> accumulated tests
  -> generated implementation
  -> verification and evidence
```

That chain attacks specification drift: a model cannot safely redefine success
merely by rewriting code and its own tests together.

The main risk is false confidence. LLM-authored stories, contracts, semantic
validation, and generated tests can agree with one another and still be wrong.
PDD is strongest when:

- stories are derived independently from real product intent;
- humans review the small story and sample the generated contract;
- negative behavior has executable tests;
- runtime and integration tests remain independent;
- synchronization is scoped;
- model-backed checks are supplemented by deterministic gates; and
- evidence distinguishes semantic, textual, and behavioral coverage.

In short: PDD turns prompts into maintainable source only by surrounding them
with stronger artifacts than prompts alone.

## Further reading

- [`PDD_WITH_ANY_AGENT_HARNESS.md`](PDD_WITH_ANY_AGENT_HARNESS.md) — operational
  router, workflows, safety, CI, and brownfield adoption.
- PDD `docs/generating_user_stories.md` — detailed current user-story workflow.
- PDD `docs/prompting_guide.md` — prompt design and story contract coverage.
- PDD `docs/coverage_contracts.md` — contract-rule-to-story/test coverage.
- PDD `docs/contract_check.md` — deterministic contract structure checks.
- [Agile Alliance: User Stories](https://agilealliance.org/glossary/user-stories/)
- [Agile Alliance: Three C's](https://agilealliance.org/glossary/three-cs/)
- [Agile Manifesto principles](https://agilemanifesto.org/principles)
- [The 2020 Scrum Guide](https://scrumguides.org/docs/scrumguide/v2020/2020-Scrum-Guide-US.pdf)
