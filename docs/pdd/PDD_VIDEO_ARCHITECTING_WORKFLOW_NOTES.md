# Notes on “Architecting with AI: The PDD Workflow Explained”

Source video:
[`Architecting with AI: The PDD Workflow Explained`](https://youtu.be/4HqKpuk6ZBk)
by the Prompt Driven Development channel.

YouTube reports that the video was published on December 23, 2025. Its captions
were archived on July 26, 2026 at:

```text
/Users/ernestyeung/.openclaw/workspace/Data/Public/youtube-transcripts/
Prompt_Driven_Development_Architecting_with_AI_The_PDD_Workflow_Explained.json
```

The archive contains a 9:03 transcript with 282 timestamped segments and is
indexed in `Data/Public/youtube-transcripts/index.json`.

## Verdict

Yes, this video materially improves our understanding of PDD. It is more useful
for the **greenfield architecture workflow** than the two introductory videos.
It explains the missing transformation between an ordinary product
specification and the collection of `.prompt` files.

It also validates the usability concern in
[`PDD_INTENT_FIRST_WORKFLOW.md`](PDD_INTENT_FIRST_WORKFLOW.md). The demonstrated
workflow exposes several mechanical stages, and the presenter explicitly uses
Claude Code or Cursor to help perform some of them. A product user should
control the decisions at those stages without being required to operate their
file formats and commands.

The video does not discuss user stories. That is important evidence that user
stories are a separate acceptance/drift-detection layer in the current PDD
tooling, not the central input to the greenfield generation pipeline.

## The workflow shown in the video

The demonstrated sequence is:

```text
Product specification / PRD
          |
          v
Technology-stack description
          |
          v
architecture.json + architecture visualization
          |
          v
one or more module prompts
          |
          v
dependency-ordered synchronization
          |
          v
generated code
```

The presenter emphasizes three review levels:

1. make the product specification say what you want;
2. make the architecture partition and connect the system the way you want;
3. make the generated module prompts say what you expect;
4. only then synchronize the generated implementation.

That is a good PDD model. The correction for agent-assisted use is that “make
sure it is what you want” does not imply “manually edit every underlying file.”
An AI agent can draft and maintain the artifacts while the human approves their
meaning.

## What the video clarifies

### The PRD is ordinary product input

At about 1:06, the presenter says an architecture template needs a PRD and
recommends a technology-stack description. At about 3:00, he clarifies that the
PRD can use any format; PDD's specialized prompting rules apply to the generated
prompt files, not to the PRD.

This supports a simple intake experience:

> Describe the product in ordinary language. The agent may organize that into a
> PRD and technology choices without making the user learn a PDD schema.

The PRD is therefore a flexible whole-product design input. It is not the
per-module source that regenerates code; the resulting `.prompt` files perform
that role.

### Architecture is a real review boundary

The architecture step partitions the product into modules, records
dependencies, and produces a visual representation. The presenter repeatedly
says that complicated projects need careful architecture iteration.

This means our simpler workflow must not hide architecture **decisions**. It
should hide JSON mechanics while presenting the important decisions:

- what major product parts will exist;
- what responsibility belongs to each;
- how they communicate;
- which interfaces and data stores are shared;
- what depends on what;
- whether coupled outputs form one logical regeneration boundary.

A domain user can approve the product decomposition in plain language or a
diagram. A technical owner should inspect consequential boundaries and
interfaces. Neither person should be required to edit `architecture.json`
directly.

### The agent is already part of the intended workflow

At about 3:14, the presenter says he uses Claude Code or Cursor to help write
the specification. At about 6:54, he says he asks an AI tool to inspect
`architecture.json` and generate a Makefile that runs PDD synchronization in
dependency order.

This strongly supports the conclusion that PDD mechanics belong behind an
agent-facing interface. If the recommended workaround is already “ask the AI
to read the JSON and automate the commands,” the product should expose that
orchestration directly and consistently.

### Prompt generation proceeds from the architecture

The architecture describes the module graph. A prompt-generation template then
uses that graph and the product documentation to create the prompts for the
modules. Code generation proceeds in dependency order so lower-level
dependencies are available before their consumers.

This is the missing explanation behind the user's earlier question:
unstructured human prompts do not directly become the entire codebase in one
opaque step. The agent first consolidates product intent, proposes an
architecture, and then creates a **prompt graph** whose members collectively
govern the project.

## What the video does not settle

### It does not explain user stories

The video presents the human-controlled layers as specification, architecture,
and prompts, followed by synchronization. It does not mention `pdd story`,
independent story contracts, or story regression tests.

That makes our current interpretation more likely, not less:

- prompts and tests are the core technical mold;
- stories are selective independent acceptance oracles added by newer/current
  tooling;
- stories should not become mandatory paperwork for every product request;
- when a story is valuable, the human approves its meaning while the agent
  handles its files and commands.

### It does not resolve one-prompt/one-file

Near the beginning the presenter says one prompt exists for every “code
module,” but later the discussion uses “code file.” The template discussion
also describes generating multiple prompt files from an architecture. These
statements do not prove that one prompt can atomically own an arbitrary
multi-file code bundle.

Continue to use the policy in
[`PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md`](PDD_PROMPT_GRAPH_AND_ARTIFACT_BUNDLES.md):
the collective prompt graph maps to the project, and logical regeneration
boundaries should not be confused with physical file count. Current standard
PDD still records singular prompt/output mappings; native atomic bundles remain
a possible fork enhancement.

## Version differences from current PDD

This is a December 2025 demonstration, not authoritative current CLI
documentation.

The video says:

- only two templates are available;
- whole-project synchronization is a future goal;
- the operator must infer dependency order and run module synchronization
  manually, commonly through an AI-generated Makefile;
- directly editing the large architecture JSON is a painful current step.

The locally installed PDD `0.0.309` on July 26, 2026 reports three templates:

- `architecture/architecture_json`;
- `generic/generate_pddrc`;
- `generic/generate_prompt`.

Its current `pdd sync --help` also says that omitting the basename performs
project-wide Tier 1 architecture synchronization. Therefore, the video's
manual Makefile workaround explains the design history but must not override
the installed command's current behavior.

Before executing the workflow, an agent must use current CLI help and repository
state rather than copying the video's commands literally.

## A simpler human-facing version of the same workflow

The user should experience this:

```text
1. Describe the product or change normally.
2. Review what the agent believes the product should do.
3. Review the important architecture choices in plain language or a diagram.
4. Review the consequential behavioral meaning of the prompt changes.
5. Let the agent run PDD and the tests.
6. Judge the resulting evidence and correct anything that is wrong.
```

The agent should perform:

```text
preserve request
-> maintain PRD/technology choices when useful
-> invoke architecture template
-> maintain .pddrc and architecture.json
-> generate/update the prompt graph
-> choose selective independent stories
-> synchronize in supported dependency order
-> generate/run tests
-> report evidence and uncertainty
```

This preserves the video's three meaningful review boundaries without forcing
the user to remember templates, file paths, JSON schemas, module names, or
synchronization order.

## Effect on the implemented `pdd intent` facade

The video supplied design evidence for the implemented `pdd intent` workflow.

`pdd intent plan` now summarizes these concerns in its review card when they
are relevant:

```text
Product interpretation:
Architecture interpretation:
Prompt/test impact:
```

It exposes consequential decisions and lets the human approve or correct the
meaning. `pdd intent apply` owns template selection, architecture
metadata, prompt generation, dependency ordering, scoped synchronization, and
verification.

For a small change to an established module, the architecture section can say
“no architecture change.” For a greenfield or cross-cutting change, it becomes
an explicit approval boundary. This avoids turning every request into a full
PRD ceremony while still protecting major design decisions.

## Bottom line

The video does not make the existing command surface simple. It does make the
underlying PDD model clearer:

> Humans govern product intent, architecture, prompt meaning, and acceptable
> evidence. AI agents and PDD should maintain the files and execute the
> dependency-aware mechanics.

That is compatible with Prompt-Driven Development and is the reasonable
human-facing workflow we should build.
