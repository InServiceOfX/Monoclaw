# PDD Prompt Graphs and Multi-File Artifact Bundles

This document records a correction prompted by the official-channel video
[`Prompt Driven Development Intro`](https://youtu.be/UsdgyHBFE0g) and by a
source audit of PDD `0.0.309` at commit `17b41a779`.

The video repeatedly says:

> one prompt per code file

That is a useful way to demonstrate small, isolated regeneration, but it is not
a sound universal architecture rule.

The better rule is:

> A project's prompt suite collectively specifies the project. Each bounded
> logical unit should own the smallest coherent artifact bundle that can be
> regenerated and verified safely. A physical file is one possible boundary,
> not the definition of the boundary.

## Video archive

The 9:20 transcript with 237 caption segments is archived at:

```text
/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/
Prompt_Driven_Development_Prompt_Driven_Development_Intro.json
```

It is indexed in:

```text
/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/index.json
```

This video is effectively another edit of “Prompt Driven Development: A Clear
Walkthrough.” It uses the same module-regeneration demonstration and repeats
the same major claims:

- prompts and tests are the durable mold;
- generated code is replaceable output;
- prompt space is more compact and deliberate than accumulated chat/code
  patches;
- chat is an interface, not a durable source file;
- PDD is appropriate for long-lived, verifiable behavior;
- architecture, performance, and security review remain necessary.

Its “one prompt per code file” statement is the point that needs refinement.

## Project mapping versus generation-unit mapping

There are two different relationships:

### Whole project

The **collective PDD program** maps to the whole project:

```text
Product intent and architecture
              |
              v
shared contracts, policies, and context
              |
              v
graph/suite of versioned prompts
              |
              v
all generated artifact bundles
              |
              v
the complete codebase
```

PDD's own prompting guide defines a **PDD Program** as a versioned prompt suite
plus its includes, examples, tests, architecture metadata, and configuration.
That is the correct project-level source model. It is not one giant prompt
containing the entire project.

### Bounded generation unit

Within the graph, each unit should be sized by:

- one coherent responsibility or contract;
- interfaces that can be stated clearly;
- artifacts that need to change together;
- tests that can verify the unit;
- a context small enough for reliable regeneration;
- a safe failure and rollback boundary.

Sometimes that is one file. Sometimes it is several inseparable files.

## Why C++ exposes the problem

A C++ class commonly has:

```text
include/ValveController.h
src/ValveController.cpp
```

The header owns the public contract. The source file implements that contract.
A signature change may require both files to change together. Calling these two
unrelated PDD units merely because they are two filesystem entries confuses
physical layout with software responsibility.

A more faithful logical unit is:

```text
ValveController logical unit
├── public API and invariants
├── include/ValveController.h
├── src/ValveController.cpp
├── compile/link verification
└── persistent behavioral tests
```

Other common bundles include:

- a C header plus C implementation;
- a C++ template header plus inline implementation file;
- a parser grammar plus generated visitor glue;
- a schema plus migration and generated model;
- a web component plus tightly coupled stylesheet;
- a protocol definition plus generated client/server bindings;
- a plugin manifest plus its entry point.

The general criterion is **cohesion under regeneration**, not file count.

## Do not replace the rule with one mega-prompt

“The prompts collectively map to the whole project” does not imply:

```text
one enormous prompt -> entire repository
```

That would sacrifice the isolation, context control, parallelism, and local
verification PDD is trying to gain.

The recommended hierarchy is:

```text
project-level intent
    -> architecture and shared contracts
        -> logical prompt units
            -> one or more generated artifacts per unit
```

Shared project rules should live in canonical context or contract prompts and
be included by affected units. A change spanning the system updates several
units in the prompt graph and then runs scoped or project-wide synchronization.

## What current PDD already supports

Current PDD already supports the **collective project graph**:

- `architecture.json` contains many prompt entries and their dependencies;
- each entry has a prompt `filename` and generated `filepath`;
- prompt `<include>` directives provide shared contracts and curated
  dependency context;
- issue-driven workflows identify and synchronize multiple affected units;
- `pdd sync` with no basename performs project-wide architecture sync in the
  currently installed CLI.

Therefore, no core change is required to say:

> The versioned prompt suite and tests collectively govern the project.

## Current one-primary-output limitation

Current PDD does not provide a first-class logical unit that atomically owns
several production code files.

The evidence in the current fork is:

- `pdd/templates/architecture/architecture_json.prompt` requires singular
  `filename` and `filepath` fields for each architecture entry.
- `prompts/agentic_arch_step5_design_LLM.prompt` explicitly instructs the
  architecture generator that each module generates one code file.
- `pdd/commands/generate.py` exposes one `PROMPT_FILE` and one `--output` for
  standard prompt generation.
- `pdd/code_generator_main.py::code_generator_main()` returns one generated
  code string and writes one `p_output`.
- `pdd/agentic_sync_runner.py::ModuleState` tracks synchronization state for a
  single module.
- `.pddrc` may configure `code`, `test`, and `example` artifact classes, but
  that is not the same as several primary production-code outputs belonging to
  one logical unit.

The prompt suite can generate many project files, but it presently does so as
many one-primary-output units.

## C++ workflow available without changing PDD

Until native bundles exist, represent a C++ object with a shared canonical
contract and two linked generation prompts:

```text
prompts/
├── _context/
│   └── valve_controller_contract.prompt
├── valve_controller_header_cpp.prompt
└── valve_controller_implementation_cpp.prompt
```

Both generated prompts include:

```xml
<include>prompts/_context/valve_controller_contract.prompt</include>
```

The architecture maps them separately:

```text
valve_controller_header_cpp.prompt
    -> include/ValveController.h

valve_controller_implementation_cpp.prompt
    -> src/ValveController.cpp
    -> depends on the header prompt
```

Verification must compile and link both files and run the same behavioral test
suite. A story covering the object should link both prompts as a cross-unit
story.

This workaround preserves one canonical contract and lets the existing PDD
engine operate. Its limitations are:

- header and implementation generation are not one atomic logical operation;
- one child prompt may synchronize without the other;
- failures and evidence are reported per physical output;
- back-propagation can update one prompt while leaving the shared contract or
  sibling stale;
- the human sees two internal units for what is conceptually one object.

Agent policy should hide that mechanical split from the product/domain user.

## When the fork needs code changes

No fork change is needed merely to have a prompt suite govern the entire
project.

A fork change **is** needed if we require:

> One logical PDD unit, specified by one or more source prompts, owns and
> atomically regenerates a bundle such as `ValveController.h` and
> `ValveController.cpp`.

That should be treated as an **artifact-bundle feature**, not as permission for
an LLM to emit an unstructured multi-file blob.

## Proposed artifact-bundle model

An architecture entry could evolve toward a shape such as:

```json
{
  "name": "valve_controller",
  "source_prompts": [
    "prompts/valve_controller_cpp.prompt"
  ],
  "artifacts": [
    {
      "role": "public_header",
      "path": "include/ValveController.h",
      "language": "cpp"
    },
    {
      "role": "implementation",
      "path": "src/ValveController.cpp",
      "language": "cpp"
    }
  ],
  "dependencies": [],
  "verification": {
    "commands": [
      "cmake --build build",
      "ctest --test-dir build --output-on-failure"
    ]
  }
}
```

The exact schema requires design work. Important properties are:

- one stable logical-unit identity;
- one or more source prompt files;
- named output roles and explicit paths;
- deterministic structured output extraction;
- generation into temporary paths;
- validation of every artifact before publication;
- atomic commit or rollback of the whole bundle;
- cross-artifact interface checks;
- accumulated tests that survive regeneration;
- evidence and provenance for every member;
- `sync`, `update`, `trace`, `fix`, story linkage, and drift detection operating
  on the logical unit rather than an arbitrary file.

Generation may still call the model once per artifact internally. The
user-visible semantic contract is that the bundle succeeds or fails together.
That is more important than forcing one model response to contain every file.

## Likely PDD implementation surfaces

A first-class implementation would need changes across:

1. architecture schema/templates and validation;
2. prompt-to-output path resolution;
3. standard generation output protocol;
4. `code_generator_main` return and write behavior;
5. sync planning, state, and evidence manifests;
6. transaction/rollback publication;
7. update and reverse-synchronization logic;
8. story-to-unit mapping and contract coverage;
9. trace/fix/test workflows;
10. C/C++ language conventions, compile/link discovery, and tests;
11. compatibility migration for existing singular `filepath` entries.

This is not a small tweak to the filename convention.

## Recommended decision

1. Adopt the **prompt graph governs the project** language immediately.
2. Define PDD units by coherent regeneration/verification boundaries, not
   physical files.
3. Use shared-contract plus linked-output prompts as the current compatibility
   pattern for C++ header/source pairs.
4. Do not modify the PDD fork on `main`.
5. If native atomic bundles are important after a small C++ pilot, create a
   feature branch and implement the artifact-bundle model with tests and a
   backward-compatible architecture schema.

The video is right about maintaining prompt/test molds and avoiding prompt
sprawl. Its one-prompt/one-file mapping should be understood as the current
tool's simplest execution shape, not a universal law of Prompt-Driven
Development.
