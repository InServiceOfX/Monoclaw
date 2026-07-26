# PDD: Start Here

This is the beginner-facing guide to Prompt-Driven Development (PDD). It is
written for someone who understands the product or problem they want to solve
but does not want to memorize software-development terminology, PDD commands,
or special filenames.

If that describes you, the short answer is:

> Tell the AI agent what you want in ordinary language. Ask it to turn your
> explanation into a draft product requirements document and a small set of
> user stories. Review those human-readable documents first. Let the agent and
> PDD create the technical PDD files after you approve the intent.

You should not have to begin by writing `.prompt` files, `.pddrc`, or
`architecture.json`.

This guide is the friendly entry point. The other two documents are references:

- [`PDD_CONCEPTS_AND_USER_STORIES.md`](PDD_CONCEPTS_AND_USER_STORIES.md)
  explains the ideas, the Agile/Extreme Programming background of user
  stories, and what the PDD code actually does.
- [`PDD_WITH_ANY_AGENT_HARNESS.md`](PDD_WITH_ANY_AGENT_HARNESS.md) gives an AI
  coding agent the detailed command-routing and safety rules.

The PDD implementation checked for this guide is version `0.0.309`, repository
commit `17b41a779`, on 2026-07-25. PDD changes quickly, so the installed
command's help is authoritative.

## The easiest mental model

PDD is a way to preserve the **reason for the software**, not just the software
that happened to be written.

Imagine ordering a custom machined part. You would not want the only surviving
record to be the finished part. You would also keep the drawing, dimensions,
tolerances, material requirements, and inspection results. If the part had to
be made again, those records would constrain the new part.

PDD applies a similar idea to software:

```text
what people need
       |
       v
PRD and user stories          human-readable intent
       |
       v
architecture and prompts      precise technical specification
       |
       v
generated code and tests      implementation and evidence
```

The prompt in Prompt-Driven Development is not a disposable chat message. A
PDD `.prompt` file is a versioned engineering artifact that tells PDD what one
development unit must do, what it may depend on, what interface it exposes, and
what it must never do.

That does **not** mean you need to author that artifact yourself. A useful
division of work is:

- You explain the need, the users, examples, constraints, and what success
  looks like.
- The AI agent helps organize that explanation into a PRD and user stories.
- You correct and approve that human-readable intent.
- The agent invokes PDD and reviews the generated architecture and prompts.
- PDD generates or synchronizes code, tests, examples, and evidence.
- The agent runs the checks and reports what is actually proven.

## Yes, you can start by dictating

You do not need to know the user-story formula before speaking. You can say:

> We test hydraulic valves. I want to upload a pressure trace and have the
> system highlight intervals outside the permitted pressure band. The test
> engineer needs to see when the problem started, how long it lasted, and the
> worst reading. Never alter the original uploaded data.

That is already useful product intent.

An AI agent can turn it into candidate stories such as:

> As a test engineer, I want out-of-limit intervals highlighted on an uploaded
> pressure trace so that I can locate and diagnose a valve problem without
> inspecting every sample manually.

It can then ask about missing decisions:

- What file formats must be accepted?
- Is the permitted band fixed or selected per test?
- How should missing or corrupt samples be handled?
- Does “never alter” mean retaining the original bytes, values, or both?
- What result would convince you that the feature works?

This question-and-answer process is part of the work. A user story is a compact
reminder of a need, not a substitute for the conversation and examples behind
it.

## What a user story is

A common format is:

```text
As a <kind of user>,
I want <a capability>,
so that <a useful outcome>.
```

For example:

```text
As a test engineer,
I want to export all out-of-limit intervals as CSV,
so that I can attach objective evidence to the test report.
```

The grammar is optional. The useful parts are:

1. **Who** needs something?
2. **What outcome or capability** do they need?
3. **Why does it matter?**
4. **What examples, limits, and failure cases define success?**

You may dictate a rough need and ask the agent to supply the structure. Do not
invent a fake “user” for every low-level technical task. Security maintenance,
dependency updates, data migrations, and infrastructure work may be clearer as
plain requirements or engineering tasks.

User stories came from Extreme Programming and are now common in Agile product
work. They are not a mandatory Scrum file format. Their value is that a person
can discuss and approve a small outcome before implementation details take
over.

## PRD versus user stories

A PRD and a user story operate at different zoom levels.

### Product requirements document

The PRD describes the product or larger change:

- the problem and intended users;
- goals and non-goals;
- the important workflows;
- constraints, risks, and assumptions;
- acceptance criteria and examples;
- major technical or operational requirements, when known.

It is the map of the whole job.

### User story

A user story describes one small, valuable slice of behavior from a person's
point of view.

It is one destination or trip on the map.

One PRD usually leads to several candidate user stories. Those stories can then
be split, reordered, clarified, or rejected. The agent should not turn every
sentence of the PRD into a story mechanically.

## The recommended beginner workflow

### Phase 1: Say what you want

Talk, type, paste notes, or dictate. Useful information includes:

- Who has the problem?
- What are they doing today?
- What should become possible or easier?
- Why is it valuable?
- Give one normal example.
- Give one difficult or failure example.
- What must always happen?
- What must never happen?
- What is definitely out of scope?

You do not have to answer everything at once.

### Phase 2: Have the agent draft human-readable intent

Ask the agent to inspect the repository and create or update a local Markdown
PRD, conventionally:

```text
docs/PRD.md
```

Ask it to propose a small set of user stories as part of that document or in a
separate draft. At this point, do not generate code. Read the draft and correct
it in ordinary language.

The PRD filename is a convention, not a PDD requirement. If the repository
already has a requirements location or template, use that instead.

### Phase 3: Approve the product intent

Check:

- Does it solve the problem you actually meant?
- Are the users and outcomes right?
- Are important limits and “must not” rules present?
- Are uncertain assumptions labeled as questions rather than facts?
- Is the first version small enough to build and verify?

This is the most valuable place for your attention. It is much cheaper to fix
an incorrect sentence here than incorrect generated architecture and code
later.

### Phase 4: Bootstrap the PDD project

This phase concerns creating a **whole greenfield architecture and its initial
prompts**. It is not the command used every time a story or generated contract
is added.

For the current PDD CLI, the supported greenfield architecture workflow begins
with a **GitHub issue URL whose body contains the PRD**:

```bash
pdd generate https://github.com/OWNER/REPO/issues/NUMBER
```

By default, that workflow generates the architecture and prompts, including:

```text
.pddrc
architecture.json
architecture_diagram.html
prompts/*.prompt
```

Posting a GitHub issue is an external action. The AI agent should show you the
draft and ask before creating or posting it. If you already created the issue,
give the agent its URL.

PDD also has an experimental incremental PRD mode for updating an **existing**
PDD architecture:

```bash
pdd generate --incremental --experimental-prd docs/PRD.md
```

That mode expects an existing `architecture.json`; it is not currently the
ordinary greenfield local-file bootstrap.

If GitHub cannot be used, keep the local PRD and ask the agent to explain the
available manual or project-specific bootstrap. Do not let it claim that
`pdd story add` automatically turns a local story into a new architecture; the
current command expects an existing prompt or development-unit association.

### Do I need a GitHub issue for every story or contract?

No. PDD uses “issue source” as a broad name for the independent product intent
from which it derives a story. That source can be:

- a GitHub issue URL or issue number;
- a local Markdown file; or
- text supplied directly on the command line.

For example, after the relevant prompt/dev unit exists:

```bash
# Durable, reviewable local source; no GitHub issue or issue fetch.
pdd story add docs/requirements/pressure_trace_limits.md \
  --devunit pressure_trace_analyzer

# Or start directly from dictated/typed text.
pdd story add \
  --text "As a test engineer, I need out-of-limit pressure intervals highlighted so I can diagnose a valve problem." \
  --title "Pressure trace limits" \
  --devunit pressure_trace_analyzer
```

The inline form persists the supplied text under `.pdd/story_sources/` so the
generated contract retains a local source reference. Both forms still use an
LLM to author the canonical story and generated contract, but neither needs a
GitHub issue.

The required `--devunit` or `--prompt` is important: a story-to-contract mapping
does not create a greenfield architecture. It describes acceptance intent for
one or more prompts that already exist.

### Phase 5: Review the generated plan

The agent should summarize, in plain language:

- the proposed development units;
- what each unit is responsible for;
- important interfaces and dependencies;
- which prompts correspond to which code files;
- assumptions PDD made;
- questions or risks that remain.

You do not need to read every line of every `.prompt` file, but the agent should
not treat generated prompts as automatically correct. Product intent can be
lost or distorted during any transformation.

### Phase 6: Build one approved slice

The agent should synchronize one development unit or a small coherent set, run
the relevant tests, and report:

- what changed;
- which requirements or stories it implements;
- what tests passed;
- what remains unproven;
- whether prompts, tests, and generated code are aligned.

Small slices make mistakes easier to identify and correct.

### Phase 7: Preserve stories as acceptance intent

Once prompts exist, PDD can associate human stories with those prompts and
derive detailed contracts and regression tests.

The conventional files are:

```text
user_stories/story__pressure_trace_limits.md
user_stories/contracts/pressure_trace_limits.contract.md
tests/story_regression/test_story_pressure_trace_limits.py
```

In the current CLI, a command such as:

```bash
pdd story add docs/requirements/pressure_trace_limits.md \
  --devunit pressure_trace_analyzer
```

creates a story for an existing development unit and best-effort derives its
contract. To generate executable regression coverage, run the separate
follow-up:

```bash
pdd test \
  --from-story user_stories/story__pressure_trace_limits.md \
  --output tests/story_regression/test_story_pressure_trace_limits.py
```

The `pdd story add --generate-regression` option only prints this handoff
command; it does not run it. The precise flags may change, so the agent must
check `pdd story add --help` and `pdd test --help`.

The short human story remains the acceptance-level source. The generated
contract is a more detailed, machine-oriented expansion and must remain
traceable to it.

## What you write and what the tools write

| Artifact | Normal owner | Do you need to hand-write it? |
|---|---|---|
| Spoken or typed product idea | You | Yes, but ordinary language is enough |
| PRD Markdown | You + AI agent | Usually reviewed by you, drafted by agent |
| Human user stories | You + AI agent | Dictate or edit; agent can format them |
| GitHub PRD issue | You + agent | Approve before agent posts it |
| `.pddrc` | PDD + agent | Normally no |
| `architecture.json` | PDD + agent | Normally no |
| `architecture_diagram.html` | PDD | No |
| `prompts/*.prompt` | PDD + agent | Normally no; review important decisions |
| Generated story contract | PDD | No; review for faithful interpretation |
| Source code and tests | PDD + agent | No, but review and test the result |

“Normally no” does not mean “never inspect.” It means these are not the price
of admission for describing your product.

## Do names and directories matter?

They matter to PDD, but the user should not have to keep them in their head.
Use the repository's established configuration. For a new project, prefer the
generated or conventional layout:

```text
project-root/
├── .pddrc
├── architecture.json
├── architecture_diagram.html
├── docs/
│   └── PRD.md
├── prompts/
│   └── <development-unit>_<language>.prompt
├── user_stories/
│   ├── story__<story-slug>.md
│   └── contracts/
│       └── <story-slug>.contract.md
├── tests/
│   └── story_regression/
│       └── test_story_<story-slug>.py
└── <source directories configured by .pddrc>
```

Important rules:

- Put `.pddrc` and the primary `architecture.json` at the project root unless
  an established nested-project layout says otherwise.
- `.pddrc` defines contexts and output directories. Relative configured paths
  are resolved from the applicable configuration/project location.
- `architecture.json` maps prompt filenames to generated code paths and records
  dependencies.
- Prompt names and locations identify development units to several PDD
  commands. Do not casually rename or move them.
- Story identity is based on the shared slug:
  `story__<slug>.md`, `<slug>.contract.md`, and corresponding story-test
  metadata.
- A repository may intentionally use nested `.pddrc` and
  `architecture.json` files. Inspect before assuming there is only one.

The practical rule is:

> You provide names that make sense to people. The agent applies the project's
> PDD naming and directory conventions, then checks that PDD can resolve them.

## A prompt you can give any AI coding agent

Copy this and replace the bracketed text:

```text
Use Prompt-Driven Development for this project.

I am describing product intent, not implementation:

[Describe the problem and what you want in ordinary language.]

Possible users:
[Who experiences the problem? It is okay if I am unsure.]

Examples, constraints, and must-not rules:
[Add anything I know. It is okay to leave this incomplete.]

First inspect the repository and determine whether it is already PDD-managed.
Then:

1. Draft or update a plain-language PRD and a small set of candidate user
   stories. Label assumptions and open questions.
2. Show me the human-readable intent for approval before generating code or
   taking external actions.
3. Do not ask me to hand-author .prompt files, .pddrc, or architecture.json
   unless the installed PDD workflow cannot generate what is needed.
4. If this is greenfield, explain that the current supported PDD architecture
   bootstrap uses a GitHub issue containing the approved PRD. Ask before
   creating or posting that issue.
5. After approval, use the installed PDD CLI and its current --help output to
   generate and review the architecture, configuration, and prompts.
6. Work in one small approved development unit at a time. Run relevant tests
   and report evidence, remaining uncertainty, and any drift among intent,
   prompts, tests, and generated code.
7. Follow this repository's branch, safety, review, and PDD ownership rules.

Explain decisions to me in product language first. I should be able to review
the workflow without already knowing PDD internals.
```

For an even shorter start:

```text
Use PDD. I want [ordinary-language description].
Turn this into a draft PRD and a few user stories for my approval.
Do not generate code yet, and do not ask me to write PDD plumbing files.
```

## What the AI agent should inspect

Before changing anything, the agent should determine:

1. Which `pdd` executable and version are installed?
2. Is the current Git branch allowed for changes?
3. Are `.pddrc`, `architecture.json`, `prompts/`, or story files already
   present?
4. Which source files are actually PDD-managed?
5. Does the repository have its own PDD guide or conventions?
6. Is this a greenfield product, a new feature in a PDD project, or a change to
   ordinary hand-maintained code?

This inspection prevents the agent from regenerating code merely because PDD
is installed.

## Three important cautions

### PDD installation does not make every file PDD-managed

The agent must find a matching prompt, architecture entry, or explicit project
rule before treating code as generated output.

### A fluent generated document can still misunderstand you

Read the PRD and user stories. Ask for concrete examples. Correct words that
have special meaning in your domain.

### Passing checks prove only what was checked

PDD can perform semantic validation with an LLM and can generate executable
tests. Those are different kinds of evidence. The agent should state whether a
claim was verified by a deterministic test, an LLM review, human acceptance,
or merely inferred.

## The whole workflow in one sentence

Describe the need in your own words, approve a human-readable PRD and small
user stories, let PDD and the agent translate that intent into versioned
technical prompts and code, and require tests plus review to show that the
translation stayed faithful.
