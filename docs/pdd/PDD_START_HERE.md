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

You also should not have to decide among GitHub, local-file, and inline story
inputs or identify a technical component name. An AI agent following the story
playbook owns those decisions.

There is one adoption decision: the project must be explicitly configured to
use PDD. After that, you do not need to say “use PDD” or “create story
coverage” every time. Ordinary requests, corrections, removals, examples, and
constraints are sufficient input. The agent preserves accepted intent and
routes it through PDD.

This guide is the friendly entry point. The other documents are references:

- [`PDD_WORKSPACE_BOOTSTRAP.md`](PDD_WORKSPACE_BOOTSTRAP.md) explains how
  workspace-root instruction files make Claude, Codex, Cursor, and other
  harnesses load the same Git-versioned Monoclaw policy.
- [`PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md`](PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md)
  tells an AI agent how to accept evolving natural-language intent and select
  the internal PDD workflow automatically.
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

PDD also has an experimental local-PRD mode for updating a project that already
has PDD architecture. The agent can determine whether that mode applies; the
user does not choose it.

If GitHub cannot be used, keep the local PRD and ask the agent to explain the
available manual or project-specific bootstrap. Adding acceptance intent to an
existing PDD specification and creating a brand-new PDD architecture are
different internal operations, but the agent—not the user—owns that routing.

### Do I need a GitHub issue for every story or contract?

No. PDD can derive a story from:

- ordinary conversation preserved in the repository;
- a local Markdown file; or
- a GitHub issue when one is useful.

The agent should normally preserve conversational intent as a versioned local
requirements record, discover which part of the product it affects, and invoke
PDD. Neither a GitHub issue nor PDD command knowledge is required from the user.

The story and contract authoring step still uses an LLM. A local requirements
record avoids a GitHub dependency, not the configured model call.

### Phase 5: Review the generated plan

The agent should summarize, in plain language:

- the proposed parts of the product;
- what each part is responsible for;
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

Once the technical PDD specification exists, PDD can associate human stories
with the affected parts and derive detailed contracts and regression tests.

The conventional files are:

```text
user_stories/story__pressure_trace_limits.md
user_stories/contracts/pressure_trace_limits.contract.md
tests/story_regression/test_story_pressure_trace_limits.py
```

The agent creates the human story and asks PDD to derive its contract. The agent
then separately asks PDD to generate executable regression coverage, inspects
whether that test is genuinely behavioral, and runs it. These are separate
internal operations, but the user only reviews the intended meaning and the
reported evidence.

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

## No required prompt template

For a project that is already configured to use PDD, simply talk about the
product:

> Highlight out-of-limit pressure intervals.

> Actually, merge intervals separated by less than two seconds.

> Remove CSV export.

> Never alter the original uploaded samples.

Those are sufficient inputs. The agent instructions—not a special user
incantation—cause the messages to be preserved and routed through PDD.

For a project not yet configured for PDD, one adoption request is sufficient:

> Set this project up to use Prompt-Driven Development. I will describe the
> product in ordinary language; preserve my requests and handle the PDD
> mechanics for me.

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
